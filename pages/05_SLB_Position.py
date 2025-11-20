import streamlit as st
import pandas as pd
from datetime import date
import io
import os
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Font, Alignment, PatternFill, numbers
# Pustaka gspread dan oauth2client sudah dihapus.

# --- Konfigurasi File Lokal ---
# File ini harus ada di root folder (sejajar dengan pages/)
BORROW_FILE = 'borrow_contracts.csv'
RETURN_FILE = 'return_events.csv'

# --- Fungsi Utility Data Loading (CSV) ---

@st.cache_data(ttl=600) 
def load_data(file_path):
    """Memuat data dari file CSV lokal atau membuat DataFrame kosong."""
    try:
        # Baca CSV. Jika ada masalah encoding di lingkungan cloud, bisa dihilangkan.
        df = pd.read_csv(file_path, encoding='utf-8') 
        
        # Konversi tipe data tanggal
        date_cols = ['Request Date', 'Reimbursement Date', 'Actual Return Date', 'Original Request Date']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
                
        # Konversi numerik
        for col in ['Borrow Amount (shares)', 'Borrow Price', 'Return Shares']:
            if col in df.columns:
                # Handle koma/titik dan konversi
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

        return df.dropna(how='all') # Bersihkan baris yang sepenuhnya kosong
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
    
    # Ambil DF yang sedang aktif (dari cache)
    df = load_data(file_path)
        
    # Tambahkan data baru
    new_df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
    
    # Simpan kembali ke CSV
    try:
        new_df.to_csv(file_path, index=False, encoding='utf-8')
    except Exception as e:
        st.error(f"Gagal menyimpan ke file CSV lokal. Pastikan izin penulisan diaktifkan: {e}")
        return False

    # Hapus cache agar data terbaru dimuat pada rerun berikutnya
    load_data.clear() 
    return True
        
# --- Fungsi Logika Pembuatan Laporan (TETAP SAMA) ---

def generate_report_dfs(borrow_df, return_df, report_date):
    """Memproses data pinjaman dan pengembalian untuk menghasilkan 2 tabel laporan."""
    
    # 1. Proses Data Pinjaman (LENT) - Tabel Atas
    lent_df = borrow_df.copy()
    
    lent_df['Borrow Value'] = lent_df['Borrow Amount (shares)'] * lent_df['Borrow Price']
    
    # Pastikan perhitungan tanggal hanya dilakukan pada kolom bertipe date
    lent_df['Request Date'] = pd.to_datetime(lent_df['Request Date'], errors='coerce')
    lent_df['Reimbursement Date'] = pd.to_datetime(lent_df['Reimbursement Date'], errors='coerce')

    lent_df['Estimated Period (days)'] = (lent_df['Reimbursement Date'] - lent_df['Request Date']).dt.days
    lent_df['Status'] = 'Lent'
    
    lent_df = lent_df[['Request Date', 'Borrower', 'Stock Code', 'Borrow Amount (shares)', 'Borrow Price', 'Borrow Value', 'Status', 'Reimbursement Date', 'Estimated Period (days)']]
    
    # Konversi kembali kolom tanggal untuk tampilan yang bersih
    lent_df['Request Date'] = lent_df['Request Date'].dt.date
    lent_df['Reimbursement Date'] = lent_df['Reimbursement Date'].dt.date
    
    # 2. Proses Data Pengembalian (RETURNED) - Tabel Bawah
    
    returned_on_date = return_df[return_df['Actual Return Date'] == report_date].copy()

    if returned_on_date.empty:
        return lent_df, pd.DataFrame()

    returned_on_date['Original Request Date'] = pd.to_datetime(returned_on_date['Original Request Date'], errors='coerce')
    returned_on_date['Actual Return Date'] = pd.to_datetime(returned_on_date['Actual Return Date'], errors='coerce')

    returned_on_date['Estimated Period (days)'] = (
        returned_on_date['Actual Return Date'] - 
        returned_on_date['Original Request Date']
    ).dt.days
    
    # Untuk mendapatkan Borrow Price: join ke kontrak terakhir yang cocok
    merge_cols = ['Stock Code', 'Borrower']
    merged_returns = returned_on_date.merge(
        borrow_df[['Stock Code', 'Borrower', 'Borrow Price']].drop_duplicates(subset=merge_cols, keep='last'),
        on=merge_cols, how='left'
    )
    
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

    # Hitung Borrow Value setelah mendapatkan Borrow Price
    returned_df_final['Borrow Value'] = returned_df_final['Borrow Amount (shares)'] * returned_df_final['Borrow Price']
    
    return lent_df, returned_df_final.reset_index(drop=True)

