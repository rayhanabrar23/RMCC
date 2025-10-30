# pages/04_Repo_Daily_Position.py (FINAL FULL CODE - FIX NameError)

import streamlit as st
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from io import BytesIO
from datetime import datetime

# ============================
# KONSTANTA (WAJIB DIDEFINISIKAN)
# ============================
REPO_KEY_COL = 'Instrument Code' 
PHEI_KEY_COL = 'ISIN CODE' 
NOMINAL_AMOUNT_COL = 'Nominal Amount' 
PHEI_VALUE_COL = 'TODAY FAIR PRICE' 

# BARIS DAN KOLOM TEMPLATE TARGET
START_ROW_EXCEL = 12 # Baris A12 di Excel
START_COL_EXCEL = 1 # Kolom A di Excel
# ============================

# ============================
# FUNGSI PENGOLAHAN DATA
# ============================

def process_repo_data(df_repo_main: pd.DataFrame, df_phei_lookup: pd.DataFrame) -> pd.DataFrame:
    st.info(f"Melakukan VLOOKUP/Merge data: '{REPO_KEY_COL}' (Repo) -> '{PHEI_KEY_COL}' (PHEI)...")
    
    # Persiapan File PHEI
    df_phei_lookup = df_phei_lookup.dropna(subset=[PHEI_KEY_COL, PHEI_VALUE_COL]).copy()
    
    # Merge (simulasi VLOOKUP)
    df_merged = pd.merge(
        df_repo_main,
        df_phei_lookup[[PHEI_KEY_COL, PHEI_VALUE_COL]],
        left_on=REPO_KEY_COL, 
        right_on=PHEI_KEY_COL, 
        how='left'
    )
    
    # Hapus kolom kunci duplikat
    if PHEI_KEY_COL in df_merged.columns:
         df_merged.drop(columns=[PHEI_KEY_COL], inplace=True)
    
    # Logika Perhitungan
    if PHEI_VALUE_COL in df_merged.columns:
        initial_match_count = df_merged[PHEI_VALUE_COL].count()
        total_rows = len(df_merged)
        st.write(f"📊 **Statistik Lookup Awal:** {initial_match_count} dari {total_rows} baris ({initial_match_count/total_rows:.2%}) berhasil dicocokkan.")

        df_merged[PHEI_VALUE_COL] = pd.to_numeric(df_merged[PHEI_VALUE_COL], errors='coerce') # <-- Sudah diperbaiki di sini
        
        # Ganti nama kolom Fair Price PHEI yang asli dengan hasil lookup
        # Pastikan kolom 'Fair Price PHEI' ada di df_repo_main agar bisa ditimpa
        # Jika 'Fair Price PHEI' adalah kolom J (indeks 9)
        if 'Fair Price PHEI' in df_merged.columns:
             # FIX TYPO DI BARIS INI: Menggunakan PHEI_VALUE_COL (sebelumnya PPEI_VALUE_COL)
             df_merged['Fair Price PHEI'] = df_merged[PHEI_VALUE_COL] / 1000000000000 
        else:
             df_merged[PHEI_VALUE_COL] = df_merged[PHEI_VALUE_COL] / 1000000000000
        
        st.success(f"'{PHEI_VALUE_COL}' berhasil dihitung dan dibagi 1T.")
    
    return df_merged
