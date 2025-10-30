# pages/04_Repo_Daily_Position.py (FINAL FIX - Revert Formatting & Harden Encoding)

import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime

# ============================
# KONSTANTA (WAJIB DIDEFINISIKAN)
# ============================
REPO_KEY_COL = 'Instrument Code' 
PHEI_KEY_COL = 'ISIN CODE' 
NOMINAL_AMOUNT_COL = 'Nominal Amount' 
PHEI_VALUE_COL = 'TODAY FAIR PRICE' 
# ============================

# ============================
# FUNGSI PENGOLAHAN DATA (Disederhanakan untuk Debug)
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
        
        # --- DEBUGGING: Cek keberhasilan Lookup ---
        initial_match_count = df_merged[PHEI_VALUE_COL].count()
        total_rows = len(df_merged)
        st.write(f"📊 **Statistik Lookup Awal:** {initial_match_count} dari {total_rows} baris ({initial_match_count/total_rows:.2%}) berhasil dicocokkan.")
        # ------------------------------------------

        df_merged[PHEI_VALUE_COL] = pd.to_numeric(df_merged[PHEI_VALUE_COL], errors='coerce')
        df_merged[PHEI_VALUE_COL] = df_merged[PHEI_VALUE_COL] / 1000000000000 
        
        st.success(f"'{PHEI_VALUE_COL}' berhasil dihitung dan dibagi 1T.")
    
    return df_merged

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
            help="File PHEI berisi ISIN CODE dan TODAY FAIR PRICE yang dipisahkan oleh koma."
        )
    
    st.markdown("---")

    if repo_file and phei_lookup_file:
        try:
            # Baca file utama
            # FIX HEADER: Header di baris 11 (indeks 10)
            df_repo_main = pd.read_excel(repo_file, header=10) 
            
            # --- FIX 1: Membersihkan header file Repo ---
            df_repo_main.columns = df_repo_main.columns.str.replace('\n', ' ').str.strip()
            # -------------------------------------------

            # -----------------------------------------------------------------
            # KODE REVISI UNTUK MEMBACA FILE LOOKUP PHEI (HARDENED)
            # -----------------------------------------------------------------
            if phei_lookup_file.name.endswith('.csv'):
                
                # Coba berbagai encoding jika latin1 gagal
                encodings_to_try = ['latin1', 'cp1252', 'ISO-8859-1', 'utf-8']
                df_phei_lookup = None
                
                for enc in encodings_to_try:
                    try:
                        st.info(f"Mencoba membaca CSV PHEI dengan delimiter=',' dan encoding='{enc}'...")
                        # Baca file sebagai string buffer untuk menghindari masalah file lock pada Streamlit
                        file_buffer = BytesIO(phei_lookup_file.getvalue())
                        df_phei_lookup = pd.read_csv(file_buffer, delimiter=',', encoding=enc)
                        break # Berhasil, keluar dari loop
                    except Exception as e:
                        # Jika gagal, coba encoding berikutnya
                        st.warning(f"Gagal dengan encoding '{enc}': {e}")
                        continue
                
                if df_phei_lookup is None:
                    raise Exception("Gagal membaca file CSV PHEI dengan semua opsi encoding yang dicoba.")
                    
            else:
                df_phei_lookup = pd.read_excel(phei_lookup_file)
            
            # Pastikan kolom di lookup file bersih dari spasi di header
            df_phei_lookup.columns = df_phei_lookup.columns.str.strip() 
            # -----------------------------------------------------------------

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
                
                df_result_raw = process_repo_data(df_repo_main, df_phei_lookup)
                
                # --- OUTPUT DATA BARU DALAM FORMAT DATAFRAME BARU ---
                # Karena template formatting bermasalah, kita kembalikan output ke DataFrame baru 
                # (sama seperti yang digunakan orang sebelumnya yang berhasil)
                st.subheader("Hasil Akhir (Dataframe Baru)")
                df_final_output = df_result_raw.copy()
                
                st.dataframe(df_final_output)

                # Siapkan file untuk di-download
                output_buffer = BytesIO()
                with pd.ExcelWriter(output_buffer, engine='openpyxl') as writer:
                    df_final_output.to_excel(writer, sheet_name='Repo Result', index=False)
                output_buffer.seek(0)
                
                date_str = datetime.now().strftime('%Y%m%d')

                st.download_button(
                    label="⬇️ Unduh Hasil Otomatisasi (.xlsx) - Dataframe Baru",
                    data=output_buffer,
                    file_name=f'Repo_Daily_Position_Automated_{date_str}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )

        except Exception as e:
            st.error(f"Terjadi kesalahan saat membaca atau memproses file. Error: {e}")
            st.warning("Silakan cek pesan *debug* di atas. Jika error ISIN CODE muncul lagi, periksa kembali *header* file PHEI Anda.")

if __name__ == '__main__':
    main()
