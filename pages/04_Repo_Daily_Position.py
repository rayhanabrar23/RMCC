# pages/04_Repo_Daily_Position.py (FINAL FULL CODE - FIX ISIN CODE NOT IN INDEX)

import streamlit as st
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from io import BytesIO
from datetime import datetime
import os 
import sys

# ============================
# KONSTANTA 
# ============================
REPO_KEY_COL = 'Instrument Code' 
PHEI_KEY_COL = 'ISIN CODE' # Nama yang konsisten (setelah dibersihkan)
NOMINAL_AMOUNT_COL = 'Nominal Amount' 
PHEI_VALUE_COL = 'TODAY FAIR PRICE' 
START_ROW_EXCEL = 12 
START_COL_EXCEL = 10 # Kolom J
# ============================

def clean_and_rename_isin(df_phei: pd.DataFrame) -> pd.DataFrame:
    """Membersihkan header PHEI dan mencari serta menamakan ulang kolom ISIN."""
    
    # Bersihkan spasi di awal/akhir semua header
    df_phei.columns = df_phei.columns.str.strip()
    
    # Cari kolom yang mengandung kata 'ISIN' (case-insensitive)
    isin_cols = [col for col in df_phei.columns if 'ISIN' in col.upper()]
    
    if not isin_cols:
        st.error(f"Kolom yang mengandung 'ISIN' TIDAK ditemukan di File PHEI. Header yang ditemukan: {df_phei.columns.tolist()}")
        # Jika ISIN tidak ditemukan, kita biarkan df_phei apa adanya, validasi nanti akan gagal
        return df_phei 
    
    # Jika ISIN ditemukan, ganti nama kolom pertama yang ditemukan menjadi PHEI_KEY_COL
    old_isin_col = isin_cols[0]
    if old_isin_col != PHEI_KEY_COL:
        df_phei.rename(columns={old_isin_col: PHEI_KEY_COL}, inplace=True)
        st.success(f"Kolom '{old_isin_col}' berhasil diubah namanya menjadi '{PHEI_KEY_COL}'.")
        
    return df_phei

# ============================
# FUNGSI PENGOLAHAN DATA
# ============================

def process_repo_data(df_repo_main: pd.DataFrame, df_phei_lookup: pd.DataFrame) -> pd.DataFrame:
    # ... (Fungsi ini tidak berubah, hanya bergantung pada PHEI_KEY_COL yang sudah diperbaiki) ...
    st.info(f"Melakukan VLOOKUP/Merge data: '{REPO_KEY_COL}' (Repo) -> '{PHEI_KEY_COL}' (PHEI)...")
    
    # 1. Persiapan File PHEI (Lookup)
    df_phei_lookup = df_phei_lookup.dropna(subset=[PHEI_KEY_COL, PHEI_VALUE_COL]).copy()
    
    # 2. Lakukan Merge (simulasi VLOOKUP)
    df_merged = pd.merge(
        df_repo_main,
        df_phei_lookup[[PHEI_KEY_COL, PHEI_VALUE_COL]],
        left_on=REPO_KEY_COL, 
        right_on=PHEI_KEY_COL, 
        how='left'
    )
    
    if PHEI_KEY_COL in df_merged.columns:
         df_merged.drop(columns=[PHEI_KEY_COL], inplace=True)
    
    # 3. Logika Perhitungan
    NEW_VALUE_COL = PHEI_VALUE_COL 

    if NEW_VALUE_COL in df_merged.columns:
        
        # --- DEBUGGING: Cek keberhasilan Lookup ---
        initial_match_count = df_merged[NEW_VALUE_COL].count()
        total_rows = len(df_merged)
        st.write(f"📊 **Statistik Lookup Awal:** {initial_match_count} dari {total_rows} baris ({initial_match_count/total_rows:.2%}) berhasil dicocokkan.")
        # ------------------------------------------

        df_merged[NEW_VALUE_COL] = pd.to_numeric(df_merged[NEW_VALUE_COL], errors='coerce')
        df_merged[NEW_VALUE_COL] = df_merged[NEW_VALUE_COL] / 1000000000000 
        
        st.success(f"'{NEW_VALUE_COL}' berhasil dihitung dan dibagi 1T.")
    
    return df_merged

def format_output(df_result_raw: pd.DataFrame) -> pd.DataFrame:
    return df_result_raw.copy()

# ============================
# ANTARMUKA UTAMA
# ============================

