import streamlit as st
import streamlit_authenticator as stauth
import yaml
import base64
from yaml.loader import SafeLoader

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD", layout="centered")

# --- 2. STYLING (CSS CUSTOM) ---
# Menghapus bagian background image, fokus ke tampilan form yang rapi
st.markdown(
    """
    <style>
    /* Mengatur warna latar belakang aplikasi menjadi abu-abu terang standar */
    .stApp {
        background-color: #000000;
    }

    /* Membuat Kotak Login Putih Solid & Rapi */
    [data-testid="stForm"] {
        background-color: #000000 !important;
        padding: 40px !important;
        border-radius: 15px !important;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.1) !important;
        border: none !important;
    }

    /* Tombol Login Warna Merah PEI */
    button[kind="primaryFormSubmit"] {
        background-color: #FFFFFF !important;
        color: white !important;
        border-radius: 8px !important;
        width: 100% !important;
        border: none !important;
    }

    /* Judul Dashboard */
    h1 {
        color: #FFFFFF !important;
        text-align: center;
        font-weight: 1500 !important;
        margin-bottom: 2rem !important;
    }
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







