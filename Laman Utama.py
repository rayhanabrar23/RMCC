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
    0
    config['preauthorized']
)

# 4. Tampilkan Form Login
name, authentication_status, username = authenticator.login('main')

# 5. Logika Login
if authentication_status:
    st.session_state["login_status"] = True # Simpan status login
    
    # Munculkan Sidebar kembali setelah login
    st.markdown("""<style>[data-testid="stSidebarNav"] {display: block;}</style>""", unsafe_allow_html=True)
    
    authenticator.logout('Logout', 'sidebar')
    st.title(f'Selamat datang, {name}')
    st.success("Silakan pilih menu di samping untuk melanjutkan.")

elif authentication_status == False:
    st.error('Username/password salah')
elif authentication_status == None:
    st.warning('Silakan masukkan username dan password')

