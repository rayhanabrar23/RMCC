import streamlit as st
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from io import BytesIO
from datetime import datetime

# Cek login (Opsional, sesuaikan dengan file utama Anda)
if "login_status" not in st.session_state or not st.session_state["login_status"]:
    st.error("🚨 Akses Ditolak! Silakan login di halaman utama terlebih dahulu.")
    st.stop()

# ============================
# KONSTANTA & KONFIGURASI
# ============================
# Nama kolom harus sesuai dengan yang ada di file Excel/CSV
REPO_KEY_COL = 'Instrument Code' 
PHEI_KEY_COL = 'SERIES' 
PHEI_VALUE_COL = 'TODAY FAIR PRICE' 

# Berdasarkan gambar user:
# Header utama (No, Agent Name, dll) ada di baris 10 Excel -> Index 9
HEADER_ROW_INDEX = 9 
# Data pertama (No. 1) mulai di baris 11 Excel
START_ROW_EXCEL = 11 

# ============================
# FUNGSI PEMBERSIH KUNCI
# ============================
def clean_key_extreme(series):
    """Membersihkan spasi dan karakter aneh pada kode instrumen."""
    return series.astype(str).str.strip().str.upper().replace(r'[^A-Z0-9]', '', regex=True)

# ============================
# FUNGSI PENGOLAHAN DATA UTAMA
# ============================
def process_repo_data(df_repo_main, df_phei_lookup):
    st.info("Sedang mencocokkan data Instrument Code dengan Series PHEI...")
    
    # 1. Standarisasi Kolom Kunci
    df_repo_main[REPO_KEY_COL] = clean_key_extreme(df_repo_main[REPO_KEY_COL].fillna(''))
    df_phei_lookup[PHEI_KEY_COL] = clean_key_extreme(df_phei_lookup[PHEI_KEY_COL].fillna(''))
    
    # 2. Hapus duplikat di PHEI agar hasil merge tidak melipatgandakan baris repo
    df_phei_lookup = df_phei_lookup.drop_duplicates(subset=[PHEI_KEY_COL])
    
    # 3. Lakukan Merge (VLOOKUP)
    df_merged = pd.merge(
        df_repo_main,
        df_phei_lookup[[PHEI_KEY_COL, PHEI_VALUE_COL]],
        left_on=REPO_KEY_COL, 
        right_on=PHEI_KEY_COL, 
        how='left'
    )
    
    # 4. PERBAIKAN LOGIKA HARGA (Agar koma setelah 3 angka: 101.xxxxx)
    if PHEI_VALUE_COL in df_merged.columns:
        # Hapus semua pemisah (titik/koma) agar jadi string angka bersih
        # Misal: "101.330,97" -> "10133097"
        val_clean = df_merged[PHEI_VALUE_COL].astype(str).str.replace(r'[^0-9]', '', regex=True)
        numeric_val = pd.to_numeric(val_clean, errors='coerce')
        
        # Bagi 100.000 agar angka 10133097 menjadi 101.33097
        df_merged['Fair Price PHEI'] = numeric_val / 100000
    
    return df_merged

# ============================
# ANTARMUKA UTAMA (STREAMLIT)
# ============================
def main():
    st.title("🔄 Otomatisasi Repo Daily Position")
    st.markdown("Fokus: **Mengisi Kolom Fair Price PHEI (J) & Update Tanggal (A2).**")

    col1, col2 = st.columns(2)
    with col1:
        repo_file_upload = st.file_uploader('1. 📂 Unggah Template Repo', type=['xlsx'])
    with col2:
        phei_lookup_file = st.file_uploader('2. 📈 Unggah File PHEI Hari Ini', type=['xlsx', 'csv'])

    st.markdown("---")

    if repo_file_upload and phei_lookup_file:
        try:
            # --- PEMBACAAN FILE REPO ---
            # Menggunakan header=9 agar baris 10 menjadi nama kolom
            repo_bytes = repo_file_upload.getvalue()
            df_repo_raw = pd.read_excel(BytesIO(repo_bytes), header=HEADER_ROW_INDEX)
            df_repo_raw.columns = df_repo_raw.columns.str.replace('\n', ' ').str.strip()
            
            # Ambil hanya baris yang memiliki nomor urut (No) agar baris 'Total' tidak ikut masuk
            df_data_only = df_repo_raw[df_repo_raw['No'].notna()].copy()
            
            # --- PEMBACAAN FILE PHEI ---
            if phei_lookup_file.name.endswith('.csv'):
                df_phei = pd.read_csv(phei_lookup_file, encoding='latin1')
            else:
                df_phei = pd.read_excel(phei_lookup_file)
            df_phei.columns = df_phei.columns.str.strip()

            if st.button("Jalankan Proses Update", type="primary"):
                # 1. Proses Data
                df_result = process_repo_data(df_data_only, df_phei)
                
                # 2. Tulis ke Excel menggunakan Openpyxl
                wb = load_workbook(BytesIO(repo_bytes))
                sheet = wb.active
                
                # Cari posisi kolom 'Fair Price PHEI' secara dinamis (Biasanya Kolom J)
                try:
                    fair_price_col_idx = df_repo_raw.columns.get_loc('Fair Price PHEI') + 1
                except KeyError:
                    st.error("Kolom 'Fair Price PHEI' tidak ditemukan di template!")
                    return

                # 3. Update Baris Tanggal (A2)
                today_date = datetime.now().strftime('%d %b %Y')
                date_text = f"Daily As of Date : {today_date} - {today_date}"
                sheet.cell(row=2, column=1, value=date_text) # Kolom 1 adalah A

                # 4. Update Kolom Fair Price (J) per baris
                for i, val in enumerate(df_result['Fair Price PHEI']):
                    current_row = START_ROW_EXCEL + i
                    # Tulis nilai hanya jika tidak NaN
                    final_val = val if pd.notna(val) else None
                    sheet.cell(row=current_row, column=fair_price_col_idx, value=final_val)

                # 5. Output Download
                output_buffer = BytesIO()
                wb.save(output_buffer)
                
                st.success(f"✅ Berhasil memproses {len(df_result)} baris data.")
                
                st.download_button(
                    label="⬇️ Unduh File Update",
                    data=output_buffer.getvalue(),
                    file_name=f"Repo_Updated_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                # Preview untuk verifikasi
                st.subheader("Preview Hasil (Kolom J)")
                st.dataframe(df_result[['No', REPO_KEY_COL, 'Fair Price PHEI']])

        except Exception as e:
            st.error(f"Terjadi kesalahan: {e}")

if __name__ == '__main__':
    main()
