import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# 1. Konfigurasi Halaman (Wajib Paling Atas)
st.set_page_config(page_title="RMCC Dashboard", layout="centered")

# --- 2. LOGIKA SIDEBAR (CSS) ---
# Jika belum login, sembunyikan semua elemen sidebar
if "login_status" not in st.session_state or st.session_state["login_status"] is not True:
    st.markdown("""
        <style>
            section[data-testid="stSidebar"] {display: none !important;}
            [data-testid="stSidebarNav"] {display: none !important;}
        </style>
    """, unsafe_allow_html=True)

# --- 3. LOAD KONFIGURASI ---
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

# --- 4. INISIALISASI AUTHENTICATOR ---
# Gunakan nama cookie baru setiap kali ada error (RMCC_v99)
authenticator = stauth.Authenticate(
    config['credentials'],
    "RMCC_v100",               # Ganti versi kuki untuk reset total
    "signature_key_secret", 
    0,                         # 0 = Refresh wajib login ulang
    config['preauthorized']
)

# --- 5. FORM LOGIN ---
# Ambil status login dari library
name, authentication_status, username = authenticator.login('main')

# --- 6. LOGIKA SETELAH LOGIN ---
if st.session_state.get("authentication_status"):
    # Set status login kita sendiri
    st.session_state["login_status"] = True
    
    # Munculkan kembali sidebar
    st.markdown("""
        <style>
            section[data-testid="stSidebar"] {display: flex !important;}
            [data-testid="stSidebarNav"] {display: block !important;}
        </style>
    """, unsafe_allow_html=True)
    
    # --- TOMBOL LOGOUT MANUAL (Anti-Error) ---
    with st.sidebar:
        st.write(f"User: **{st.session_state['name']}**")
        if st.button("Logout", key="logout_manual_final"):
            # RESET TOTAL SESSION STATE TANPA MANGGIL LIBRARY
            st.session_state["authentication_status"] = None
            st.session_state["login_status"] = False
            st.session_state["name"] = None
            st.session_state["username"] = None
            
            # Hapus semua yang tersisa
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            st.rerun()
        st.markdown("---")

    # --- KONTEN UTAMA ---
    st.title("RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD")
    st.success(f"Selamat datang, {st.session_state['name']}!")
    st.info("Pilih menu di samping untuk melihat data.")

elif st.session_state.get("authentication_status") is False:
    st.error('Username atau password salah')
    st.session_state["login_status"] = False

elif st.session_state.get("authentication_status") is None:
    st.warning('Silakan masukkan username dan password.')
    st.session_state["login_status"] = False
