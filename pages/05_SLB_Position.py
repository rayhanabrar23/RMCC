import streamlit as st
import pandas as pd
from datetime import date
import io
import os
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Font, Alignment, PatternFill, numbers

# --- Konfigurasi File ---
# File-file ini akan digunakan untuk menyimpan riwayat transaksi secara persisten
BORROW_FILE = 'borrow_contracts.csv'
RETURN_FILE = 'return_events.csv'

# --- Fungsi Utility Data Loading ---

@st.cache_data
def load_data(file_path):
    """Memuat data dari CSV. Jika file tidak ada, buat DataFrame kosong."""
    try:
        df = pd.read_csv(file_path)
        # Pastikan kolom tanggal adalah datetime.date object
        date_cols = ['Request Date', 'Reimbursement Date', 'Actual Return Date', 'Original Request Date']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
        return df
    except FileNotFoundError:
        if file_path == BORROW_FILE:
            return pd.DataFrame(columns=['Request Date', 'Borrower', 'Stock Code', 'Borrow Amount (shares)', 'Borrow Price', 'Reimbursement Date', 'Status'])
        elif file_path == RETURN_FILE:
            return pd.DataFrame(columns=['Original Request Date', 'Borrower', 'Stock Code', 'Return Shares', 'Actual Return Date'])
        return pd.DataFrame()

# --- Fungsi Utility Data Saving ---

def append_and_save(df, new_data, file_path):
    """Menambahkan data baru dan menyimpan kembali ke CSV."""
    # Konversi tanggal ke format string yang sesuai untuk penyimpanan CSV
    for key, value in new_data.items():
        if isinstance(value, date):
            new_data[key] = value.isoformat()
            
    new_df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
    new_df.to_csv(file_path, index=False)
    # Ini penting untuk memastikan data di-reload setelah disimpan
    st.session_state['data_updated'] = True 
    return new_df

# --- Fungsi Logika Pembuatan Laporan ---

def generate_report_dfs(borrow_df, return_df, report_date):
    """Memproses data pinjaman dan pengembalian untuk menghasilkan 2 tabel laporan."""
    
    # 1. Proses Data Pinjaman (LENT) - Tabel Atas
    lent_df = borrow_df.copy()
    
    # Hitung posisi net (ini adalah VERSI SEDERHANA, di mana kita hanya menampilkan semua kontrak yang dimasukkan 
    # di form "Lent". Untuk netting, logika perlu lebih kompleks, tapi ini sesuai permintaan "input lent/returned terpisah").
    
    # Hitung kolom turunan
    lent_df['Borrow Value'] = lent_df['Borrow Amount (shares)'] * lent_df['Borrow Price']
    lent_df['Estimated Period (days)'] = (pd.to_datetime(lent_df['Reimbursement Date']) - pd.to_datetime(lent_df['Request Date'])).dt.days
    lent_df['Status'] = 'Lent'
    
    # Pilih dan urutkan kolom sesuai template output
    lent_df = lent_df[['Request Date', 'Borrower', 'Stock Code', 'Borrow Amount (shares)', 'Borrow Price', 'Borrow Value', 'Status', 'Reimbursement Date', 'Estimated Period (days)']]
    
    # 2. Proses Data Pengembalian (RETURNED) - Tabel Bawah
    
    # Filter pengembalian yang terjadi pada tanggal laporan
    returned_on_date = return_df[return_df['Actual Return Date'] == report_date].copy()

    if returned_on_date.empty:
        return lent_df, pd.DataFrame() # Jika tidak ada pengembalian pada tanggal ini

    # Hitung Estimated Period (Actual Return Date - Original Request Date)
    returned_on_date['Estimated Period (days)'] = (
        pd.to_datetime(returned_on_date['Actual Return Date']) - 
        pd.to_datetime(returned_on_date['Original Request Date'])
    ).dt.days
    
    # Format DataFrame Returned sesuai dengan output Lent
    returned_df_final = pd.DataFrame({
        'Request Date': returned_on_date['Original Request Date'],
        'Borrower': returned_on_date['Borrower'],
        'Stock Code': returned_on_date['Stock Code'],
        'Borrow Amount (shares)': returned_on_date['Return Shares'], # Jumlah yang dikembalikan
        'Borrow Price': [0.0] * len(returned_on_date), # Harga Pinjaman harus diambil dari kontrak asli (disimplifikasi jadi 0 untuk demo ini)
        'Borrow Value': [0] * len(returned_on_date), # Borrow Value di sini biasanya nol atau dihitung berdasarkan harga saat pengembalian
        'Status': 'Returned',
        'Reimbursement Date': returned_on_date['Actual Return Date'],
        'Estimated Period (days)': returned_on_date['Estimated Period (days)']
    })

    # Catatan: Kolom 'Borrow Price' dan 'Borrow Value' untuk tabel Returned memerlukan 
    # proses join yang kompleks ke kontrak asli untuk mendapatkan harga.
    # Untuk demo ini, kita isi 0 atau Anda dapat menambahkannya secara manual setelah download.
    
    # Jika Anda ingin mengisi 'Borrow Price' dengan harga kontrak *terakhir* yang cocok:
    # merge_cols = ['Stock Code', 'Borrower']
    # merged_returns = returned_on_date.merge(
    #     borrow_df[['Stock Code', 'Borrower', 'Borrow Price']].drop_duplicates(subset=merge_cols, keep='last'),
    #     on=merge_cols, how='left'
    # )
    # returned_df_final['Borrow Price'] = merged_returns['Borrow Price'].fillna(0)
    # returned_df_final['Borrow Value'] = returned_df_final['Borrow Amount (shares)'] * returned_df_final['Borrow Price']

    return lent_df, returned_df_final.reset_index(drop=True)


