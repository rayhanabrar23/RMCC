import streamlit as st
import pandas as pd
from datetime import date
import io
import gspread # Untuk interaksi Google Sheets
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Font, Alignment, PatternFill, numbers
# Perlu menambahkan 'gspread' dan 'oauth2client' ke requirements.txt

# --- Konfigurasi Google Sheets ---
# Ganti dengan nama spreadsheet Anda di Google Drive
GSHEET_NAME = "SLB Database" 
SHEET_CONTRACTS = "Contracts"
SHEET_RETURNS = "Returns"

# --- Fungsi Utility Data Loading (GSheets) ---

@st.cache_resource(ttl=3600) 
def get_gspread_client():
    """Menginisialisasi koneksi GSheets menggunakan st.secrets."""
    try:
        # Menggunakan Service Account dari st.secrets["gspread"]
        return gspread.service_account_from_dict(st.secrets["gspread"])
    except Exception as e:
        st.error(f"Gagal otentikasi Google Sheets. Cek file .streamlit/secrets.toml. Error: {e}")
        return None

@st.cache_data(ttl=600) 
def load_gsheet_data(sheet_name):
    """Memuat data dari Google Sheet dan mengonversinya ke DataFrame."""
    try:
        gc = get_gspread_client()
        if not gc:
            return pd.DataFrame()
            
        sh = gc.open(GSHEET_NAME)
        worksheet = sh.worksheet(sheet_name)
        
        data = worksheet.get_all_values()
        if not data:
            return pd.DataFrame()
            
        df = pd.DataFrame(data[1:], columns=data[0])
        
        # Konversi tipe data
        date_cols = ['Request Date', 'Reimbursement Date', 'Actual Return Date', 'Original Request Date']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

        for col in ['Borrow Amount (shares)', 'Borrow Price', 'Return Shares']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].str.replace(',', '.'), errors='coerce').fillna(0) # Handle koma/titik
        
        return df.dropna(how='all')
    except Exception as e:
        st.warning(f"Memuat data {sheet_name} gagal. Pastikan sheet/spreadsheet name benar dan izin share sudah diberikan. Error: {e}")
        return pd.DataFrame()

# --- Fungsi Utility Data Saving (GSheets) ---

def append_and_save_gsheet(sheet_name, new_data):
    """Menambahkan baris baru ke Google Sheet."""
    try:
        gc = get_gspread_client()
        if not gc:
            return False
            
        sh = gc.open(GSHEET_NAME)
        worksheet = sh.worksheet(sheet_name)
        
        # Penentuan kunci kolom berdasarkan sheet
        if sheet_name == SHEET_CONTRACTS:
            keys = ['Request Date', 'Borrower', 'Stock Code', 'Borrow Amount (shares)', 'Borrow Price', 'Reimbursement Date', 'Status']
        else: # SHEET_RETURNS
            keys = ['Original Request Date', 'Borrower', 'Stock Code', 'Return Shares', 'Actual Return Date']
            
        row_values = []
        for key in keys:
            value = new_data.get(key)
            if isinstance(value, date):
                row_values.append(value.isoformat())
            elif isinstance(value, (float, int)):
                 row_values.append(value)
            else:
                row_values.append(str(value))
        
        worksheet.append_row(row_values)
        
        # Hapus cache data agar data terbaru dimuat pada rerun berikutnya
        load_gsheet_data.clear() 
        return True
    except Exception as e:
        st.error(f"Gagal menyimpan data ke Google Sheet. Error: {e}")
        return False
        
# --- Fungsi Logika Pembuatan Laporan ---

def generate_report_dfs(borrow_df, return_df, report_date):
    """Memproses data pinjaman dan pengembalian untuk menghasilkan 2 tabel laporan."""
    
    # 1. Proses Data Pinjaman (LENT) - Tabel Atas
    lent_df = borrow_df.copy()
    
    lent_df['Borrow Value'] = lent_df['Borrow Amount (shares)'] * lent_df['Borrow Price']
    lent_df['Estimated Period (days)'] = (pd.to_datetime(lent_df['Reimbursement Date']) - pd.to_datetime(lent_df['Request Date'])).dt.days
    lent_df['Status'] = 'Lent'
    
    lent_df = lent_df[['Request Date', 'Borrower', 'Stock Code', 'Borrow Amount (shares)', 'Borrow Price', 'Borrow Value', 'Status', 'Reimbursement Date', 'Estimated Period (days)']]
    
    # 2. Proses Data Pengembalian (RETURNED) - Tabel Bawah
    
    returned_on_date = return_df[return_df['Actual Return Date'] == report_date].copy()

    if returned_on_date.empty:
        return lent_df, pd.DataFrame()

    returned_on_date['Estimated Period (days)'] = (
        pd.to_datetime(returned_on_date['Actual Return Date']) - 
        pd.to_datetime(returned_on_date['Original Request Date'])
    ).dt.days
    
    # Untuk mendapatkan Borrow Price: join ke kontrak terakhir yang cocok
    merge_cols = ['Stock Code', 'Borrower']
    merged_returns = returned_on_date.merge(
        borrow_df[['Stock Code', 'Borrower', 'Borrow Price']].drop_duplicates(subset=merge_cols, keep='last'),
        on=merge_cols, how='left'
    )
    
    # Buat DataFrame Returned Final
    returned_df_final = pd.DataFrame({
        'Request Date': merged_returns['Original Request Date'],
        'Borrower': merged_returns['Borrower'],
        'Stock Code': merged_returns['Stock Code'],
        'Borrow Amount (shares)': merged_returns['Return Shares'], 
        'Borrow Price': merged_returns['Borrow Price'].fillna(0),
        'Status': 'Returned',
        'Reimbursement Date': merged_returns['Actual Return Date'],
        'Estimated Period (days)': merged_returns['Estimated Period (days)']
    })

    # Hitung Borrow Value setelah mendapatkan Borrow Price
    returned_df_final['Borrow Value'] = returned_df_final['Borrow Amount (shares)'] * returned_df_final['Borrow Price']
    
    return lent_df, returned_df_final.reset_index(drop=True)