# ... (Akhir fungsi process_repo_data) ...


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
            
            # 1. Baca data dari template (untuk diproses)
            df_repo_main = pd.read_excel(repo_file_buffer, header=10) 
            df_repo_main.columns = df_repo_main.columns.str.replace('\n', ' ').str.strip()
            original_repo_cols = df_repo_main.columns.tolist()

            # -----------------------------------------------------------------
            # KODE REVISI UNTUK MEMBACA FILE LOOKUP PHEI (HARDENED)
            # -----------------------------------------------------------------
            if phei_lookup_file.name.endswith('.csv'):
                encodings_to_try = ['latin1', 'cp1252', 'ISO-8859-1', 'utf-8']
                df_phei_lookup = None
                for enc in encodings_to_try:
                    try:
                        file_buffer = BytesIO(phei_lookup_file.getvalue())
                        df_phei_lookup = pd.read_csv(file_buffer, delimiter=',', encoding=enc)
                        break 
                    except Exception:
                        continue
                if df_phei_lookup is None:
                    raise Exception("Gagal membaca file CSV PHEI dengan semua opsi encoding yang dicoba.")
            else:
                df_phei_lookup = pd.read_excel(phei_lookup_file)
            
            df_phei_lookup.columns = df_phei_lookup.columns.str.strip() 
            # -----------------------------------------------------------------

            # --- VALIDASI & PREP ---
            if REPO_KEY_COL not in df_repo_main.columns or NOMINAL_AMOUNT_COL not in df_repo_main.columns:
                 st.error(f"Kolom kunci ('{REPO_KEY_COL}' atau '{NOMINAL_AMOUNT_COL}') TIDAK DITEMUKAN di Repo File.")
                 return

            df_repo_main = df_repo_main.dropna(subset=[REPO_KEY_COL, NOMINAL_AMOUNT_COL]).copy()
            
            if PHEI_VALUE_COL not in df_phei_lookup.columns or PHEI_KEY_COL not in df_phei_lookup.columns:
                st.error(f"Kolom kunci **'{PHEI_KEY_COL}'** atau nilai **'{PHEI_VALUE_COL}'** TIDAK DITEMUKAN di file lookup PHEI.")
                st.info("Kolom yang ditemukan di File PHEI: " + str(df_phei_lookup.columns.tolist()))
                return
            
            
            if st.button("Jalankan Otomatisasi Lookup & Isi Template", type="primary"):
                st.success("Mulai Pemrosesan Data...")
                
                # 2. Lakukan Proses Lookup
                df_result_raw = process_repo_data(df_repo_main, df_phei_lookup)
                
                # --- MEMPERSIAPKAN DATA UNTUK DITIMPA ---
                df_to_write = df_result_raw[original_repo_cols].copy() 

                # 3. Muat Workbook Openpyxl dari template
                repo_file_buffer.seek(0) # Reset pointer
                wb = load_workbook(repo_file_buffer)
                sheet = wb.active # Asumsi sheet yang digunakan adalah yang aktif
                
                # 4. Tulis data ke dalam template mulai dari baris 12 (START_ROW_EXCEL)
                
                for r_idx, row_data in df_to_write.iterrows():
                    row_number = START_ROW_EXCEL + r_idx 
                    
                    for c_idx, cell_value in enumerate(row_data):
                        col_number = START_COL_EXCEL + c_idx 
                        
                        # Konversi NaN ke None agar sel di Excel kosong
                        final_value = cell_value if pd.notna(cell_value) else None 
                        
                        # Tulis nilai ke sel
                        sheet.cell(row=row_number, column=col_number, value=final_value)

                st.success(f"Data hasil lookup dan perhitungan berhasil ditimpa ke dalam template Excel, mulai dari sel A{START_ROW_EXCEL} ke bawah.")
                
                # 5. Siapkan file untuk di-download
                output_buffer = BytesIO()
                wb.save(output_buffer)
                output_buffer.seek(0)
                
                date_str = datetime.now().strftime('%Y%m%d')

                st.download_button(
                    label="⬇️ Unduh File Template Repo (.xlsx) - Data Updated",
                    data=output_buffer,
                    file_name=f'Repo_Daily_Position_Template_Updated_{date_str}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                
                st.subheader("Hasil Dataframe (Verifikasi Data yang Ditulis)")
                st.dataframe(df_to_write)

        except Exception as e:
            st.error(f"Terjadi kesalahan saat membaca atau memproses file. Error: {e}")
            st.warning("Pastikan kolom kunci di File Repo ('Instrument Code') dan File PHEI ('ISIN CODE') sudah bersih dari spasi dan karater aneh.")

if __name__ == '__main__':
    main()