# --- Fungsi Pembuatan Excel (OpenPyXL) ---

def create_excel_report(template_file, lent_df, returned_df, report_date):
    """Mengisi template Excel dengan data pinjaman dan pengembalian."""
    
    try:
        # 1. Muat Template
        wb = load_workbook(template_file)
        ws = wb.active # Asumsi data berada di sheet aktif pertama
    except Exception as e:
        st.error(f"Gagal memuat template Excel: {e}")
        return None

    # --- PEMBARUAN HEADER TANGGAL (ROW 2, MERGED A-I) ---
    date_str_formatted = report_date.strftime("%d-%b-%Y")
    
    new_header_value = (
        "SLB Daily Position\n"
        f"Daily As of Date: {date_str_formatted} – {date_str_formatted}"
    )
    # A2 adalah sel top-left dari merged area
    ws['A2'].value = new_header_value
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    # ----------------------------------------------------
    
    # Tentukan baris awal untuk data (Baris 8 di template Anda)
    start_row_lent = 8
    
    # Hapus data lama dan footer dari baris 8 hingga max row
    ws.delete_rows(start_row_lent, ws.max_row - start_row_lent + 1)
    
    # Tambahkan data baru dari lent_df
    # Pastikan data dikonversi ke format yang sesuai
    lent_data_for_excel = lent_df.copy()
    
    # Tulis data ke worksheet
    for r_idx, row in enumerate(dataframe_to_rows(lent_data_for_excel, header=False, index=False)):
        ws.append(row)

    # Tentukan baris total baru untuk LENT
    new_total_row_lent = start_row_lent + len(lent_data_for_excel)
    
    # Tulis baris Total dan format
    ws[f'A{new_total_row_lent}'] = 'Total'
    ws[f'A{new_total_row_lent}'].font = Font(bold=True)
    
    # Formula Sum Borrow Value (Kolom G)
    ws[f'G{new_total_row_lent}'] = f'=SUM(G{start_row_lent}:G{new_total_row_lent-1})'
    ws[f'G{new_total_row_lent}'].font = Font(bold=True)
    ws[f'G{new_total_row_lent}'].number_format = '#,##0.00' 
    
    # --- Tabel BAWAH (Returned) ---
    
    # Tentukan baris awal untuk tabel returned (2 baris setelah total LENT)
    start_row_returned = new_total_row_lent + 2 
    
    # Tulis Header untuk Tabel Returned
    header_returned = ['Request Date', 'Borrower', 'Stock Code', 'Borrow Amount (shares)', 'Borrow Price', 'Borrow Value', 'Status', 'Reimbursement Date', 'Estimated Period (days)']
    header_fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
    for c_idx, title in enumerate(header_returned, start=1):
        cell = ws.cell(row=start_row_returned, column=c_idx, value=title)
        cell.fill = header_fill
        cell.font = Font(bold=True)
    
    data_row_returned = start_row_returned + 1
    
    if not returned_df.empty:
        # Tambahkan data baru dari returned_df
        for r_idx, row in enumerate(dataframe_to_rows(returned_df, header=False, index=False)):
            ws.append(row)
            
        new_total_row_returned = data_row_returned + len(returned_df)
    else:
        new_total_row_returned = data_row_returned
        
    # Tulis baris Total dan format untuk Returned
    ws.cell(row=new_total_row_returned, column=1).value = 'Total'
    ws.cell(row=new_total_row_returned, column=1).font = Font(bold=True)
    
    # Formula Sum Borrow Value (Kolom G)
    ws.cell(row=new_total_row_returned, column=7).value = f'=SUM(G{data_row_returned}:G{new_total_row_returned-1})'
    ws.cell(row=new_total_row_returned, column=7).font = Font(bold=True)
    ws.cell(row=new_total_row_returned, column=7).number_format = '#,##0.00'
    
    # Simpan ke buffer
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

