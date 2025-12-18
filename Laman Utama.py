import streamlit as st
import streamlit_authenticator as stauth
import yaml
import base64
from yaml.loader import SafeLoader

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD", layout="centered")

# --- FUNGSI HELPER BACKGROUND LOKAL ---
def get_base64(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Ganti 'background.jpg' dengan nama file gambar aslimu
try:
    bin_str = get_base64('background.jpg') 
    bg_img_style = f"background-image: url('data:image/png;base64,{bin_str}');"
except FileNotFoundError:
    # Jika gambar tidak ketemu, fallback ke warna hitam seperti awal
    bg_img_style = "background-color: #000000;"

# --- 2. STYLING (CSS CUSTOM) ---
st.markdown(
    f"""
    <style>
    /* Mengatur Latar Belakang Aplikasi */
    .stApp {{
        {bg_img_style}
        background-size: cover;
        background-attachment: fixed;
    }}

    /* Membuat Kotak Login Agak Transparan agar Background Terlihat Cantik */
    [data-testid="stForm"] {{
        background-color: rgba(0, 0, 0, 0.8) !important; /* Hitam dengan transparansi 80% */
        padding: 40px !important;
        border-radius: 15px !important;
        box-shadow: 0px 4px 20px rgba(0,0,0,0.5) !important;
        border: 1px solid #444 !important;
    }}

    /* Tombol Login */
    button[kind="primaryFormSubmit"] {{
        background-color: #FFFFFF !important;
        color: black !important; /* Diubah ke hitam agar kontras dengan tombol putih */
        border-radius: 8px !important;
        width: 100% !important;
        border: none !important;
        font-weight: bold;
    }}

    /* Judul Dashboard */
    h1 {{
        color: #FFFFFF !important;
        text-align: center;
        font-weight: 800 !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.7); /* Agar judul terbaca meski bg terang */
        margin-bottom: 2rem !important;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# --- 3. LOGIKA SIDEBAR ---
if "login_status" not in st.session_state or st.session_state["login_status"] is not True:
    st.markdown("<style>section[data-testid='stSidebar'] {display: none !important;}</style>", unsafe_allow_html=True)

# --- 4. LOAD KONFIGURASI ---
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

# --- 5. AUTHENTICATOR ---
authenticator = stauth.Authenticate(
    config['credentials'],
    "RMCC_v101", 
    "signature_key_secret", 
    0, 
    config['preauthorized']
)

# --- 6. TAMPILAN DASHBOARD / LOGIN ---
st.title("RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD")

name, authentication_status, username = authenticator.login('main')

if st.session_state.get("authentication_status"):
    st.session_state["login_status"] = True
    
    with st.sidebar:
        st.write(f"Selamat Datang, **{st.session_state['name']}**")
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    st.success(f"Login Berhasil. Halo {st.session_state['name']}!")
    st.info("Pilih menu di samping untuk melihat data.")

elif st.session_state.get("authentication_status") is False:
    st.error('Username/Password salah')

elif st.session_state.get("authentication_status") is None:
    st.warning('Silakan masukkan kredensial untuk mengakses dashboard.')



