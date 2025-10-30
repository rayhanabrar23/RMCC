import streamlit as st
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from io import BytesIO
from datetime import datetime

# ============================
# KONSTANTA
# ============================
REPO_KEY_COL = 'Instrument Code' 
PHEI_KEY_COL = 'SERIES' 
NOMINAL_AMOUNT_COL = 'Nominal Amount' 
PHEI_VALUE_COL = 'TODAY FAIR PRICE' 

START_ROW_EXCEL = 12 
START_COL_EXCEL = 1 
# ============================

# ============================
# FUNGSI PEMBERSIH KUNCI
# ============================
def clean_key_extreme(series):
    series = series.astype(str).str.strip().str.upper()
    series = series.replace(r'[^A-Z0-9]', '', regex=True)
    return series

# ============================
# FUNGSI PENGOLAHAN DATA UTAMA
# ============================
def process_repo_data(df_repo_main: pd.DataFrame, df_phei_lookup: pd.DataFrame) -> pd.DataFrame:
    st.info(f"Melakukan VLOOKUP/Merge data: '{REPO_KEY_COL}' (Repo) -> '{PHEI_KEY_COL}' (PHEI)...")
    st.warning("Membersihkan kolom kunci dan nilai (EKSTREM)...")
    
    if REPO_KEY_COL in df_repo_main.columns:
        df_repo_main[REPO_KEY_COL] = clean_key_extreme(df_repo_main[REPO_KEY_COL])
    
    if PHEI_KEY_COL in df_phei_lookup.columns:
        df_phei_lookup[PHEI_KEY_COL] = clean_key_extreme(df_phei_lookup[PHEI_KEY_COL])
    
    st.subheader("Data Kunci Repo yang Digunakan:")
    st.dataframe(df_repo_main[[REPO_KEY_COL, NOMINAL_AMOUNT_COL]].head())
    
    df_phei_lookup = df_phei_lookup.dropna(subset=[PHEI_KEY_COL, PHEI_VALUE_COL]).copy()
    
    df_merged = pd.merge(
        df_repo_main,
        df_phei_lookup[[PHEI_KEY_COL, PHEI_VALUE_COL]],
        left_on=REPO_KEY_COL, 
        right_on=PHEI_KEY_COL, 
        how='left'
    )
    
    if PHEI_KEY_COL in df_merged.columns:
         df_merged.drop(columns=[PHEI_KEY_COL], inplace=True)
    
    if PHEI_VALUE_COL in df_merged.columns:
        initial_match_count = df_merged[PHEI_VALUE_COL].count()
        total_rows = len(df_merged)
        st.write(f"📊 **Statistik Lookup Akhir:** {initial_match_count} dari {total_rows} baris ({initial_match_count/total_rows:.2%}) berhasil dicocokkan.")

        # Perbaikan Skala Nilai Harga Mentah
        df_merged['RAW_PHEI_VALUE'] = df_merged[PHEI_VALUE_COL].astype(str)
        df_merged['RAW_PHEI_VALUE'] = df_merged['RAW_PHEI_VALUE'].str.replace(',', '', regex=False).str.replace('.', '', regex=False)
        df_merged['RAW_PHEI_VALUE'] = pd.to_numeric(df_merged['RAW_PHEI_VALUE'], errors='coerce') 
        st.info(f"Nilai Mentah PHEI ({PHEI_VALUE_COL}) telah dibersihkan dan dikonversi ke numerik.")
        
        if 'Fair Price PHEI' in df_merged.columns:
             df_merged['Fair Price PHEI'] = df_merged['RAW_PHEI_VALUE'] / 1000000000000 
             st.success(f"Nilai **Fair Price PHEI (Kolom J)** berhasil diperbarui.")
        else:
             st.error("Kolom 'Fair Price PHEI' tidak ditemukan di template.")
             
    return df_merged

# ============================
# ANTARMUKA UTAMA
# ============================

