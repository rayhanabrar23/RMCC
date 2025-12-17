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
            [data-testid="stSidebarNav"] {display: none;}
            [data-testid="stSidebar"] {display: none;}
        </style>
    """, unsafe_allow_html=True)

# 2. Load data dari config.yaml
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

# 3. Inisialisasi Authenticator
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    0,
    config['preauthorized']
)

# 4. Tampilkan Form Login
name, authentication_status, username = authenticator.login('main')

# --- 5. LOGIKA DISPLAY BERDASARKAN STATUS AUTENTIKASI ---

if authentication_status:
    # 1. Simpan status di Session State
    st.session_state["login_status"] = True
    
    # 2. PAKSA SIDEBAR MUNCUL (Gunakan !important agar CSS dasar Streamlit kalah)
    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {display: block !important;}
            [data-testid="stSidebar"] {display: flex !important;}
        </style>
    """, unsafe_allow_html=True)
    
    # 3. Tampilkan Logout dan Konten
    authenticator.logout('Logout', 'sidebar')
    st.sidebar.title(f"User: {name}")
    
    st.title(f'Selamat datang, {name}')
    st.success("Login Berhasil! Silakan gunakan menu di samping.")
    
    # Di sini Anda bisa memanggil fungsi konten utama Anda
    # app_content()

elif authentication_status is False:
    # Jika gagal login, pastikan sidebar tetap hilang
    st.session_state["login_status"] = False
    st.error('Username atau password salah')
    st.markdown("""<style>[data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)

elif authentication_status is None:
    # Jika belum login, pastikan sidebar hilang total
    st.session_state["login_status"] = False
    st.warning('Silakan masukkan username dan password')
    st.markdown("""<style>[data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)



