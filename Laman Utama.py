import streamlit as st
import streamlit_authenticator as stauth
import yaml
import base64
from yaml.loader import SafeLoader

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="RMCC Dashboard", layout="centered")

# --- 2. FUNGSI BACKGROUND & STYLING (CSS CUSTOM) ---
def get_base64(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

try:
    bin_str = get_base64('background.jpg')
    st.markdown(
        f"""
        <style>
        /* Mengatur Background */
        .stApp {{
            background-image: url("data:image/png;base64,{bin_str}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}

        /* Merapikan Header agar tidak tertutup */
        header {{background: rgba(0,0,0,0) !important;}}
        
        /* Membuat Kotak Login Putih Solid & Bersih */
        [data-testid="stForm"] {{
            background-color: #FFFFFF !important;
            padding: 40px !important;
            border-radius: 20px !important;
            box-shadow: 0px 10px 25px rgba(0,0,0,0.2) !important;
            max-width: 450px;
            margin: auto;
            border: none !important;
        }}

        /* Warna Teks Label (Username/Password) jadi Hitam Pekat */
        [data-testid="stForm"] label p {{
            color: #1E1E1E !important;
            font-weight: 600 !important;
            font-size: 1.1rem !important;
        }}

        /* Tombol Login Warna Merah (Senada Logo PEI) */
        button[kind="primaryFormSubmit"] {{
            background-color: #C62127 !important;
            color: white !important;
            border-radius: 10px !important;
            width: 100% !important;
            border: none !important;
            height: 3em !important;
        }}

        /* Input Field (Kotak Ketik) */
        .stTextInput input {{
            background-color: #F0F2F6 !important;
            color: #1E1E1E !important;
            border-radius: 10px !important;
        }}

        /* Judul Dashboard di Atas Kotak */
        h1 {{
            color: white !important;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
            text-align: center;
            font-weight: 800 !important;
        }}

        /* Kotak Pesan Error/Warning */
        .stAlert {{
            background-color: white !important;
            color: black !important;
            border-radius: 15px !important;
            border-left: 5px solid #C62127 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
except Exception:
    st.warning("Gunakan file 'background.jpg' untuk tampilan maksimal.")

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
st.title("RMCC DASHBOARD")

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
    # Tambahkan konten dashboard kamu di sini

elif st.session_state.get("authentication_status") is False:
    st.error('Username/Password salah')

elif st.session_state.get("authentication_status") is None:
    st.info('Silakan masukkan kredensial untuk mengakses dashboard.')
