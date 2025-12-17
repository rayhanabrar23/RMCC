import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# 1. Konfigurasi Halaman
st.set_page_config(page_title="RMCC Dashboard", layout="centered")

# --- TRIK CSS: Sembunyikan Sidebar jika belum login ---
if "login_status" not in st.session_state or not st.session_state["login_status"]:
    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {display: none !important;}
            [data-testid="stSidebar"] {display: none !important;}
        </style>
    """, unsafe_allow_html=True)

# 2. Load data dari config.yaml
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

# 3. Inisialisasi Authenticator (Urutan diperbaiki)
authenticator = stauth.Authenticate(
    config['credentials'],
    "RMCC_v5",                # Nama cookie baru untuk reset sesi lama
    "signature_key_abc123",   # Key rahasia
    0,                        # 0 artinya refresh = wajib login ulang
    config['preauthorized']
)

# 4. Tampilkan Form Login
name, authentication_status, username = authenticator.login('main')

# --- 5. LOGIKA DISPLAY BERDASARKAN STATUS AUTENTIKASI ---

if authentication_status:
    # Simpan status di Session State
    st.session_state["login_status"] = True
    
    # PAKSA SIDEBAR MUNCUL
    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {display: block !important;}
            [data-testid="stSidebar"] {display: flex !important;}
        </style>
    """, unsafe_allow_html=True)
    
    # Tampilkan Logout di Sidebar
    authenticator.logout('Logout', 'sidebar')
    
    st.sidebar.title(f"User: {name}")
    st.title(f'Selamat datang, {name}')
    st.success("Login Berhasil! Menu dashboard tersedia di samping.")

elif authentication_status is False:
    st.session_state["login_status"] = False
    st.error('Username atau password salah')

elif authentication_status is None:
    st.session_state["login_status"] = False
    st.warning('Silakan masukkan username dan password')