# --- Fungsi Pembuatan Excel (OpenPyXL) ---

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
    ws.delete_rows(start_row_lent, ws.max_row - start_row_lent + 1)
    
    # Tulis data LENT
    for r_idx, row in enumerate(dataframe_to_rows(lent_df, header=False, index=False)):
        ws.append(row)

    # Total LENT
    new_total_row_lent = start_row_lent + len(lent_df)
    ws[f'A{new_total_row_lent}'] = 'Total'
    ws[f'A{new_total_row_lent}'].font = Font(bold=True)
    ws[f'G{new_total_row_lent}'] = f'=SUM(G{start_row_lent}:G{new_total_row_lent-1})'
    ws[f'G{new_total_row_lent}'].font = Font(bold=True)
    ws[f'G{new_total_row_lent}'].number_format = '#,##0.00' 
    
    # TABEL RETURNED (2 baris setelah total LENT)
    start_row_returned = new_total_row_lent + 2 
    header_returned = ['Request Date', 'Borrower', 'Stock Code', 'Borrow Amount (shares)', 'Borrow Price', 'Borrow Value', 'Status', 'Reimbursement Date', 'Estimated Period (days)']
    header_fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
    for c_idx, title in enumerate(header_returned, start=1):
        cell = ws.cell(row=start_row_returned, column=c_idx, value=title)
        cell.fill = header_fill
        cell.font = Font(bold=True)
    
    data_row_returned = start_row_returned + 1
    
    if not returned_df.empty:
        for r_idx, row in enumerate(dataframe_to_rows(returned_df, header=False, index=False)):
            ws.append(row)
            
        new_total_row_returned = data_row_returned + len(returned_df)
    else:
        new_total_row_returned = data_row_returned
        
    # Total RETURNED
    ws.cell(row=new_total_row_returned, column=1).value = 'Total'
    ws.cell(row=new_total_row_returned, column=1).font = Font(bold=True)
    ws.cell(row=new_total_row_returned, column=7).value = f'=SUM(G{data_row_returned}:G{new_total_row_returned-1})'
    ws.cell(row=new_total_row_returned, column=7).font = Font(bold=True)
    ws.cell(row=new_total_row_returned, column=7).number_format = '#,##0.00'
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

# --- Aplikasi Streamlit Utama ---

st.set_page_config(layout="wide", page_title="SLB Daily Position Generator")

st.title("📊 SLB Daily Position Automation (Google Sheets DB)")

# --- Pemuatan Data dari Google Sheets ---
# Data disimpan di st.session_state untuk akses cepat
if 'slb_borrow_df' not in st.session_state:
    st.session_state['slb_borrow_df'] = load_gsheet_data(SHEET_CONTRACTS)
if 'slb_return_df' not in st.session_state:
    st.session_state['slb_return_df'] = load_gsheet_data(SHEET_RETURNS)

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
        
        submitted = st.form_submit_button("Simpan Kontrak Pinjaman ke GSheets")
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
                if append_and_save_gsheet(SHEET_CONTRACTS, new_borrow):
                    st.success("Kontrak Pinjaman Baru berhasil ditambahkan ke Google Sheets!")
                
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
        
        return_submitted = st.form_submit_button("Simpan Event Pengembalian ke GSheets")
        
        if return_submitted:
            if selected_contract != 'Pilih Saham | Peminjam' and selected_contract != 'Tidak ada kontrak aktif' and return_shares:
                stock_code, borrower_name = selected_contract.split(' | ')
                
                # Cari Request Date asli (gunakan kontrak terakhir yang cocok untuk menyederhanakan)
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
                
                if append_and_save_gsheet(SHEET_RETURNS, new_return):
                    st.success(f"Event Pengembalian untuk {stock_code} berhasil ditambahkan ke Google Sheets!")
            else:
                st.error("Mohon pilih kontrak dan isi jumlah saham.")

st.markdown("---")

# --- Bagian Pembuatan Laporan ---

if uploaded_file is not None:
    st.header("3. Hasil Laporan dan Download")
    
    # Ambil posisi terakhir (Lent & Returned pada tanggal laporan)
    final_lent_df, final_returned_df = generate_report_dfs(borrow_df, return_df, report_date)
    
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
        st.warning("Data belum tersedia atau gagal terhubung ke Google Sheets.")
