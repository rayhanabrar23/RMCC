import streamlit as st
import base64

# 1. Konfigurasi Halaman (Biar tampilan lebar)
st.set_page_config(page_title="Update Password", layout="centered")

# 2. Fungsi untuk memproses gambar background.jpg
def get_base64(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

try:
    bin_str = get_base64('background.jpg')
    
    # 3. CSS untuk Background dan Styling Form
    page_bg_img = f'''
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{bin_str}");
        background-size: cover;
        background-position: center;
    }}

    /* Membuat kotak form jadi agak transparan biar estetik */
    [data-testid="stForm"] {{
        background-color: rgba(255, 255, 255, 0.8);
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #ddd;
    }}
    
    /* Menyesuaikan warna judul agar terlihat di background */
    h1 {{
        color: white;
        text-shadow: 2px 2px 4px #000000;
        text-align: center;
    }}
    </style>
    '''
    st.markdown(page_bg_img, unsafe_allow_html=True)
except FileNotFoundError:
    st.error("File 'background.jpg' tidak ditemukan. Pastikan sudah di-upload ke GitHub!")

# 4. Konten Aplikasi
st.title("Ganti Password User")

with st.form("form_password"):
    st.subheader("Silakan masukkan detail baru")
    pass_lama = st.text_input("Password Lama", type="password")
    pass_baru = st.text_input("Password Baru", type="password")
    konfirmasi = st.text_input("Konfirmasi Password Baru", type="password")
    
    submit_button = st.form_submit_button("Simpan Perubahan")

    if submit_button:
        if pass_baru == konfirmasi and pass_baru != "":
            st.success("Password berhasil diperbarui!")
        else:
            st.error("Password baru dan konfirmasi tidak cocok!")
