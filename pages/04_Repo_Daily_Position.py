# pages/04_Repo_Daily_Position.py (FINAL FULL CODE - FIX HEADER EXCEL)

import streamlit as st
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment, Border, Side, NamedStyle, numbers
from io import BytesIO
from datetime import datetime
import os 
import sys

# ============================
# KONSTANTA (WAJIB DIDEFINISIKAN)
# ============================
# Kunci di file UTAMA (Reverse Repo Bonds Daily Position) - Kolom E12
REPO_KEY_COL = 'Instrument Code' 
# Kunci di file PHEI (20251028_SeriesAll_PEI) - Kolom C setelah Text-to-Column
PHEI_KEY_COL = 'ISIN CODE' 
# Kolom di file utama yang berisi nominal amount (untuk dropna)
NOMINAL_AMOUNT_COL = 'Nominal Amount' 
# NILAI yang diambil dari file PHEI - Kolom J setelah Text-to-Column
PHEI_VALUE_COL = 'TODAY FAIR PRICE' 

# ============================
# FUNGSI PENGOLAHAN DATA
# ============================

def process_repo_data(df_repo_main: pd.DataFrame, df_phei_lookup: pd.DataFrame) -> pd.DataFrame:
    """
    Melakukan VLOOKUP (Merge) antara data Repo (Instrument Code) 
    dengan data Fair Price PHEI (ISIN CODE).
    """
    st.info(f"Melakukan VLOOKUP/Merge data: '{REPO_KEY_COL}' (Repo) -> '{PHEI_KEY_COL}' (PHEI)...")
    
    # 1. Persiapan File PHEI (Lookup)
    df_phei_lookup.columns = df_phei_lookup.columns.str.strip() 
    # Dropna untuk memastikan kunci dan nilai PHEI valid
    df_phei_lookup = df_phei_lookup.dropna(subset=[PHEI_KEY_COL, PHEI_VALUE_COL]).copy()
    
    # 2. Lakukan Merge (simulasi VLOOKUP)
    df_merged = pd.merge(
        df_repo_main,
        df_phei_lookup[[PHEI_KEY_COL, PHEI_VALUE_COL]],
        left_on=REPO_KEY_COL, # Kunci di file Repo
        right_on=PHEI_KEY_COL, # Kunci di file PHEI
        how='left'
    )
    
    # Hapus kolom ISIN CODE yang baru ditambahkan dari PHEI (agar tidak duplikat)
    if PHEI_KEY_COL in df_merged.columns:
         df_merged.drop(columns=[PHEI_KEY_COL], inplace=True)
    
    # 3. Logika Perhitungan (Menyesuaikan VLOOKUP Excel Anda)
    
    if PHEI_VALUE_COL in df_merged.columns:
        
        # Mengubah kolom TODAY FAIR PRICE menjadi numerik
        df_merged[PHEI_VALUE_COL] = pd.to_numeric(df_merged[PHEI_VALUE_COL], errors='coerce')

        # === Perhitungan: Nilai VLOOKUP dibagi 1 Triliun ===
        df_merged[PHEI_VALUE_COL] = df_merged[PHEI_VALUE_COL] / 1000000000000 
        
        st.success(f"'{PHEI_VALUE_COL}' berhasil ditambahkan dan dibagi 1T. Hasil terisi otomatis ke semua baris.")
        
    return df_merged

