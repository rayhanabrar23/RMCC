import streamlit as st
import zipfile
import io

st.set_page_config(page_title="SLIK Editor Pro", layout="wide")

# --- UI HEADER ---
st.title("🚀 SLIK Data Customizer")
st.markdown("Edit Header, Closing, dan konten data SLIK secara dinamis.")

# --- SIDEBAR: FITUR INTERAKSI ---
st.sidebar.header("⚙️ Pengaturan File")

# Input untuk periode (misal: 2025.11)
periode_input = st.sidebar.text_input("Periode Data (YYYY.MM)", value="2025.11")

st.sidebar.subheader("📝 Custom Header & Trailer")
# Fitur agar user bisa ganti Opening, Closing, TA langsung
custom_opening = st.sidebar.text_area("Baris Opening (Header)", placeholder="Contoh: H|016357|...")
custom_closing = st.sidebar.text_area("Baris Closing", placeholder="Contoh: C|...")
custom_footer = st.sidebar.text_area("Baris TA (Trailer)", placeholder="Contoh: T|016357|...")

# --- LOGIKA PEMROSESAN ---
def process_slik_content(filename, content, op, cl, ta):
    lines = content.splitlines()
    if not lines:
        return ""
    
    new_lines = []
    
    for idx, line in enumerate(lines):
        current_line = line
        
        # 1. GANTI OPENING (Biasanya baris pertama / Start with 'H')
        if idx == 0 and op:
            current_line = op
        
        # 2. GANTI CLOSING/TA (Biasanya baris terakhir / Start with 'T' atau 'C')
        elif idx == len(lines) - 1:
            if ta and (current_line.startswith('T') or "TA" in filename):
                current_line = ta
            elif cl and current_line.startswith('C'):
                current_line = cl

        # 3. GLOBAL REPLACE SID AJAIB
        current_line = current_line.replace("SCD2810HAI23003", "SCD100456212317")

        # 4. LOGIKA SPESIFIK FILE F06
        if ".F06." in filename:
            # Edit Interest BBM & MSU
            if any(id_nasabah in current_line for id_nasabah in ["CPD2303CJB66884", "CPD0104CJB43364"]):
                current_line = current_line.replace(",00", "7,00")
            
            # Ubah Baris Asep F06
            if "IDD1601G7811173" in current_line and "REPCT202503000001" in current_line:
                current_line = "D|REPCT202312000006|IDD1601G7811173|005|016357|20231227|20251219|12,00|IDR|3231979475||5|20240606|99|3231979475|512|00|||000|U"

        # 5. LOGIKA SPESIFIK FILE A01
        elif ".A01." in filename:
            # Ubah Baris Asep A01
            if "IDD1601G7811173" in current_line and "Asep Sulaeman Sabanda" in current_line:
                current_line = "D|REPCT202312000006IPPE20251031|REPCT202312000006|IDD1601G7811173|F06|1|F0419|||99|20231227|Asep Sulaeman Sabanda|PEI01C00300108|Gedung BEI, Tower I, Lt.3, Suite 301, Jl. Jend. Sudirman Kav. 52-53, Jakarta 12190, Indonesia|0394|2860461800|2860461800|20251031||||T||T|T||000|C"

        new_lines.append(current_line)
        
    return "\n".join(new_lines)

# --- UPLOAD & EXECUTE ---
uploaded_files = st.file_uploader("Upload 6 File SLIK TXT", type=['txt'], accept_multiple_files=True)

if uploaded_files:
    if st.button("🚀 Jalankan & Download ZIP"):
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for file in uploaded_files:
                original_content = file.getvalue().decode("utf-8")
                processed_content = process_slik_content(
                    file.name, 
                    original_content, 
                    custom_opening, 
                    custom_closing, 
                    custom_footer
                )
                zip_file.writestr(file.name, processed_content)
        
        st.success(f"Berhasil memproses {len(uploaded_files)} file!")
        st.download_button(
            label="⬇️ Download Hasil Modifikasi",
            data=zip_buffer.getvalue(),
            file_name=f"SLIK_MODIFIED_{periode_input}.zip",
            mime="application/zip"
        )
