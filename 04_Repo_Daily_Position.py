# pages/02_Repo_Daily_Position.py (REVISI PADA FUNGSI main)

# ... (Import dan Fungsi lainnya TIDAK BERUBAH) ...

# ============================
# ANTARMUKA UTAMA (REVISI BAGIAN BACA FILE)
# ============================

def main():
    st.title("🔄 Otomatisasi Repo Daily Position")
    st.markdown("Unggah file data utama dan file *lookup* harian PHEI untuk menggantikan `VLOOKUP`.")

    col1, col2 = st.columns(2)

    with col1:
        repo_file = st.file_uploader(
            '1. Unggah File Repo Position Template (.xlsx)', 
            type=['xlsx'], 
            key='repo_main'
        )
    with col2:
        # File harian PHEI (Simulasi untuk Lookup)
        # Tambahkan 'csv' ke tipe yang diterima, ini sudah ada di kode sebelumnya.
        phei_lookup_file = st.file_uploader(
            '2. Unggah File Lookup Harian PHEI (CSV/Excel)', 
            type=['xlsx', 'csv'], 
            key='phei_lookup',
            help="File ini berisi Instrument Code dan Fair Price PHEI. Jika CSV, pastikan menggunakan koma sebagai pemisah."
        )
    
    st.markdown("---")

    if repo_file and phei_lookup_file:
        try:
            # Baca file utama
            df_repo_main = pd.read_excel(repo_file, engine='openpyxl')
            
            # -----------------------------------------------------------------
            # KODE REVISI UNTUK MEMBACA FILE LOOKUP DENGAN PEMISAH KOMA
            # -----------------------------------------------------------------
            if phei_lookup_file.name.endswith('.csv'):
                # Gunakan pd.read_csv dengan delimiter=',' untuk meniru Text-to-Column di Excel
                df_phei_lookup = pd.read_csv(phei_lookup_file, delimiter=',')
            else:
                df_phei_lookup = pd.read_excel(phei_lookup_file, engine='openpyxl')
            # -----------------------------------------------------------------
            
            # Hapus baris kosong/header yang tidak perlu dari file utama
            df_repo_main = df_repo_main.dropna(subset=[LOOKUP_KEY, NOMINAL_AMOUNT_COL]).copy()
            
            # Pastikan kolom lookup ada
            if LOOKUP_VALUE_COL not in df_phei_lookup.columns:
                 st.warning(f"Kolom **'{LOOKUP_VALUE_COL}'** tidak ditemukan di file lookup PHEI. Cek kembali nama kolomnya.")
                 st.info("Pastikan file CSV/Excel PHEI memiliki kolom bernama 'Fair Price PHEI' dan 'Instrument Code'.")
                 return
            
            # ... (Logika process_repo_data dan download tetap sama) ...
            
            if st.button("Jalankan Otomatisasi Lookup", type="primary"):
                
                df_result_raw = process_repo_data(df_repo_main, df_phei_lookup)
                
                df_final_output = format_output(df_result_raw.copy())
                
                st.subheader("Hasil Akhir (Siap Download)")
                st.dataframe(df_final_output)

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
            st.error(f"Terjadi kesalahan saat membaca atau memproses file. Pastikan nama sheet, header, dan format data sudah benar. Error: {e}")

if __name__ == '__main__':
    main()