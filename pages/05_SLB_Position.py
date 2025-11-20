import streamlit as st
import pandas as pd
from datetime import date
import io
import os
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Font, Alignment, PatternFill, numbers, Border, Side
# Pastikan Anda telah menghapus gspread dan oauth2client dari requirements.txt

# --- Konfigurasi File Lokal ---
# Pastikan file ini ada di root folder dengan header yang benar
BORROW_FILE = 'borrow_contracts.csv'
RETURN_FILE = 'return_events.csv'

# --- Fungsi Utility Data Loading (CSV) ---

@st.cache_data(ttl=600) 
def load_data(file_path):
    """Memuat data dari file CSV lokal atau membuat DataFrame kosong."""
    try:
        df = pd.read_csv(file_path, encoding='utf-8') 
        
        # Konversi tipe data tanggal
        date_cols = ['Request Date', 'Reimbursement Date', 'Actual Return Date', 'Original Request Date']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
                
        # Konversi numerik
        for col in ['Borrow Amount (shares)', 'Borrow Price', 'Return Shares']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

        return df.dropna(how='all')
    except (FileNotFoundError, pd.errors.EmptyDataError):
        # Jika file tidak ada atau kosong, buat DataFrame kosong dengan header yang sesuai
        if file_path == BORROW_FILE:
            cols = ['Request Date', 'Borrower', 'Stock Code', 'Borrow Amount (shares)', 'Borrow Price', 'Reimbursement Date', 'Status']
        elif file_path == RETURN_FILE:
            cols = ['Original Request Date', 'Borrower', 'Stock Code', 'Return Shares', 'Actual Return Date']
        else:
            cols = []
            
        return pd.DataFrame(columns=cols)
    except Exception as e:
        st.error(f"Gagal memuat data dari CSV. Pastikan header sudah benar. Error: {e}")
        return pd.DataFrame()

# --- Fungsi Utility Data Saving (CSV) ---

def append_and_save(file_path, new_data):
    """Menambahkan data baru, menyimpan kembali ke CSV, dan memperbarui cache."""
    
    df = load_data(file_path)
    new_df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
    
    try:
        new_df.to_csv(file_path, index=False, encoding='utf-8')
    except Exception as e:
        st.error(f"Gagal menyimpan ke file CSV lokal. Error: {e}")
        return False

    load_data.clear() 
    return True
        
# --- Fungsi Logika Pembuatan Laporan ---

def generate_report_dfs(borrow_df, return_df, report_date):
    """Memproses data pinjaman dan pengembalian untuk menghasilkan 2 tabel laporan."""
    
    # 1. Proses Data Pinjaman (LENT) - Tabel Atas
    lent_df = borrow_df.copy()
    lent_df['Borrow Value'] = lent_df['Borrow Amount (shares)'] * lent_df['Borrow Price']
    
    lent_df['Request Date'] = pd.to_datetime(lent_df['Request Date'], errors='coerce')
    lent_df['Reimbursement Date'] = pd.to_datetime(lent_df['Reimbursement Date'], errors='coerce')

    lent_df['Estimated Period (days)'] = (lent_df['Reimbursement Date'] - lent_df['Request Date']).dt.days
    lent_df['Status'] = 'Lent'
    
    lent_df = lent_df[['Request Date', 'Borrower', 'Stock Code', 'Borrow Amount (shares)', 'Borrow Price', 'Borrow Value', 'Status', 'Reimbursement Date', 'Estimated Period (days)']]
    
    lent_df['Request Date'] = lent_df['Request Date'].dt.date
    lent_df['Reimbursement Date'] = lent_df['Reimbursement Date'].dt.date
    
    # 2. Proses Data Pengembalian (RETURNED) - Tabel Bawah
    
    returned_on_date = return_df.copy() # Ambil semua riwayat return
    
    if returned_on_date.empty:
        return lent_df, pd.DataFrame()

    returned_on_date['Original Request Date'] = pd.to_datetime(returned_on_date['Original Request Date'], errors='coerce')
    returned_on_date['Actual Return Date'] = pd.to_datetime(returned_on_date['Actual Return Date'], errors='coerce')

    # Filter untuk pengembalian yang terjadi sampai tanggal laporan (misalnya hari ini)
    returned_on_date = returned_on_date[returned_on_date['Actual Return Date'].dt.date <= report_date].copy()

    # Perhitungan periode dan merge Borrow Price
    merged_returns = returned_on_date.merge(
        borrow_df[['Stock Code', 'Borrower', 'Borrow Price']].drop_duplicates(subset=['Stock Code', 'Borrower'], keep='last'),
        on=['Stock Code', 'Borrower'], how='left'
    )
    
    merged_returns['Estimated Period (days)'] = (
        merged_returns['Actual Return Date'] - 
        merged_returns['Original Request Date']
    ).dt.days

    # Buat DataFrame Returned Final
    returned_df_final = pd.DataFrame({
        'Request Date': merged_returns['Original Request Date'].dt.date,
        'Borrower': merged_returns['Borrower'],
        'Stock Code': merged_returns['Stock Code'],
        'Borrow Amount (shares)': merged_returns['Return Shares'], 
        'Borrow Price': merged_returns['Borrow Price'].fillna(0),
        'Status': 'Returned',
        'Reimbursement Date': merged_returns['Actual Return Date'].dt.date,
        'Estimated Period (days)': merged_returns['Estimated Period (days)']
    })

    returned_df_final['Borrow Value'] = returned_df_final['Borrow Amount (shares)'] * returned_df_final['Borrow Price']
    
    return lent_df, returned_df_final.reset_index(drop=True)

