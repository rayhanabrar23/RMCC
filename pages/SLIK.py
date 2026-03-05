import streamlit as st
import pandas as pd
import zipfile
import io
import re

st.set_page_config(page_title="SLIK Data Processor", layout="wide")

st.title("🛠️ SLIK Data Automator")
st.write("Upload 6 file SLIK (.txt) untuk diproses otomatis sesuai aturan.")

# --- SIDEBAR: KONFIGURASI ---
st.sidebar.header("Konfigurasi Data")
periode = st.sidebar.text_input("Periode (YYYY.MM)", value="2025.11")
target_sid_lama = "SCD2810HAI23003"
target_sid_baru = "SCD100456212317"

st.sidebar.info(f"Proses akan mengganti SID Ajaib dan melakukan penyesuaian spesifik pada file A01 dan F06.")

# --- UPLOAD FILES ---
uploaded_files = st.file_uploader("Pilih 6 file TXT", type=['txt'], accept_multiple_files=True)

def process_slik_files(files, periode):
    processed_files = {}
    
    for file in files:
        filename = file.name
        content = file.getvalue().decode("utf-8")
        lines = content.splitlines()
        new_lines = []

        for line in lines:
            # RULE 1: Global Replace SID Ajaib Sekuritas
            current_line = line.replace(target_sid_lama, target_sid_baru)

            # RULE 2: Spesifik FILE F06
            if ".F06." in filename:
                # Edit Interest BBM
                if "CPD2303CJB66884" in current_line:
                    current_line = current_line.replace(",00", "7,00")
                # Edit Interest MSU
                elif "CPD0104CJB43364" in current_line:
                    current_line = current_line.replace(",00", "7,00")
                
                # Ubah Baris Asep (F06)
                if "IDD1601G7811173" in current_line and "REPCT202503000001" in current_line:
                    current_line = "D|REPCT202312000006|IDD1601G7811173|005|016357|20231227|20251219|12,00|IDR|3231979475||5|20240606|99|3231979475|512|00|||000|U"

            # RULE 3: Spesifik FILE A01
            elif ".A01." in filename:
                # Ubah Baris Asep (A01)
                if "IDD1601G7811173" in current_line and "Asep Sulaeman Sabanda" in current_line:
                    # Kita ganti string sesuai instruksi
                    current_line = "D|REPCT202312000006IPPE20251031|REPCT202312000006|IDD1601G7811173|F06|1|F0419|||99|20231227|Asep Sulaeman Sabanda|PEI01C00300108|Gedung BEI, Tower I, Lt.3, Suite 301, Jl. Jend. Sudirman Kav. 52-53, Jakarta 12190, Indonesia|0394|2860461800|2860461800|20251031||||T||T|T||000|C"

            new_lines.append(current_line)
        
        processed_files[filename] = "\n".join(new_lines)
    
    return processed_files

# --- EKSEKUSI ---
if uploaded_files:
    if len(uploaded_files) != 6:
        st.warning(f"Terdeteksi {len(uploaded_files)} file. Pastikan mengunggah tepat 6 file sesuai standar SLIK.")
    
    if st.button("Proses & Generate Data"):
        result_data = process_slik_files(uploaded_files, periode)
        
        # Simpan ke ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for file_name, data in result_data.items():
                zip_file.writestr(file_name, data)
        
        st.success("✅ Pemrosesan Selesai!")
        st.download_button(
            label="Download Hasil (.zip)",
            data=zip_buffer.getvalue(),
            file_name=f"SLIK_PROCESSED_{periode}.zip",
            mime="application/zip"
        )

# --- PENJELASAN LOGIKA ---
with st.expander("Lihat Detail Logika Perubahan"):
    st.markdown("""
    - **Global:** Semua `SCD2810HAI23003` diganti jadi `SCD100456212317`.
    - **File F06:** - Interest BBM & MSU diubah ke `7,00`.
        - Record Asep (IDD1601G7811173) diupdate ke format 2023 (REPCT202312000006).
    - **File A01:**
        - Record Asep diupdate ke ID PPE 20251031.
    - **Note Tambahan:** Angka '542' atau angka dinamis lainnya akan tetap mengikuti data asli kecuali baris yang disebutkan di atas.
    """)