def main():
    st.title("🔄 Otomatisasi Repo Daily Position")
    st.markdown("Unggah file data utama dan file *lookup* harian PHEI untuk menggantikan `VLOOKUP`.")

    col1, col2 = st.columns(2)

    with col1:
        repo_file_upload = st.file_uploader(
            '1. Unggah File Repo Position Template (.xlsx)', 
            type=['xlsx'], 
            key='Reverse Repo Bonds Daily Position'
        )
    with col2:
        phei_lookup_file = st.file_uploader(
            '2. Unggah File Lookup Harian PHEI (CSV/Excel)', 
            type=['xlsx', 'csv'], 
            key='20251027_SeriesAll_PEI',
            help="File PHEI berisi ISIN CODE dan TODAY FAIR PRICE yang dipisahkan oleh koma."
        )
    
    st.markdown("---")

    if repo_file_upload and phei_lookup_file:
        try:
            repo_file_buffer = BytesIO(repo_file_upload.getvalue())
            
            # 1. Baca data dari template Repo
            df_repo_main = pd.read_excel(repo_file_buffer, engine='openpyxl', header=10) 
            df_repo_main.columns = df_repo_main.columns.str.replace('\n', ' ').str.strip()

            # -----------------------------------------------------------------
            # KODE REVISI UNTUK MEMBACA FILE LOOKUP PHEI
            # -----------------------------------------------------------------
            if phei_lookup_file.name.endswith('.csv'):
                # FIX ENCODING: encoding='latin1'
                df_phei_lookup = pd.read_csv(phei_lookup_file, delimiter=',', encoding='latin1')
            else:
                df_phei_lookup = pd.read_excel(phei_lookup_file, engine='openpyxl')
            
            # --- FIX 2: Memastikan PHEI_KEY_COL ada dan konsisten ---
            df_phei_lookup = clean_and_rename_isin(df_phei_lookup)
            # --------------------------------------------------------
            
            # --- VALIDASI KOLOM FILE UTAMA ---
            if REPO_KEY_COL not in df_repo_main.columns or NOMINAL_AMOUNT_COL not in df_repo_main.columns:
                 st.error(f"Kolom kunci ('{REPO_KEY_COL}' atau '{NOMINAL_AMOUNT_COL}') TIDAK DITEMUKAN di Repo File.")
                 st.info("Kolom yang ditemukan di File Repo: " + str(df_repo_main.columns.tolist()))
                 return

            df_repo_main = df_repo_main.dropna(subset=[REPO_KEY_COL, NOMINAL_AMOUNT_COL]).copy()
            
            # --- VALIDASI KOLOM FILE LOOKUP ---
            if PHEI_VALUE_COL not in df_phei_lookup.columns or PHEI_KEY_COL not in df_phei_lookup.columns:
                st.error(f"Kolom kunci **'{PHEI_KEY_COL}'** atau nilai **'{PHEI_VALUE_COL}'** TIDAK DITEMUKAN di file lookup PHEI.")
                st.info("Kolom yang ditemukan di File PHEI: " + str(df_phei_lookup.columns.tolist()))
                return
            
            
            if st.button("Jalankan Otomatisasi Lookup", type="primary"):
                st.success("Mulai Pemrosesan Data...")
                
                # 2. Lakukan Proses Lookup
                df_result_raw = process_repo_data(df_repo_main, df_phei_lookup)
                
                # 3. Muat Workbook Openpyxl dari template
                repo_file_buffer.seek(0) 
                wb = load_workbook(repo_file_buffer)
                sheet = wb.active 
                
                # 4. Ambil Kolom Hasil Lookup
                df_lookup_result = df_result_raw[PHEI_VALUE_COL]
                
                # 5. Tulis hasil lookup ke dalam template
                for r_idx, value in enumerate(df_lookup_result.tolist()):
                    row_number = START_ROW_EXCEL + r_idx 
                    col_number = START_COL_EXCEL 
                    
                    # Konversi NaN ke None agar sel di Excel kosong
                    cell_value = value if pd.notna(value) else None 
                    
                    sheet.cell(row=row_number, column=col_number, value=cell_value)
                    
                st.success(f"Data hasil lookup berhasil di-embed ke dalam template Excel mulai dari sel J{START_ROW_EXCEL}.")
                
                # 6. Siapkan file untuk di-download
                output_buffer = BytesIO()
                wb.save(output_buffer)
                output_buffer.seek(0)
                
                date_str = datetime.now().strftime('%Y%m%d')

                st.download_button(
                    label="⬇️ Unduh Hasil Otomatisasi (.xlsx) - Template Updated",
                    data=output_buffer,
                    file_name=f'Repo_Daily_Position_Automated_{date_str}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                
                st.subheader("Hasil Dataframe (Untuk Verifikasi)")
                st.dataframe(df_result_raw[[REPO_KEY_COL, PHEI_KEY_COL, NOMINAL_AMOUNT_COL, PHEI_VALUE_COL]])


        except Exception as e:
            st.error(f"Terjadi kesalahan saat membaca atau memproses file. Error: {e}")
            st.warning("Pastikan Anda mengunggah file yang benar dan header berada di baris ke-11. Jika error ini muncul lagi, kemungkinan data kunci di kedua file tidak cocok.")

if __name__ == '__main__':
    main()