# --- Fungsi Pembuatan Excel (OpenPyXL, REVISI FINAL) ---

def create_excel_report(template_file, lent_df, returned_df, report_date):
    """Mengisi template Excel dengan strategi append dan mempertahankan format."""
    
    try:
        wb = load_workbook(template_file)
        ws = wb.active 
    except Exception as e:
        st.error(f"Gagal memuat template Excel: {e}")
        return None

    # --- KONFIGURASI BARIS UTAMA BERDASARKAN TEMPLATE ANDA ---
    START_ROW_LENT_DATA = 8             # Data Lent dimulai dari baris 8
    ORIGINAL_TOTAL_LENT_ROW = 19        # Baris Total Lent di template awal
    
    # Header Returned di template lama berada 6 baris setelah Baris 19 (yaitu Baris 25)
    # Total Returned berada 2 baris di bawah header Returned (yaitu Baris 27)
    
    # Asumsi: Jarak dari Total Lent ke Header Returned selalu 6 baris
    
    # --- 1. PEMBARUAN HEADER TANGGAL (ROW 2) ---
    date_str_formatted = report_date.strftime("%d-%b-%Y")
    new_header_value = (
        "SLB Daily Position\n"
        f"Daily As of Date: {date_str_formatted} – {date_str_formatted}"
    )
    ws['A2'].value = new_header_value
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    # --- 2. PERGESERAN BARIS LENT ---
    
    # Hitung data lama yang ada di template (asumsi Baris 8-18)
    old_data_count = ORIGINAL_TOTAL_LENT_ROW - START_ROW_LENT_DATA
    new_data_count = len(lent_df)
    
    row_difference = new_data_count - old_data_count # Berapa baris yang perlu ditambahkan/dihapus
    
    # --- Sisipkan/Hapus Baris di atas Baris Total Lent lama (Baris 19) ---
    if row_difference > 0:
        ws.insert_rows(ORIGINAL_TOTAL_LENT_ROW, row_difference)
    elif row_difference < 0:
        ws.delete_rows(ORIGINAL_TOTAL_LENT_ROW + row_difference, abs(row_difference))

    # --- 3. TULIS ULANG SELURUH DATA LENT (Mulai dari Baris 8) ---
    for r_idx, row in enumerate(dataframe_to_rows(lent_df, header=False, index=False)):
        row_num = START_ROW_LENT_DATA + r_idx
        
        # Tulis Kolom A-I
        ws.cell(row=row_num, column=1, value=row[0]) # Request Date
        ws.cell(row=row_num, column=2, value=row[1]) # Borrower
        ws.cell(row=row_num, column=3, value=row[2]) # Stock Code
        ws.cell(row=row_num, column=4, value=row[3]) # Borrow Amount
        ws.cell(row=row_num, column=5, value=row[4]) # Borrow Price
        ws.cell(row=row_num, column=6, value=row[5]) # Borrow Value
        ws.cell(row=row_num, column=7, value=row[6]) # Status
        ws.cell(row=row_num, column=8, value=row[7]) # Reimbursement Date
        ws.cell(row=row_num, column=9, value=row[8]) # Estimated Period
        
        # Format angka (Kolom D, E, F)
        ws.cell(row=row_num, column=4).number_format = numbers.FORMAT_NUMBER_COMMA_SEPARATED1
        ws.cell(row=row_num, column=5).number_format = numbers.FORMAT_NUMBER_COMMA_SEPARATED1
        ws.cell(row=row_num, column=6).number_format = numbers.FORMAT_NUMBER_COMMA_SEPARATED1

    # --- 4. PERBARUI BARIS TOTAL LENT (ROW BARU YANG BERGESER) ---
    
    new_total_lent_row = START_ROW_LENT_DATA + new_data_count 
    
    # Salin kembali format Total (dari baris Total lama ke baris Total yang bergeser)
    for col_idx in range(1, 10):
        source_cell = ws.cell(row=ORIGINAL_TOTAL_LENT_ROW, column=col_idx)
        dest_cell = ws.cell(row=new_total_lent_row, column=col_idx)
        dest_cell._style = source_cell._style
        
        # Hanya salin nilai jika itu formula atau teks Total
        if isinstance(source_cell.value, str) and '=' in source_cell.value:
             # Koreksi formula SUM
            dest_cell.value = f'=SUM(F{START_ROW_LENT_DATA}:F{new_total_lent_row - 1})'
        else:
            dest_cell.value = source_cell.value
    
    # Kosongkan baris Total Lent lama jika baris bergeser ke atas
    if row_difference < 0:
         for col in range(1, 10):
            ws.cell(row=ORIGINAL_TOTAL_LENT_ROW + row_difference, column=col).value = None


    # --- 5. PERBARUI DATA RETURNED (TABEL BAWAH) ---
    
    # Lokasi Header Returned yang baru (asumsi bergeser bersama Total Lent)
    # Jarak Header Returned (Baris 25) dari Total Lent (Baris 19) adalah 6 baris.
    NEW_START_ROW_RETURNED_HEADER = new_total_lent_row + 6 
    
    # Lokasi Data Returned Baru
    START_ROW_RETURNED_DATA = NEW_START_ROW_RETURNED_HEADER + 2 

    # Hapus data Returned lama (Asumsi 2 baris data lama dari Baris 27 dan 28)
    # Kita tidak tahu persis baris mana yang dihapus di template, 
    # jadi kita akan menghapus 2 baris setelah header returned yang lama.
    
    # TEMPORARY FIX: Coba hapus 2 baris di lokasi default Baris 27 (jika belum tergeser)
    ws.delete_rows(27, 2) 

    # Sisipkan baris baru di lokasi data Returned baru (jika ada data baru)
    new_returned_data_count = len(returned_df)
    if new_returned_data_count > 0:
        ws.insert_rows(START_ROW_RETURNED_DATA, new_returned_data_count)
        
    # Tulis data RETURNED baru
    for r_idx, row in enumerate(dataframe_to_rows(returned_df, header=False, index=False)):
        row_num = START_ROW_RETURNED_DATA + r_idx
        
        # Tulis Kolom A-I
        ws.cell(row=row_num, column=1, value=row[0]) 
        ws.cell(row=row_num, column=2, value=row[1]) 
        ws.cell(row=row_num, column=3, value=row[2]) 
        ws.cell(row=row_num, column=4, value=row[3]) 
        ws.cell(row=row_num, column=5, value=row[4]) 
        ws.cell(row=row_num, column=6, value=row[5]) 
        ws.cell(row=row_num, column=7, value=row[6])
        ws.cell(row=row_num, column=8, value=row[7])
        ws.cell(row=row_num, column=9, value=row[8]) 
            
        # Format Value cell (Kolom F)
        ws.cell(row=row_num, column=6).number_format = numbers.FORMAT_NUMBER_COMMA_SEPARATED1
        
    # --- 6. PERBARUI BARIS TOTAL RETURNED ---
    
    # Hitung lokasi baris Total Returned yang baru
    new_total_returned_row = START_ROW_RETURNED_DATA + new_returned_data_count 
    
    # Perbarui formula SUM (Asumsi Total Value di kolom F)
    ws.cell(row=new_total_returned_row, column=6).value = f'=SUM(F{START_ROW_RETURNED_DATA}:F{new_total_returned_row - 1})'
    ws.cell(row=new_total_returned_row, column=6).font = Font(bold=True)
    ws.cell(row=new_total_returned_row, column=6).number_format = numbers.FORMAT_NUMBER_COMMA_SEPARATED1

    # --- SIMPAN DAN KEMBALIKAN FILE ---
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