def main():
    st.title("🔄 Otomatisasi Repo Daily Position")
    st.markdown("Fokus: **Mengisi Kolom J (Fair Price PHEI) mulai dari Baris 12 ke bawah & Update Tanggal (A2).**")

    col1, col2 = st.columns(2)

    with col1:
        repo_file_upload = st.file_uploader(
            '1. 📂 Unggah File Repo Template (Output Hari Sebelumnya)', 
            type=['xlsx'], 
            key='Reverse Repo Bonds Daily Position',
            help="Pastikan kolom 'Instrument Code' berisi kode SERIES/ISIN yang benar."
        )
    with col2:
        phei_lookup_file = st.file_uploader(
            '2. 📈 Unggah File Lookup Harian PHEI (Data Hari Ini)', 
            type=['xlsx', 'csv'], 
            key='20251027_SeriesAll_PEI',
            help="File PHEI berisi ISIN CODE, SERIES, dan TODAY FAIR PRICE terbaru."
        )
    
    st.markdown("---")

    if repo_file_upload and phei_lookup_file:
        try:
            repo_file_buffer = BytesIO(repo_file_upload.getvalue())
            df_repo_main = pd.read_excel(repo_file_buffer, header=10) 
            df_repo_main.columns = df_repo_main.columns.str.replace('\n', ' ').str.strip()
            original_repo_cols = df_repo_main.columns.tolist() 

            # --- PEMBACAAN PHEI ---
            if phei_lookup_file.name.endswith('.csv'):
                encodings_to_try = ['latin1', 'cp1252', 'ISO-8859-1', 'utf-8']
                df_phei_lookup = None
                
                for enc in encodings_to_try:
                    try:
                        file_buffer = BytesIO(phei_lookup_file.getvalue())
                        df_phei_lookup_raw = pd.read_csv(file_buffer, delimiter=',', encoding=enc, header=None)
                        df_phei_lookup_raw.columns = df_phei_lookup_raw.iloc[0]
                        df_phei_lookup = df_phei_lookup_raw[1:].copy() 
                        break 
                    except Exception:
                        continue
                if df_phei_lookup is None:
                    raise Exception("Gagal membaca file CSV PHEI.")
            else:
                df_phei_lookup = pd.read_excel(phei_lookup_file)
            
            df_phei_lookup.columns = df_phei_lookup.columns.str.strip() 
            # -----------------------------

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
                
                
                # --- PERBAIKAN MERGED CELL KRITIS ---
                
                # Target Sel A2:O2 (Tanggal)
                merged_range_A2 = 'A2:O2' 
                
                # Target Kolom J (Fair Price PHEI) dari Baris 12 hingga akhir data
                max_row_data = START_ROW_EXCEL + len(df_to_write) - 1
                col_letter_J = chr(ord('@') + fair_price_col_index) 
                
                merged_cells_to_remerge = []
                st.warning("Menghapus sementara penggabungan sel (Merged Cells)...")
                
                for merged_range in list(sheet.merged_cells):
                    # Hapus penggabungan A2:O2 atau sel lain yang tumpang tindih
                    if merged_range.coord == merged_range_A2 or (merged_range.min_col == fair_price_col_index and merged_range.min_row >= START_ROW_EXCEL):
                         merged_cells_to_remerge.append(merged_range.coord)
                         sheet.unmerge_cells(merged_range.coord)
                
                # 4b. Tulis Nilai ke Sel A2 (Tanggal) -> Diubah dari B2 ke A2
                today_date = datetime.now()
                date_str_formatted = today_date.strftime('%d %b %Y') 
                b2_value = f"Daily As of Date : {date_str_formatted} - {date_str_formatted}"
                
                # *** KOREKSI DI SINI: Kolom 1 adalah A ***
                sheet.cell(row=2, column=1, value=b2_value) 
                st.info(f"📅 Sel A2 (Tanggal) berhasil diperbarui menjadi: **{b2_value}**.")
                
                # 4c. Tulis Kolom J (Fair Price PHEI) mulai dari baris 12
                for r_idx, row_data in df_to_write.iterrows():
                    row_number = START_ROW_EXCEL + r_idx 
                    
                    cell_value = row_data['Fair Price PHEI']
                    final_value = cell_value if pd.notna(cell_value) else None 
                        
                    sheet.cell(row=row_number, column=fair_price_col_index, value=final_value)

                st.success(f"✅ Data Fair Price PHEI (Kolom J) berhasil ditimpa ke dalam template Excel.")

                # 4d. Gabungkan kembali sel yang dihapus (untuk format)
                for merged_range_coord in merged_cells_to_remerge:
                    sheet.merge_cells(merged_range_coord)
                st.success("✅ Penggabungan sel asli (Merged Cells) berhasil dikembalikan.")
                # ------------------------------------

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
                st.dataframe(df_result_raw[['Instrument Code', 'RAW_PHEI_VALUE', 'Fair Price PHEI']])

        except Exception as e:
            st.error(f"Terjadi kesalahan saat membaca atau memproses file. Error: {e}")
            st.warning("Pastikan Anda mengunggah file Repo output kemarin sebagai File 1 dan File PHEI terbaru sebagai File 2.")

if __name__ == '__main__':
    main()
