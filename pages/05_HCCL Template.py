import streamlit as st
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string
from io import BytesIO
from datetime import datetime
import base64

# ===============================================================
# 1. KONFIGURASI HALAMAN (WAJIB PALING ATAS)
# ===============================================================
st.set_page_config(page_title="HC CL Updater", layout="wide")

# ===============================================================
# 2. PROTEKSI HALAMAN & STYLE (EKSEKUSI SETELAH CONFIG)
# ===============================================================

# Cek login
if "login_status" not in st.session_state or not st.session_state["login_status"]:
    st.error("🚨 Akses Ditolak! Silakan login di halaman utama terlebih dahulu.")
    st.stop()

# Import fungsi style (pastikan file style_utils.py ada di folder utama)
try:
    from style_utils import apply_custom_style
    apply_custom_style()
except ImportError:
    st.warning("Fungsi apply_custom_style tidak ditemukan, menggunakan gaya default.")

# ============================
# KONFIGURASI GLOBAL CL
# ============================
COL_RMCC = 'CONCENTRATION LIMIT USULAN RMCC'
COL_LISTED = 'CONCENTRATION LIMIT TERKENA % LISTED SHARES'
COL_FF = 'CONCENTRATION LIMIT TERKENA % FREE FLOAT'
COL_PERHITUNGAN = 'CONCENTRATION LIMIT SESUAI PERHITUNGAN'
THRESHOLD_5M = 5_000_000_000
KODE_EFEK_KHUSUS = ['LPKR', 'MLPL', 'NOBU', 'PTPP', 'SILO']
OVERRIDE_MAPPING = {
    'LPKR': 10_000_000_000, 'MLPL': 10_000_000_000,
    'NOBU': 10_000_000_000, 'PTPP': 50_000_000_000, 'SILO': 10_000_000_000
}
TARGET_100 = 100.0
TOLERANCE = 1e-6 

# ... (Fungsi utilitas calc_concentration_limit_listed, dll tetap sama) ...
# [Simpan semua fungsi perhitunganmu di sini]

def calculate_concentration_limit(df_cl_source: pd.DataFrame) -> pd.DataFrame:
    # ... (Isi fungsi calculate_concentration_limit tetap sama) ...
    df = df_cl_source.copy()
    # [Lanjutkan kode fungsi perhitunganmu]
    return df # (Pastikan return dataframe hasil)

def update_excel_template(file_template: BytesIO, df_cl_hasil: pd.DataFrame) -> BytesIO:
    # ... (Isi fungsi update_excel_template tetap sama) ...
    wb = load_workbook(file_template)
    # [Lanjutkan kode fungsi excelmu]
    return output_buffer

# ============================
# ANTARMUKA STREAMLIT
# ============================

def main():
    # JANGAN panggil st.set_page_config di sini lagi karena sudah di baris atas!
    
    st.title("🛡️ Concentration Limit (CL) & Haircut Calculation Updater")
    st.markdown("---")
    
    current_month_name = datetime.now().strftime('%B').lower()
    
    st.markdown("""
    **Instruksi:** Unggah kedua file di bawah ini. File **Template Output** Anda akan di-update pada Sheet `HC` dan `CONC` berdasarkan hasil perhitungan.
    """)

    col1, col2 = st.columns(2)

    with col1:
        uploaded_file_cl_source = st.file_uploader(
            "1. Unggah File Sumber Data CL (Input)",
            type=['xlsx'],
            key='cl_source'
        )

    with col2:
        uploaded_file_cl_template = st.file_uploader(
            "2. Unggah File Template Output (yang akan di-update)",
            type=['xlsx'],
            key='cl_template'
        )

    st.markdown("---")

    if uploaded_file_cl_source is not None and uploaded_file_cl_template is not None:
        if st.button("🚀 Jalankan Perhitungan & Update Template Excel", type="primary"):
            try:
                # 1. BACA FILE SUMBER
                df_cl_source = pd.read_excel(uploaded_file_cl_source, engine='openpyxl')
                
                # 2. JALANKAN PERHITUNGAN
                with st.spinner('Menghitung Concentration Limit dan Haircut...'):
                    # Panggil fungsi perhitungan (pastikan fungsinya sudah didefinisikan di atas)
                    df_cl_hasil = calculate_concentration_limit(df_cl_source)

                st.success("✅ Perhitungan Concentration Limit selesai.")
                st.dataframe(df_cl_hasil.head())

                # 3. UPDATE TEMPLATE
                uploaded_file_cl_template.seek(0) 
                with st.spinner('⏳ Mengupdate File Template Excel...'):
                    output_buffer_template = update_excel_template(uploaded_file_cl_template, df_cl_hasil)
                
                st.success("🎉 File Template Output berhasil di-update!")
                
                dynamic_filename_output = f'clhc_updated_{current_month_name}.xlsx' 
                
                st.download_button(
                    label="⬇️ Unduh File",
                    data=output_buffer_template,
                    file_name=dynamic_filename_output, 
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                
            except Exception as e:
                st.error(f"❌ Detail Error: {e}")
                st.exception(e)

    elif uploaded_file_cl_source is None and uploaded_file_cl_template is None:
        st.info("⬆️ Silakan unggah kedua file untuk memulai.")

if __name__ == '__main__':
    main()