# --- Fungsi Pembuatan Excel (OpenPyXL, TETAP SAMA) ---

def create_excel_report(template_file, lent_df, returned_df, report_date):
    """Mengisi template Excel dengan data pinjaman dan pengembalian."""
    
    try:
        wb = load_workbook(template_file)
        ws = wb.active 
    except Exception as e:
        st.error(f"Gagal memuat template Excel: {e}")
        return None

    # PEMBARUAN HEADER TANGGAL (ROW 2, MERGED A-I)
    date_str_formatted = report_date.strftime("%d-%b-%Y")
    
    new_header_value = (
        "SLB Daily Position\n"
        f"Daily As of Date: {date_str_formatted} – {date_str_formatted}"
    )
    ws['A2'].value = new_header_value
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    # BARIS DATA DI MULAI DARI BARIS 8
    start_row_lent = 8
    # Hapus baris lama (setelah header tabel LENT)
    ws.delete_rows(start_row_lent, ws.max_row) 
    
    # Tulis data LENT
    for r_idx, row in enumerate(dataframe_to_rows(lent_df, header=False, index=False)):
        ws.append(row)

    # Total LENT
    new_total_row_lent = start_row_lent + len(lent_df)
    ws[f'A{new_total_row_lent}'] = 'Total'
    ws[f'A{new_total_row_lent}'].font = Font(bold=True)
    ws[f'F{new_total_row_lent}'] = 'Total Value:'
    ws[f'F{new_total_row_lent}'].font = Font(bold=True)
    ws[f'G{new_total_row_lent}'] = f'=SUM(G{start_row_lent}:G{new_total_row_lent-1})'
    ws[f'G{new_total_row_lent}'].font = Font(bold=True)
    ws[f'G{new_total_row_lent}'].number_format = numbers.FORMAT_NUMBER_COMMA_SEPARATED1
    
    # TABEL RETURNED (2 baris setelah total LENT)
    start_row_returned_header = new_total_row_lent + 2 
    header_returned = ['Request Date', 'Borrower', 'Stock Code', 'Borrow Amount (shares)', 'Borrow Price', 'Borrow Value', 'Status', 'Reimbursement Date', 'Estimated Period (days)']
    header_fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
    for c_idx, title in enumerate(header_returned, start=1):
        cell = ws.cell(row=start_row_returned_header, column=c_idx, value=title)
        cell.fill = header_fill
        cell.font = Font(bold=True)
    
    data_row_returned = start_row_returned_header + 1
    
    if not returned_df.empty:
        for r_idx, row in enumerate(dataframe_to_rows(returned_df, header=False, index=False)):
            # Tulis data pengembalian
            ws.cell(row=data_row_returned + r_idx, column=1, value=row[0]) 
            ws.cell(row=data_row_returned + r_idx, column=2, value=row[1]) 
            ws.cell(row=data_row_returned + r_idx, column=3, value=row[2]) 
            ws.cell(row=data_row_returned + r_idx, column=4, value=row[3]) 
            ws.cell(row=data_row_returned + r_idx, column=5, value=row[4]) 
            ws.cell(row=data_row_returned + r_idx, column=6, value=row[5]) 
            ws.cell(row=data_row_returned + r_idx, column=7, value=row[6])
            ws.cell(row=data_row_returned + r_idx, column=8, value=row[7])
            ws.cell(row=data_row_returned + r_idx, column=9, value=row[8]) 
            
            # Format Value cell (Kolom F)
            ws.cell(row=data_row_returned + r_idx, column=6).number_format = numbers.FORMAT_NUMBER_COMMA_SEPARATED1
            
        new_total_row_returned = data_row_returned + len(returned_df)
    else:
        new_total_row_returned = data_row_returned
        
    # Total RETURNED
    ws.cell(row=new_total_row_returned, column=1).value = 'Total'
    ws.cell(row=new_total_row_returned, column=1).font = Font(bold=True)
    ws.cell(row=new_total_row_returned, column=5).value = 'Total Value:'
    ws.cell(row=new_total_row_returned, column=5).font = Font(bold=True)
    ws.cell(row=new_total_row_returned, column=6).value = f'=SUM(F{data_row_returned}:F{new_total_row_returned-1})'
    ws.cell(row=new_total_row_returned, column=6).font = Font(bold=True)
    ws.cell(row=new_total_row_returned, column=6).number_format = numbers.FORMAT_NUMBER_COMMA_SEPARATED1

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

