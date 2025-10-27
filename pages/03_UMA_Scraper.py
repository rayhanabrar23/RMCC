# pages/03_UMA_Scraper.py

import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO

# --- FUNGSI UTAMA STREAMLIT (Diberi nama 'app') ---
def app():
    st.title("📂 UMA (Unusual Market Activity) - File Upload")
    st.markdown("""
    Karena adanya pemblokiran server (Error 403), fungsi *Scraper* otomatis dinonaktifkan.
    
    **Langkah:**
    1. Unduh data UMA dari website IDX (atau siapkan file Anda).
    2. Unggah file XLSX/CSV tersebut di bawah.
    """)

    # File Uploader
    uploaded_file = st.file_uploader(
        "Unggah File Data UMA (.xlsx atau .csv)",
        type=['xlsx', 'csv']
    )
    
    # Kontrol Input (Filter)
    col1, col2 = st.columns(2)
    current_year = datetime.now().year
    
    target_month_num = col1.selectbox(
        "Pilih Bulan Target (untuk penamaan file):",
        range(1, 13),
        format_func=lambda x: datetime(current_year, x, 1).strftime("%B")
    )
    
    target_year = col2.selectbox(
        "Pilih Tahun Target (untuk penamaan file):",
        range(current_year, current_year - 3, -1)
    )
    
    target_month_name = datetime(target_year, target_month_num, 1).strftime("%b")

    if uploaded_file is not None:
        
        st.info("✅ File berhasil diunggah. Tampilkan data...")
        
        try:
            # Membaca file
            if uploaded_file.name.endswith('.csv'):
                df_uma = pd.read_csv(uploaded_file)
            else:
                df_uma = pd.read_excel(uploaded_file)
            
            # Penggantian nama kolom jika ini adalah data mentah dari API IDX
            if 'AnnouncementDate' in df_uma.columns:
                df_uma.rename(columns={
                    'AnnouncementDate': 'Tanggal', 
                    'Description': 'Keterangan UMA',
                    'Code': 'Kode Emiten' 
                }, inplace=True)

            # Tampilkan data yang diunggah
            st.subheader("Data UMA yang Diunggah:")
            st.dataframe(df_uma, use_container_width=True)
            
            # Sediakan tombol download
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                df_uma.to_excel(writer, sheet_name=f'UMA_Uploaded', index=False)
            
            excel_buffer.seek(0)

            st.download_button(
                label=f"💾 Unduh Data UMA Hasil Olahan",
                data=excel_buffer,
                file_name=f"Output_UMA_Diunggah_{target_month_name}_{target_year}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"❌ Gagal memproses file. Pastikan format kolom benar. Error: {e}")
