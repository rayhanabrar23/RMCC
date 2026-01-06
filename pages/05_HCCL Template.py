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
# 2. PROTEKSI HALAMAN & STYLE
# ===============================================================
if "login_status" not in st.session_state or not st.session_state["login_status"]:
    st.error("🚨 Akses Ditolak! Silakan login di halaman utama terlebih dahulu.")
    st.stop()

try:
    from style_utils import apply_custom_style
    apply_custom_style()
except ImportError:
    st.warning("Fungsi apply_custom_style tidak ditemukan, menggunakan gaya default.")

# ============================
# KONFIGURASI GLOBAL CL
# ============================
COL_RMCC = 'CONCENTRATION LIMIT USULAN RMCC'
KODE_EFEK_KHUSUS = ['LPKR', 'MLPL', 'NOBU', 'PTPP', 'SILO']
OVERRIDE_MAPPING = {
    'LPKR': 10_000_000_000, 'MLPL': 10_000_000_000,
    'NOBU': 10_000_000_000, 'PTPP': 50_000_000_000, 'SILO': 10_000_000_000
}

# ============================
# FUNGSI PERHITUNGAN
# ============================
def calculate_concentration_limit(df_cl_source: pd.DataFrame) -> pd.DataFrame:
    """
    Logika perhitungan Concentration Limit.
    Sesuaikan bagian ini dengan rumus bisnis Anda.
    """
    df = df_cl_source.copy()
    
    # Contoh logika sederhana: jika kode ada di override_mapping, gunakan nilai tersebut
    # Jika tidak, gunakan nilai default (misal 5M)
    # Anda bisa mengganti ini dengan logika asli Anda
    if 'KODE' in df.columns:
        df[COL_RMCC] = df['KODE'].map(OVERRIDE_MAPPING).fillna(5_000_000_000)
    
    return df

def update_excel_template(file_template: BytesIO, df_cl_hasil: pd.DataFrame) -> BytesIO:
    """
    Memasukkan data hasil perhitungan ke dalam template Excel yang diunggah.
    """
    # 1. Load workbook dari memori
    wb = load_workbook(file_template)
    
    # 2. Tentukan sheet target (Misal: 'CONC')
    # Sesuaikan nama sheet dengan yang ada di file Excel Anda
    sheet_name = 'CONC'
    if sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        
        # Opsi: Bersihkan data lama mulai baris 2 (jika diperlukan)
        # ws.delete_rows(2, ws.max_row) 

        # 3. Tulis data dari DataFrame ke Excel
        # Dimulai dari baris 2, kolom 1
        for r_idx, row in enumerate(df_cl_hasil.values, start=2):
            for c_idx, value in enumerate(row, start=1):
                ws.cell(row=r_idx, column=c_idx, value=value)
    else:
        st.error(f"Sheet '{sheet_name}' tidak ditemukan di template!")

    # 4. BUAT BUFFER & SIMPAN (Solusi untuk error sebelumnya)
    output_buffer = BytesIO()
    wb.save(output_buffer)
    output_buffer.seek(0) # Kembalikan pointer ke awal agar bisa didownload
    
    return output_buffer

# ============================
# ANTARMUKA STREAMLIT
# ============================
def main():
    st.title("🛡️ Concentration Limit (CL) & Haircut Calculation Updater")
    st.markdown("---")
    
    current_month_name = datetime.now().strftime('%B').lower()
    
    st.markdown("""
    **Instruksi:** Unggah kedua file di bawah ini. File **Template Output** Anda akan di-update secara otomatis.
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

    if uploaded_file_cl_source and uploaded_file_cl_template:
        if st.button("🚀 Jalankan Perhitungan & Update Template Excel", type="primary"):
            try:
                # 1. BACA FILE SUMBER
                df_cl_source = pd.read_excel(uploaded_file_cl_source, engine='openpyxl')
                
                # 2. JALANKAN PERHITUNGAN
                with st.spinner('Menghitung Concentration Limit...'):
                    df_cl_hasil = calculate_concentration_limit(df_cl_source)

                st.success("✅ Perhitungan selesai.")
                st.dataframe(df_cl_hasil.head())

                # 3. UPDATE TEMPLATE
                with st.spinner('⏳ Mengupdate File Template Excel...'):
                    # Penting: gunakan .seek(0) jika file sudah pernah dibaca sebelumnya
                    uploaded_file_cl_template.seek(0)
                    output_buffer_template = update_excel_template(uploaded_file_cl_template, df_cl_hasil)
                
                st.success("🎉 File Template Output berhasil di-update!")
                
                # 4. DOWNLOAD BUTTON
                dynamic_filename_output = f'clhc_updated_{current_month_name}.xlsx' 
                st.download_button(
                    label="⬇️ Unduh Hasil Update (Excel)",
                    data=output_buffer_template,
                    file_name=dynamic_filename_output, 
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                
            except Exception as e:
                st.error(f"❌ Detail Error: {e}")
                st.exception(e)

    elif not uploaded_file_cl_source or not uploaded_file_cl_template:
        st.info("⬆️ Silakan unggah kedua file di atas untuk memulai.")

if __name__ == '__main__':
    main()