def format_output(df_result_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Melakukan formatting akhir pada DataFrame sebelum ditampilkan/didownload.
    """
    st.info("Melakukan formatting hasil akhir...")
    return df_result_raw.copy()

# ============================
# ANTARMUKA UTAMA
# ============================

def main():
    st.title("🔄 Otomatisasi Repo Daily Position")
    st.markdown("Unggah file data utama dan file *lookup* harian PHEI untuk menggantikan `VLOOKUP`.")

    col1, col2 = st.columns(2)

    with col1:
        repo_file = st.file_uploader(
            '1. Unggah File Repo Position Template (.xlsx)', 
            type=['xlsx'], 
            key='Reverse Repo Bonds Daily Position'
        )
    with col2:
        phei_lookup_file = st.file_uploader(
            '2. Unggah File Lookup Harian PHEI (CSV/Excel)', 
            type=['xlsx', 'csv'], 
            key='20251027_SeriesAll_PEI',
            help="File PHEI berisi ISIN CODE dan TODAY FAIR PRICE yang dipisahkan oleh koma. Harap unggah file yang sudah di-Text-to-Column di Excel."
        )
    
    st.markdown("---")

    if repo_file and phei_lookup_file:
        try:
            # Baca file utama (Reverse Repo Bonds Daily Position Template)
            # FIX HEADER: Header di baris 11 (indeks 10)
            df_repo_main = pd.read_excel(repo_file, engine='openpyxl', header=10) 
            
            # -----------------------------------------------------------------
            # KODE REVISI UNTUK MEMBACA FILE LOOKUP PHEI
            # -----------------------------------------------------------------
            if phei_lookup_file.name.endswith('.csv'):
                # FIX ENCODING: encoding='latin1' untuk file CSV/TXT
                df_phei_lookup = pd.read_csv(phei_lookup_file, delimiter=',', encoding='latin1')
                
            else:
                df_phei_lookup = pd.read_excel(phei_lookup_file, engine='openpyxl')
            
            # Pastikan kolom di lookup file bersih dari spasi di header
            df_phei_lookup.columns = df_phei_lookup.columns.str.strip() 
            # -----------------------------------------------------------------
            
            # --- VALIDASI KOLOM FILE UTAMA ---
            if REPO_KEY_COL not in df_repo_main.columns or NOMINAL_AMOUNT_COL not in df_repo_main.columns:
                 # Ini adalah baris yang menghasilkan error Anda, jika error muncul lagi,
                 # kemungkinan nama kolom di Excel Anda ada spasi di akhir ('Instrument Code ')
                 st.error(f"Kolom kunci ('{REPO_KEY_COL}' atau '{NOMINAL_AMOUNT_COL}') tidak ditemukan di File Repo Position Template. Harap cek header file Anda.")
                 st.info("Kolom yang ditemukan di File Repo: " + str(df_repo_main.columns.tolist()))
                 return

            df_repo_main = df_repo_main.dropna(subset=[REPO_KEY_COL, NOMINAL_AMOUNT_COL]).copy()
            
            # --- VALIDASI KOLOM FILE LOOKUP ---
            if PHEI_VALUE_COL not in df_phei_lookup.columns or PHEI_KEY_COL not in df_phei_lookup.columns:
                st.warning(f"Kolom kunci **'{PHEI_KEY_COL}'** atau nilai **'{PHEI_VALUE_COL}'** tidak ditemukan di file lookup PHEI. ")
                st.info("Kolom yang ditemukan di File PHEI: " + str(df_phei_lookup.columns.tolist()))
                return
            
            
            if st.button("Jalankan Otomatisasi Lookup", type="primary"):
                st.success("Mulai Pemrosesan Data...")
                
                df_result_raw = process_repo_data(df_repo_main, df_phei_lookup)
                
                df_final_output = format_output(df_result_raw.copy())
                
                st.subheader("Hasil Akhir (Siap Download)")
                st.dataframe(df_final_output)

                # Siapkan file untuk di-download
                output_buffer = BytesIO()
                with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
                    df_final_output.to_excel(writer, sheet_name='Repo Result', index=False)
                output_buffer.seek(0)
                
                date_str = datetime.now().strftime('%Y%m%d')

                st.download_button(
                    label="⬇️ Unduh Hasil Otomatisasi (.xlsx)",
                    data=output_buffer,
                    file_name=f'Repo_Daily_Position_Automated_{date_str}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )

        except Exception as e:
            st.error(f"Terjadi kesalahan saat membaca atau memproses file. Error: {e}")
            st.warning("Jika error ini muncul lagi, coba pastikan file Excel Repo tidak memiliki sel gabungan di sekitar baris header.")

if __name__ == '__main__':
    main()