# --- Aplikasi Streamlit Utama ---

st.set_page_config(layout="wide", page_title="SLB Daily Position Generator")

st.title("📊 SLB Daily Position Automation (CSV DB)")

# --- Pemuatan Data dari CSV ---
# Data disimpan di st.session_state 
if 'slb_borrow_df' not in st.session_state:
    st.session_state['slb_borrow_df'] = load_data(BORROW_FILE)
if 'slb_return_df' not in st.session_state:
    st.session_state['slb_return_df'] = load_data(RETURN_FILE)

borrow_df = st.session_state['slb_borrow_df']
return_df = st.session_state['slb_return_df']

# ... (sisa kode formulir dan logika download tetap sama, hanya ganti pemanggilan fungsi) ...

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
                # Panggil fungsi penyimpanan CSV yang baru
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
        
        # Opsi dropdown saham diambil dari kontrak aktif
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
                
                # Cari Request Date asli (gunakan kontrak terakhir yang cocok untuk menyederhanakan)
                original_contract = borrow_df[
                    (borrow_df['Stock Code'] == stock_code) & 
                    (borrow_df['Borrower'] == borrower_name)
                ]
                
                if original_contract.empty:
                    st.error("Kontrak asli tidak ditemukan.")
                    st.stop()
                    
                # Ambil data kontrak terakhir yang cocok
                original_contract = original_contract.sort_values(by='Reimbursement Date', ascending=False).iloc[0]

                new_return = {
                    'Original Request Date': original_contract['Request Date'],
                    'Borrower': borrower_name,
                    'Stock Code': stock_code,
                    'Return Shares': return_shares,
                    'Actual Return Date': actual_return_date
                }
                
                # Panggil fungsi penyimpanan CSV yang baru
                if append_and_save(RETURN_FILE, new_return):
                    st.session_state['slb_return_df'] = load_data(RETURN_FILE)
                    st.success(f"Event Pengembalian untuk {stock_code} berhasil ditambahkan ke CSV lokal!")
            else:
                st.error("Mohon pilih kontrak dan isi jumlah saham.")

st.markdown("---")

# --- Bagian Pembuatan Laporan ---

if uploaded_file is not None:
    st.header("3. Hasil Laporan dan Download")
    
    # Ambil posisi terakhir (Lent & Returned pada tanggal laporan)
    final_lent_df, final_returned_df = generate_report_dfs(st.session_state['slb_borrow_df'], st.session_state['slb_return_df'], report_date)
    
    # Reset pointer file sebelum diproses OpenPyXL
    uploaded_file.seek(0)
    
    # Generate Excel dan Download
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