# --- Aplikasi Streamlit Utama ---

st.set_page_config(layout="wide", page_title="SLB Daily Position Generator")

st.title("📊 SLB Daily Position Automation (CSV DB)")

# --- Pemuatan Data dari CSV ---
if 'slb_borrow_df' not in st.session_state:
    st.session_state['slb_borrow_df'] = load_data(BORROW_FILE)
if 'slb_return_df' not in st.session_state:
    st.session_state['slb_return_df'] = load_data(RETURN_FILE)

borrow_df = st.session_state['slb_borrow_df']
return_df = st.session_state['slb_return_df']


# --- Antarmuka Pengguna ---

uploaded_file = st.file_uploader("1. Upload Template Excel SLB Anda", type=['xlsx'])
report_date = st.date_input("2. Tanggal Laporan Posisi", date.today())
st.markdown("---")

col1, col2 = st.columns(2)

# --- Form Input Peminjaman Baru (LENT) ---
with col1:
    st.header("➕ Input Kontrak Pinjaman Baru (LENT)")
    with st.form("borrow_form", clear_on_submit=True):
        req_date = st.date_input("Request Date", date.today())
        borrower = st.text_input("Borrower (cth: HD, KPEI)")
        stock = st.text_input("Stock Code (cth: PGEO, MEDC)")
        amount = st.number_input("Borrow Amount (shares)", min_value=1, step=100)
        price = st.number_input("Borrow Price", min_value=0.01, step=0.001, format="%.3f")
        reimburse_date = st.date_input("Reimbursement Date (Jatuh Tempo)", date.today())
        
        submitted = st.form_submit_button("Simpan Kontrak Pinjaman ke CSV Lokal")
        if submitted:
            if all([borrower, stock, amount, price]):
                new_borrow = {
                    'Request Date': req_date,
                    'Borrower': borrower.upper(),
                    'Stock Code': stock.upper(),
                    'Borrow Amount (shares)': amount,
                    'Borrow Price': price,
                    'Reimbursement Date': reimburse_date,
                    'Status': 'Lent'
                }
                if append_and_save(BORROW_FILE, new_borrow):
                    st.session_state['slb_borrow_df'] = load_data(BORROW_FILE)
                    st.success("Kontrak Pinjaman Baru berhasil ditambahkan ke CSV lokal!")
                
            else:
                st.error("Mohon isi semua kolom input Pinjaman.")

