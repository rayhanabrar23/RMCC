# pages/04_Repo_Daily_Position.py (KODE FINAL DENGAN KONSTANTA KUNCI BARU)

import streamlit as st
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from io import BytesIO
from datetime import datetime

# ============================
# KONSTANTA (DISESUAIKAN BERDASARKAN VLOOKUP MANUAL)
# ============================
REPO_KEY_COL = 'Instrument Code' 
# Kunci di File PHEI (Kolom B/Series)
PHEI_KEY_COL = 'SERIES' 
NOMINAL_AMOUNT_COL = 'Nominal Amount' 
# Nilai yang diambil dari File PHEI (TODAY LOW PRICE - indeks 9 di VLOOKUP Anda)
PHEI_VALUE_COL = 'TODAY LOW PRICE' 

START_ROW_EXCEL = 12 
START_COL_EXCEL = 1 
# ============================

# ============================
# FUNGSI PENGOLAHAN DATA
# ============================

def clean_key_extreme(series):
    # Pembersihan Ekstrem untuk mengatasi karakter tak terlihat/spasi
    series = series.astype(str).str.strip().str.upper()
    # Menghapus semua karakter yang BUKAN huruf atau angka
    series = series.replace(r'[^A-Z0-9]', '', regex=True)
    return series

def process_repo_data(df_repo_main: pd.DataFrame, df_phei_lookup: pd.DataFrame) -> pd.DataFrame:
    st.info(f"Melakukan VLOOKUP/Merge data: '{REPO_KEY_COL}' (Repo) -> '{PHEI_KEY_COL}' (PHEI)...")
    
    st.warning("Membersihkan kolom kunci (EKSTREM: menghapus semua karakter non-alfanumerik)...")
    
    # 1. Bersihkan Kunci di File REPO
    if REPO_KEY_COL in df_repo_main.columns:
        df_repo_main[REPO_KEY_COL] = clean_key_extreme(df_repo_main[REPO_KEY_COL])
    
    # 2. Bersihkan Kunci di File PHEI
    if PHEI_KEY_COL in df_phei_lookup.columns:
        df_phei_lookup[PHEI_KEY_COL] = clean_key_extreme(df_phei_lookup[PHEI_KEY_COL])
    
    # --- DIAGNOSA: Tampilkan data kunci Repo yang sudah dibersihkan ---
    st.subheader("Data Kunci Repo yang Digunakan (EKSTREM CLEANING):")
    st.dataframe(df_repo_main[[REPO_KEY_COL, NOMINAL_AMOUNT_COL]].head())
    st.caption(f"Kunci Repo: **{REPO_KEY_COL}** | Kunci PHEI: **{PHEI_KEY_COL}** | Nilai Diambil: **{PHEI_VALUE_COL}**")
    # -----------------------------------------------------------------

    df_phei_lookup = df_phei_lookup.dropna(subset=[PHEI_KEY_COL, PHEI_VALUE_COL]).copy()
    
    df_merged = pd.merge(
        df_repo_main,
        df_phei_lookup[[PHEI_KEY_COL, PHEI_VALUE_COL]],
        left_on=REPO_KEY_COL, 
        right_on=PHEI_KEY_COL, 
        how='left'
    )
    
    # Drop kolom PHEI_KEY_COL yang duplikat setelah merge
    if PHEI_KEY_COL in df_merged.columns:
         df_merged.drop(columns=[PHEI_KEY_COL], inplace=True)
    
    if PHEI_VALUE_COL in df_merged.columns:
        initial_match_count = df_merged[PHEI_VALUE_COL].count()
        total_rows = len(df_merged)
        st.write(f"📊 **Statistik Lookup Akhir:** {initial_match_count} dari {total_rows} baris ({initial_match_count/total_rows:.2%}) berhasil dicocokkan.")

        df_merged[PHEI_VALUE_COL] = pd.to_numeric(df_merged[PHEI_VALUE_COL], errors='coerce') 
        
        if 'Fair Price PHEI' in df_merged.columns:
             # Nilai dari PHEI_VALUE_COL (TODAY LOW PRICE) dibagi 1T dan diisikan ke kolom 'Fair Price PHEI'
             df_merged['Fair Price PHEI'] = df_merged[PHEI_VALUE_COL] / 1000000000000 
             st.success(f"Nilai **Fair Price PHEI (Kolom J)** berhasil diperbarui dari kolom **{PHEI_VALUE_COL}**.")
        else:
             st.error("Kolom 'Fair Price PHEI' tidak ditemukan di template.")
             
    return df_merged

# ============================
# ANTARMUKA UTAMA
# ============================

