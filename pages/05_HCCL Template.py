import streamlit as st
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from io import BytesIO
from datetime import datetime

# ===============================================================
# 1. KONFIGURASI HALAMAN
# ===============================================================
st.set_page_config(page_title="HC CL Updater", layout="wide")

# ===============================================================
# 2. PROTEKSI HALAMAN (SIMULASI LOGIN)
# ===============================================================
if "login_status" not in st.session_state:
    st.session_state["login_status"] = True  # Set True untuk testing, False untuk produksi

if not st.session_state["login_status"]:
    st.error("🚨 Akses Ditolak! Silakan login terlebih dahulu.")
    st.stop()

# ============================
# KONFIGURASI GLOBAL CL
# ============================
COL_KODE = 'KODE EFEK'
COL_RMCC = 'CONCENTRATION LIMIT USULAN RMCC'
COL_PERHITUNGAN = 'CONCENTRATION LIMIT SESUAI PERHITUNGAN'

OVERRIDE_MAPPING = {
    'LPKR': 10_000_000_000, 'MLPL': 10_000_000_000,
    'NOBU': 10_000_000_000, 'PTPP': 50_000_000_000, 'SILO': 10_000_000_000
}

# ============================
# FUNGSI LOGIKA PERHITUNGAN
# ============================

def calculate_concentration_limit(df: pd.DataFrame) -> pd.DataFrame:
    """Fungsi untuk menghitung CL berdasarkan logika bisnis."""
    df_hasil = df.copy()
    
    # Contoh logika: Jika kode ada di mapping, gunakan nilai override
    # Jika tidak, gunakan nilai dari kolom RMCC (atau logika lainnya)
    def apply_logic(row):
        kode = str(row.get(COL_KODE, ''))
        if kode in OVERRIDE_MAPPING:
            return OVERRIDE_MAPPING[kode]
        return row.get(COL_RMCC, 0)

    df_hasil[COL_PERHITUNGAN] = df_hasil.apply(apply_logic, axis=1)
    return df_hasil

def update_excel_template(file_template: BytesIO, df_cl_hasil: pd.DataFrame) -> BytesIO:
    """Menulis hasil dataframe ke dalam sheet Excel yang sudah ada."""
    output_buffer = BytesIO()
    
    # Load workbook dari buffer
    wb = load_workbook(file_template)
    
    # Pastikan Sheet 'CONC' ada
    if 'CONC' in wb.sheetnames:
        ws = wb['CONC']
        # Contoh sederhana: Tulis data mulai dari baris ke-2
        for r_idx, row in enumerate(df_cl_hasil.values, start=2):
            for c_idx, value in enumerate(row, start=1):
                ws.cell(row=r_idx, column=c_idx, value=value)
    
    wb.save(output_buffer)
    output_buffer.seek(0)
    return output_buffer

# ============================
# ANTARMUKA STREAMLIT
# ============================

def main():
    st.title("🛡️ Concentration Limit (CL) & Haircut Calculation Updater")
    st.markdown("---")
    
    current_month_name = datetime.now().strftime('%B').lower()
    
    st.info("💡 Pastikan file sumber memiliki kolom **'KODE EFEK'** dan **'CONCENTRATION LIMIT USULAN RMCC'**")

    col1, col2 = st.columns(2)
    with col1:
        uploaded_file_cl_source = st.file_uploader("1. Unggah File Sumber Data (Input)", type=['xlsx'])
    with col2:
        uploaded_file_cl_template = st.file_uploader("2. Unggah Template Output (Excel)", type=['xlsx'])

    if uploaded_file_cl_source and uploaded_file_cl_template:
        if st.button("🚀 Jalankan Perhitungan", type="primary"):
            try:
                # 1. Baca File
                df_source = pd.read_excel(uploaded_file_cl_source)
                
                # 2. Proses
                with st.spinner('Menghitung...'):
                    df_hasil = calculate_concentration_limit(df_source)
                
                st.success("✅ Perhitungan Selesai!")
                st.dataframe(df_hasil.head(10)) # Tampilkan preview 10 data

                # 3. Update Excel
                with st.spinner('⏳ Mengupdate Template...'):
                    output_xlsx = update_excel_template(uploaded_file_cl_template, df_hasil)
                
                # 4. Download
                st.download_button(
                    label="⬇️ Unduh File Terupdate",
                    data=output_xlsx,
                    file_name=f'clhc_updated_{current_month_name}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                
            except Exception as e:
                st.error(f"Terjadi kesalahan: {e}")

if __name__ == '__main__':
    main()
