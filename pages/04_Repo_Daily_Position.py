import streamlit as st
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from io import BytesIO
from datetime import datetime

# ============================
# KONSTANTA (SESUAI GAMBAR)
# ============================
# Pastikan nama kolom di bawah ini PERSIS sama dengan yang ada di Excel
REPO_KEY_COL = 'Instrument Code' 
PHEI_KEY_COL = 'SERIES' 
PHEI_VALUE_COL = 'TODAY FAIR PRICE' 

# Berdasarkan gambar: Header (No, KPEI Contract, dll) ada di baris 10
# Dalam pandas (0-indexed), baris 10 Excel = index 9
HEADER_ROW_INDEX = 9 
START_ROW_EXCEL = 11 # Data pertama (No. 1) mulai di baris 11 Excel

# ============================
# FUNGSI PEMBERSIH
# ============================
def clean_key_extreme(series):
    return series.astype(str).str.strip().str.upper().replace(r'[^A-Z0-9]', '', regex=True)

# ============================
# PROSES DATA
# ============================
def process_repo_data(df_repo_main, df_phei_lookup):
    # 1. Bersihkan kunci tanpa menghapus baris agar data tidak hilang
    df_repo_main[REPO_KEY_COL] = clean_key_extreme(df_repo_main[REPO_KEY_COL].fillna(''))
    df_phei_lookup[PHEI_KEY_COL] = clean_key_extreme(df_phei_lookup[PHEI_KEY_COL].fillna(''))
    
    # 2. Hapus duplikat di file PHEI agar tidak menyebabkan baris Repo bertambah (double)
    df_phei_lookup = df_phei_lookup.drop_duplicates(subset=[PHEI_KEY_COL])
    
    # 3. Merge / VLOOKUP
    df_merged = pd.merge(
        df_repo_main,
        df_phei_lookup[[PHEI_KEY_COL, PHEI_VALUE_COL]],
        left_on=REPO_KEY_COL, 
        right_on=PHEI_KEY_COL, 
        how='left'
    )
    
    # 4. Cleaning Nilai Fair Price (Contoh: 101,3681)
    if PHEI_VALUE_COL in df_merged.columns:
        # Menangani format Indonesia (titik ribuan, koma desimal)
        val_clean = df_merged[PHEI_VALUE_COL].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df_merged['CLEAN_PRICE'] = pd.to_numeric(val_clean, errors='coerce')
        
        # Update kolom Fair Price PHEI (Kolom J)
        # Jika nilai di PHEI adalah 101.36, kita langsung pakai. 
        # (Hilangkan pembagi triliun kecuali data mentahnya memang angka bulat panjang)
        df_merged['Fair Price PHEI'] = df_merged['CLEAN_PRICE']
        
    return df_merged

def main():
    st.title("🔄 Repo Daily Automation (Updated)")
    
    file_repo = st.file_uploader("1. Unggah Template Repo", type=['xlsx'])
    file_phei = st.file_uploader("2. Unggah Data PHEI", type=['xlsx', 'csv'])

    if file_repo and file_phei:
        try:
            # BACA REPO: Gunakan header yang benar agar baris tidak hilang
            df_repo = pd.read_excel(file_repo, header=HEADER_ROW_INDEX)
            df_repo.columns = df_repo.columns.str.replace('\n', ' ').str.strip()
            
            # FILTER: Hanya ambil baris yang ada nomor urutnya (menghindari baris kosong/total)
            # Ini penting agar baris 'Total' tidak ikut diproses sebagai data
            df_data = df_repo[df_repo['No'].notna()].copy()
            
            # BACA PHEI
            if file_phei.name.endswith('.csv'):
                df_phei = pd.read_csv(file_phei, encoding='latin1')
            else:
                df_phei = pd.read_excel(file_phei)
            df_phei.columns = df_phei.columns.str.strip()

            if st.button("Proses & Perbarui Kolom J"):
                # Jalankan penggabungan data
                df_result = process_repo_data(df_data, df_phei)
                
                # Load workbook untuk menulis tanpa merusak format
                file_repo.seek(0)
                wb = load_workbook(file_repo)
                ws = wb.active
                
                # Cari posisi kolom 'Fair Price PHEI' secara dinamis
                try:
                    target_col_idx = df_repo.columns.get_loc('Fair Price PHEI') + 1
                except:
                    st.error("Kolom 'Fair Price PHEI' tidak ditemukan!")
                    return

                # Tulis hasil ke Excel mulai dari START_ROW_EXCEL
                for i, val in enumerate(df_result['Fair Price PHEI']):
                    ws.cell(row=START_ROW_EXCEL + i, column=target_col_idx, value=val)
                
                # Update Tanggal di A2 (Opsional)
                today_str = datetime.now().strftime('%d %b %Y')
                ws['A2'] = f"Daily As of Date : {today_str} - {today_str}"

                # Download
                out = BytesIO()
                wb.save(out)
                st.download_button("⬇️ Download Hasil", out.getvalue(), "Repo_Updated.xlsx")
                st.success(f"Berhasil memproses {len(df_result)} baris data.")
                st.dataframe(df_result[['No', REPO_KEY_COL, 'Fair Price PHEI']])

        except Exception as e:
            st.error(f"Error: {e}")

if __name__ == '__main__':
    main()
