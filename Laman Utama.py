import streamlit as st
import streamlit_authenticator as stauth
import yaml
import base64
from yaml.loader import SafeLoader

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="RMCC Dashboard", layout="centered")

# --- 2. FUNGSI BACKGROUND (TAMBAHAN BARU) ---
def get_base64(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

try:
    bin_str = get_base64('background.jpg')
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{bin_str}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}
        /* Membuat kotak login jadi putih transparan agar teks terbaca */
        [data-testid="stForm"], .stAlert {{
            background-color: rgba(255, 255, 255, 0.85) !important;
            padding: 20px;
            border-radius: 10px;
        }}
        h1 {{
            color: white !important;
            text-shadow: 2px 2px 4px #000000;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
except Exception:
    # Jika gambar tidak ketemu, aplikasi tetap jalan tanpa background
    pass

# --- 3. LOGIKA SIDEBAR ---
if "login_status" not in st.session_state or st.session_state["login_status"] is not True:
    st.markdown("""
        <style>
            section[data-testid="stSidebar"] {display: none !important;}
            [data-testid="stSidebarNav"] {display: none !important;}
        </style>
    """, unsafe_allow_html=True)

# --- 4. LOAD KONFIGURASI ---
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

# --- 5. INISIALISASI AUTHENTICATOR ---
authenticator = stauth.Authenticate(
    config['credentials'],
    "RMCC_v101", 
    "signature_key_secret", 
    0, 
    config['preauthorized']
)

# --- 6. FORM LOGIN ---
name, authentication_status, username = authenticator.login('main')

# --- 7. LOGIKA SETELAH LOGIN ---
if st.session_state.get("authentication_status"):
    st.session_state["login_status"] = True
    
    st.markdown("""
        <style>
            section[data-testid="stSidebar"] {display: flex !important;}
            [data-testid="stSidebarNav"] {display: block !important;}
        </style>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.write(f"User: **{st.session_state['name']}**")
        if st.button("Logout", key="logout_manual_final"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        st.markdown("---")

    st.title("RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD")
    st.success(f"Selamat datang, {st.session_state['name']}!")
    st.info("Pilih menu di samping untuk melihat data.")

elif st.session_state.get("authentication_status") is False:
    st.error('Username atau password salah')
    st.session_state["login_status"] = False

elif st.session_state.get("authentication_status") is None:
    st.warning('Silakan masukkan username dan password.')
    st.session_state["login_status"] = False
