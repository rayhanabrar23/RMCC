import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# 1. Konfigurasi Halaman
st.set_page_config(page_title="RMCC Dashboard", layout="centered")

# --- 2. LOGIKA SIDEBAR (CSS) ---
if "login_status" not in st.session_state or not st.session_state["login_status"]:
    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {display: none !important;}
            [data-testid="stSidebar"] {display: none !important;}
        </style>
    """, unsafe_allow_html=True)

# --- 3. LOAD KONFIGURASI ---
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

# --- 4. INISIALISASI AUTHENTICATOR ---
authenticator = stauth.Authenticate(
    config['credentials'],
    "RMCC_Cookie_V1",          # Nama cookie
    "signature_key_secure",    # Key bebas
    0,                         # 0 = Refresh wajib login ulang
    config['preauthorized']
)

# --- 5. FORM LOGIN ---
name, authentication_status, username = authenticator.login('main')

# --- 6. LOGIKA SETELAH LOGIN ---
if authentication_status:
    st.session_state["login_status"] = True
    
    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {display: block !important;}
            [data-testid="stSidebar"] {display: flex !important;}
        </style>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.write(f"User: **{name}**")
        # Perbaikan tombol logout agar tidak bentrok dengan library internal
        if st.button("Logout", key="btn_logout_final"):
            st.session_state["login_status"] = False
            authenticator.logout(location='unrendered')
            st.rerun()
        st.markdown("---")

    st.title("RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD")
    st.success(f"Selamat datang {name}!")

elif authentication_status is False:
    st.error('Username atau password salah')
    st.session_state["login_status"] = False

elif authentication_status is None:
    st.warning('Silakan masukkan username dan password.')
    st.session_state["login_status"] = False