# --- Aplikasi Streamlit Utama ---

st.set_page_config(layout="wide", page_title="SLB Daily Position Generator")

st.title("📊 SLB Daily Position Automation")

# Inisialisasi state untuk memicu reload data
if 'data_updated' not in st.session_state:
    st.session_state['data_updated'] = False

# Muat data persisten
borrow_df = load_data(BORROW_FILE)
return_df = load_data(RETURN_FILE)

# --- Upload Template Excel ---
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
        
        submitted = st.form_submit_button("Simpan Kontrak Pinjaman")
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
                global borrow_df
                borrow_df = append_and_save(borrow_df, new_borrow, BORROW_FILE)
                st.success("Kontrak Pinjaman Baru berhasil ditambahkan!")
            else:
                st.error("Mohon isi semua kolom input Pinjaman.")

# --- Form Input Pengembalian (RETURNED) ---
with col2:
    st.header("➖ Input Event Pengembalian (RETURNED)")
    with st.form("return_form", clear_on_submit=True):
        actual_return_date = st.date_input("Actual Return Date (Tanggal Keluar)", date.today())
        
        # Opsi dropdown saham yang sedang 'Lent'
        active_contracts = borrow_df.copy()
        active_contracts['Contract Key'] = active_contracts['Stock Code'] + ' | ' + active_contracts['Borrower']
        
        stock_options = ['Pilih Saham | Peminjam'] + active_contracts['Contract Key'].unique().tolist()
        selected_contract = st.selectbox("Pilih Kontrak Saham (Kode Saham | Peminjam)", stock_options)
        
        return_shares = st.number_input("Return Amount (shares)", min_value=1, step=100)
        
        return_submitted = st.form_submit_button("Simpan Event Pengembalian")
        
        if return_submitted:
            if selected_contract != 'Pilih Saham | Peminjam' and return_shares:
                stock_code, borrower_name = selected_contract.split(' | ')
                
                # Cari Request Date asli (asumsi: ambil yang paling baru untuk kontrak ini)
                original_contract = borrow_df[
                    (borrow_df['Stock Code'] == stock_code) & 
                    (borrow_df['Borrower'] == borrower_name)
                ].sort_values(by='Reimbursement Date', ascending=False).iloc[0]
                
                new_return = {
                    'Original Request Date': original_contract['Request Date'],
                    'Borrower': borrower_name,
                    'Stock Code': stock_code,
                    'Return Shares': return_shares,
                    'Actual Return Date': actual_return_date
                }
                global return_df
                return_df = append_and_save(return_df, new_return, RETURN_FILE)
                st.success(f"Event Pengembalian untuk {stock_code} berhasil ditambahkan!")
            else:
                st.error("Mohon pilih kontrak dan isi jumlah saham.")

st.markdown("---")

# --- Bagian Pembuatan Laporan ---

if uploaded_file is not None:
    st.header("3. Hasil Laporan dan Download")
    
    # Ambil posisi terakhir (Lent & Returned pada tanggal laporan)
    final_lent_df, final_returned_df = generate_report_dfs(borrow_df, return_df, report_date)
    
    st.subheader(f"Posisi Lent Aktif per {report_date.strftime('%d %b %Y')}")
    st.dataframe(final_lent_df.style.format({
        'Borrow Price': '{:.3f}',
        'Borrow Value': '{:,.0f}'
    }))

    st.subheader(f"Event Returned pada {report_date.strftime('%d %b %Y')}")
    st.dataframe(final_returned_df.style.format({
        'Borrow Price': '{:.3f}',
        'Borrow Value': '{:,.0f}'
    }))

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
    st.warning("Silakan upload template Excel Anda di langkah 1 untuk memulai pembuatan laporan.")