# --- Form Input Pengembalian (RETURNED) ---
with col2:
    st.header("➖ Input Event Pengembalian (RETURNED)")
    with st.form("return_form", clear_on_submit=True):
        actual_return_date = st.date_input("Actual Return Date (Tanggal Keluar)", date.today())
        
        active_contracts = borrow_df.copy()
        if not active_contracts.empty:
            active_contracts['Contract Key'] = active_contracts['Stock Code'] + ' | ' + active_contracts['Borrower']
            stock_options = ['Pilih Saham | Peminjam'] + active_contracts['Contract Key'].unique().tolist()
        else:
            stock_options = ['Tidak ada kontrak aktif']

        selected_contract = st.selectbox("Pilih Kontrak Saham (Kode Saham | Peminjam)", stock_options)
        
        return_shares = st.number_input("Return Amount (shares)", min_value=1, step=100)
        
        return_submitted = st.form_submit_button("Simpan Event Pengembalian ke CSV Lokal")
        
        if return_submitted:
            if selected_contract != 'Pilih Saham | Peminjam' and selected_contract != 'Tidak ada kontrak aktif' and return_shares:
                try:
                    stock_code, borrower_name = selected_contract.split(' | ')
                except ValueError:
                    st.error("Format kontrak tidak valid.")
                    st.stop()
                
                original_contract = borrow_df[
                    (borrow_df['Stock Code'] == stock_code) & 
                    (borrow_df['Borrower'] == borrower_name)
                ]
                
                if original_contract.empty:
                    st.error("Kontrak asli tidak ditemukan.")
                    st.stop()
                    
                original_contract = original_contract.sort_values(by='Reimbursement Date', ascending=False).iloc[0]

                new_return = {
                    'Original Request Date': original_contract['Request Date'],
                    'Borrower': borrower_name,
                    'Stock Code': stock_code,
                    'Return Shares': return_shares,
                    'Actual Return Date': actual_return_date
                }
                
                if append_and_save(RETURN_FILE, new_return):
                    st.session_state['slb_return_df'] = load_data(RETURN_FILE)
                    st.success(f"Event Pengembalian untuk {stock_code} berhasil ditambahkan ke CSV lokal!")
            else:
                st.error("Mohon pilih kontrak dan isi jumlah saham.")

st.markdown("---")

# --- Bagian Pembuatan Laporan ---

if uploaded_file is not None:
    st.header("3. Hasil Laporan dan Download")
    
    final_lent_df, final_returned_df = generate_report_dfs(st.session_state['slb_borrow_df'], st.session_state['slb_return_df'], report_date)
    
    uploaded_file.seek(0)
    
    excel_report = create_excel_report(uploaded_file, final_lent_df, final_returned_df, report_date)

    if excel_report:
        file_name = f"SLB Position {report_date.strftime('%Y%m%d')}.xlsx"
        st.download_button(
            label="Download Laporan Excel Otomatis",
            data=excel_report,
            file_name=file_name,
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    else:
        st.warning("Data belum tersedia atau gagal memproses laporan.")
