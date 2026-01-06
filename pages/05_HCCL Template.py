import streamlit as st
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from io import BytesIO
from datetime import datetime

# ===============================================================
# 1. KONFIGURASI HALAMAN (WAJIB PALING ATAS)
# ===============================================================
st.set_page_config(page_title="HC CL Updater", layout="wide")

# ===============================================================
# 2. PROTEKSI HALAMAN & STYLE
# ===============================================================

# Simulasi login status (Pastikan session_state ini diatur di main app Anda)
if "login_status" not in st.session_state:
    st.session_state["login_status"] = True  # Ubah ke False jika ingin proteksi aktif

if not st.session_state["login_status"]:
    st.error("🚨 Akses Ditolak! Silakan login di halaman utama terlebih dahulu.")
    st.stop()

# ============================
# 3. KONFIGURASI GLOBAL CL
# ============================
COL_KODE = 'KODE EFEK'
COL_RMCC = 'CONCENTRATION LIMIT USULAN RMCC'
COL_PERHITUNGAN = 'CONCENTRATION LIMIT SESUAI PERHITUNGAN'
THRESHOLD_5M = 5_000_000_000
KODE_EFEK_KHUSUS = ['LPKR', 'MLPL', 'NOBU', 'PTPP', 'SILO']
OVERRIDE_MAPPING = {
    'LPKR': 10_000_000_000, 
    'MLPL': 10_000_000_000,
    'NOBU': 10_000_000_000, 
    'PTPP': 50_000_000_000, 
    'SILO': 10_000_000_000
}

# ============================
# 4. FUNGSI LOGIKA PERHITUNGAN
# ============================

def calculate_concentration_limit(df_source: pd.DataFrame) -> pd.DataFrame:
    """Mengolah data CL berdasarkan aturan bisnis."""
    df = df_source.copy()
    
    # Pastikan kolom yang dibutuhkan ada
    if COL_KODE not in df.columns or COL_RMCC not in df.columns:
        st.error(f"File sumber harus memiliki kolom '{COL_KODE}' dan '{COL_RMCC}'")
        st.stop()

    def logic_cl(row):
        kode = str(row[COL_KODE]).strip()
        usulan_rmcc = row[COL_RMCC]
        
        # 1. Cek jika masuk dalam daftar override khusus
        if kode in OVERRIDE_MAPPING:
            return OVERRIDE_MAPPING[kode]
        
        # 2. Logika default (Contoh: minimal 5M atau sesuai usulan)
        return max(usulan_rmcc, THRESHOLD_5M) if pd.notnull(usulan_rmcc) else THRESHOLD_5M

    df[COL_PERHITUNGAN] = df.apply(logic_cl, axis=1)
    return df

def update_excel_template(file_template: BytesIO, df_cl_hasil: pd.DataFrame) -> BytesIO:
    """Mengupdate sheet 'CONC' pada template Excel."""
    # Load workbook dari file yang diupload
    wb = load_workbook(file_template)
    
    # Pilih sheet 'CONC' (atau buat jika tidak ada untuk mencegah error)
    if 'CONC' in wb.sheetnames:
        ws = wb['CONC']
    else:
        ws = wb.create_sheet('CONC')
        st.warning("Sheet 'CONC' tidak ditemukan, sistem membuat sheet baru.")

    # Tulis Header (Opsional)
    headers = df_cl_hasil.columns.tolist()
    for col_num, column_title in enumerate(headers, 1):
        ws.cell(row=1, column=col_num, value=column_title)

    # Tulis Data dari DataFrame
    for r_idx, row in enumerate(df_cl_hasil.values, start=2):
        for c_idx, value in enumerate(row, start=1):
            # Mengonversi numpy types ke standar python agar openpyxl tidak error
            if isinstance(value, (np.int64, np.float64)):
                value = float(value)
            ws.cell(row=r_idx, column=c_idx, value=value)

    # Simpan hasil ke buffer
    output_buffer = BytesIO()
    wb.save(output_buffer)
    output_buffer.seek(0)
    return output_buffer

# ============================
# 5. ANTARMUKA STREAMLIT
# ============================

def main():
    st.title("🛡️ Concentration Limit (CL) & Haircut Calculation Updater")
    st.markdown("---")
    
    current_month_name = datetime.now().strftime('%B').lower()
    
    st.markdown("""
    **Instruksi:** 1. Unggah **File Sumber** (Data mentah hasil perhitungan).
    2. Unggah **File Template** (File tujuan yang ingin diisi datanya).
    3. Klik tombol Jalankan untuk memproses.
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
            "2. Unggah File Template Output (Tujuan)",
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
                with st.spinner('Menghitung Concentration Limit...'):
                    df_cl_hasil = calculate_concentration_limit(df_cl_source)

                st.success("✅ Perhitungan Selesai.")
                st.write("Preview Hasil (5 baris teratas):")
                st.dataframe(df_cl_hasil.head())

                # 3. UPDATE TEMPLATE
                with st.spinner('⏳ Mengupdate File Template Excel...'):
                    # PENTING: Reset pointer template agar bisa dibaca ulang
                    uploaded_file_cl_template.seek(0)
                    output_buffer_template = update_excel_template(uploaded_file_cl_template, df_cl_hasil)
                
                st.success("🎉 File Berhasil Di-update!")
                
                dynamic_filename_output = f'clhc_updated_{current_month_name}.xlsx' 
                
                st.download_button(
                    label="⬇️ Unduh Hasil Update (.xlsx)",
                    data=output_buffer_template,
                    file_name=dynamic_filename_output, 
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                
            except Exception as e:
                st.error(f"❌ Detail Error: {e}")
                st.exception(e)

    elif uploaded_file_cl_source is None or uploaded_file_cl_template is None:
        st.info("⬆️ Silakan unggah kedua file di atas untuk mengaktifkan tombol proses.")

if __name__ == '__main__':
    main()