def main():
    st.title("🔄 Otomatisasi Repo Daily Position")
    st.markdown("Fokus: **Mengisi Kolom J (Fair Price PHEI) mulai dari Baris 12 ke bawah.**")

    col1, col2 = st.columns(2)

    with col1:
        repo_file_upload = st.file_uploader(
            '1. 📂 Unggah File Repo Template (Output Hari Sebelumnya)', 
            type=['xlsx'], 
            key='Reverse Repo Bonds Daily Position',
            help="Pastikan kolom 'Instrument Code' berisi ISIN CODE yang benar."
        )
    with col2:
        phei_lookup_file = st.file_uploader(
            '2. 📈 Unggah File Lookup Harian PHEI (Data Hari Ini)', 
            type=['xlsx', 'csv'], 
            key='20251027_SeriesAll_PEI',
            help="File PHEI berisi ISIN CODE dan TODAY FAIR PRICE terbaru."
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
            # KODE REVISI UNTUK MEMBACA FILE LOOKUP PHEI (FINAL FIX)
            # -----------------------------------------------------------------
            if phei_lookup_file.name.endswith('.csv'):
                encodings_to_try = ['latin1', 'cp1252', 'ISO-8859-1', 'utf-8']
                df_phei_lookup = None
                
                for enc in encodings_to_try:
                    try:
                        file_buffer = BytesIO(phei_lookup_file.getvalue())
                        # Baca tanpa header, pisahkan koma, lalu gunakan baris pertama sebagai header
                        df_phei_lookup_raw = pd.read_csv(file_buffer, delimiter=',', encoding=enc, header=None)
                        
                        # Set header menggunakan baris pertama (indeks 0)
                        df_phei_lookup_raw.columns = df_phei_lookup_raw.iloc[0]
                        df_phei_lookup = df_phei_lookup_raw[1:].copy() 
                        break 
                    except Exception as e:
                        continue
                if df_phei_lookup is None:
                    raise Exception("Gagal membaca file CSV PHEI.")
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
                st.info("Kolom yang ditemukan di File PHEI (setelah parsing): " + str(df_phei_lookup.columns.tolist()))
                return
            
            
            if st.button("Jalankan Otomatisasi Lookup & Isi Kolom J", type="primary"):
                st.success("Mulai Pemrosesan Data...")
                
                # 2. Lakukan Proses Lookup
                df_result_raw = process_repo_data(df_repo_main, df_phei_lookup)
                
                # --- MEMPERSIAPKAN DATA UNTUK DITIMPA ---
                df_to_write = df_result_raw[original_repo_cols].copy() 

                # 3. Muat Workbook Openpyxl dari template
                repo_file_buffer.seek(0) 
                wb = load_workbook(repo_file_buffer)
                sheet = wb.active 
                
                # Mendapatkan indeks kolom 'Fair Price PHEI' (Kolom J)
                try:
                    fair_price_col_index = original_repo_cols.index('Fair Price PHEI') + 1 
                except ValueError:
                    st.error("Gagal menemukan kolom 'Fair Price PHEI' (Kolom J) di template.")
                    return
                
                # 4. Tulis HANYA KOLOM J ke dalam template mulai dari baris 12
                START_ROW_EXCEL = 12
                
                for r_idx, row_data in df_to_write.iterrows():
                    row_number = START_ROW_EXCEL + r_idx 
                    
                    cell_value = row_data['Fair Price PHEI']
                    final_value = cell_value if pd.notna(cell_value) else None 
                        
                    sheet.cell(row=row_number, column=fair_price_col_index, value=final_value)

                st.success(f"✅ Data Fair Price PHEI (Kolom J) berhasil ditimpa ke dalam template Excel.")
                
                # 5. Siapkan file untuk di-download
                output_buffer = BytesIO()
                wb.save(output_buffer)
                output_buffer.seek(0)
                
                date_str = datetime.now().strftime('%Y%m%d')

                st.download_button(
                    label="⬇️ Unduh File Template Repo Hari Ini (.xlsx)",
                    data=output_buffer,
                    file_name=f'Repo_Daily_Position_Tgl{date_str}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                
                st.subheader("Hasil Dataframe (Verifikasi Data Kolom J)")
                st.dataframe(df_to_write[['Instrument Code', 'Fair Price PHEI']])

        except Exception as e:
            st.error(f"Terjadi kesalahan saat membaca atau memproses file. Error: {e}")
            st.warning("Pastikan Anda mengunggah file Repo output kemarin sebagai File 1 dan File PHEI terbaru sebagai File 2.")

if __name__ == '__main__':
    main()
