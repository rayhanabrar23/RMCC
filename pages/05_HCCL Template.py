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

# Login Check
if "login_status" not in st.session_state:
    st.session_state["login_status"] = True 

if not st.session_state["login_status"]:
    st.error("🚨 Akses Ditolak! Silakan login terlebih dahulu.")
    st.stop()

# ============================
# 2. KONFIGURASI GLOBAL
# ============================
COL_KODE = 'KODE EFEK'
COL_RMCC = 'CONCENTRATION LIMIT USULAN RMCC'
COL_LISTED = 'CONCENTRATION LIMIT TERKENA % LISTED SHARES'
COL_FF = 'CONCENTRATION LIMIT TERKENA % FREE FLOAT'
COL_PERHITUNGAN = 'CONCENTRATION LIMIT SESUAI PERHITUNGAN'

OVERRIDE_MAPPING = {
    'LPKR': 10_000_000_000, 'MLPL': 10_000_000_000,
    'NOBU': 10_000_000_000, 'PTPP': 50_000_000_000, 'SILO': 10_000_000_000
}

# ============================
# 3. FUNGSI INTI (LOGIKA & EXCEL)
# ============================

def calculate_concentration_limit(df):
    """Fungsi perhitungan lengkap"""
    df_hasil = df.copy()
    
    # Pastikan kolom RMCC ada, jika tidak buat kolom dummy 0
    if COL_RMCC not in df_hasil.columns:
        df_hasil[COL_RMCC] = 0

    def apply_logic(row):
        kode = str(row.get(COL_KODE, '')).strip()
        # Jika ada di daftar override
        if kode in OVERRIDE_MAPPING:
            return OVERRIDE_MAPPING[kode]
        # Jika tidak, ambil dari RMCC
        return row.get(COL_RMCC, 0)

    df_hasil[COL_PERHITUNGAN] = df_hasil.apply(apply_logic, axis=1)
    
    # Tambahkan kolom lain jika belum ada (agar tidak error saat update excel)
    for col in [COL_LISTED, COL_FF]:
        if col not in df_hasil.columns:
            df_hasil[col] = 0
            
    return df_hasil

def update_excel_template(file_template, df_hasil):
    """Proses penulisan ke Excel dengan penanganan buffer yang benar"""
    # 1. Buat buffer baru
    output = BytesIO()
    
    # 2. Load template
    wb = load_workbook(file_template)
    
    # 3. Update Sheet CONC
    if 'CONC' in wb.sheetnames:
        ws = wb['CONC']
        # Tulis Header
        for c_idx, column_title in enumerate(df_hasil.columns, 1):
            ws.cell(row=1, column=c_idx, value=column_title)
        
        # Tulis Data
        for r_idx, row in enumerate(df_hasil.values, start=2):
            for c_idx, value in enumerate(row, start=1):
                # Handle numpy types agar tidak error saat save
                if isinstance(value, (np.int64, np.float64)):
                    value = float(value)
                ws.cell(row=r_idx, column=c_idx, value=value)
    
    # 4. Simpan ke buffer
    wb.save(output)
    output.seek(0)
    return output

# ============================
# 4. ANTARMUKA STREAMLIT (UI)
# ============================

def main():
    st.title("🛡️ HC CL Updater Professional")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        source_file = st.file_uploader("Upload File Sumber (XLSX)", type=['xlsx'])
    with col2:
        template_file = st.file_uploader("Upload Template Target (XLSX)", type=['xlsx'])

    if source_file and template_file:
        if st.button("🚀 Jalankan Proses Update", type="primary"):
            try:
                # Proses 1: Baca
                df_input = pd.read_excel(source_file)
                
                # Proses 2: Hitung
                with st.spinner("Menghitung data..."):
                    df_final = calculate_concentration_limit(df_input)
                
                # Proses 3: Update Excel
                with st.spinner("Menyusun file Excel..."):
                    # Reset pointer file template
                    template_file.seek(0)
                    processed_file = update_excel_template(template_file, df_final)
                
                st.success("✅ Berhasil! File siap diunduh.")
                
                # Preview
                st.dataframe(df_final.head(10))

                # Download Button
                st.download_button(
                    label="⬇️ Download Updated Excel",
                    data=processed_file,
                    file_name=f"Update_CL_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            except Exception as e:
                st.error(f"Terjadi Kesalahan: {e}")
                st.exception(e)

if __name__ == "__main__":
    main()
