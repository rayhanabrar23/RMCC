import streamlit as st
import streamlit_authenticator as stauth
import yaml
import base64
from yaml.loader import SafeLoader

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="RMCC Dashboard", layout="wide") # Pakai 'wide' agar lebih fleksibel

# --- 2. FUNGSI BACKGROUND & STYLING (CSS) ---
def get_base64(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

try:
    bin_str = get_base64('background.jpg')
    st.markdown(
        f"""
        <style>
        /* Mengatur Background agar memenuhi layar tanpa terpotong */
        .stApp {{
            background-image: url("data:image/png;base64,{bin_str}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}

        /* Sembunyikan Header default Streamlit agar bersih */
        header {{background: rgba(0,0,0,0) !important;}}
        [data-testid="stHeader"] {{background: rgba(0,0,0,0) !important;}}

        /* Mengatur posisi konten utama: Geser ke kiri agar tidak menutupi gambar kantor di kanan */
        .main .block-container {{
            max-width: 1200px;
            padding-top: 2rem;
            margin-left: 5% !important; /* Geser ke kiri */
        }}

        /* Desain Kotak Login yang Modern & Kompak */
        [data-testid="stForm"] {{
            background-color: rgba(255, 255, 255, 0.95) !important;
            padding: 30px !important;
            border-radius: 15px !important;
            box-shadow: 0px 8px 20px rgba(0,0,0,0.2) !important;
            width: 380px !important; /* Ukuran kotak diperkecil agar tidak 'makan tempat' */
            border: none !important;
        }}

        /* Warna Teks Judul Dashboard - diletakkan di atas kotak login */
        .custom-title {{
            color: #C62127 !important; /* Merah PEI */
            font-size: 2.2rem;
            font-weight: 800;
            text-shadow: 1px 1px 2px rgba(255,255,255,0.8);
            margin-bottom: 10px;
        }}

        /* Warna Label Form */
        [data-testid="stForm"] label p {{
            color: #1E1E1E !important;
            font-weight: bold !important;
        }}

        /* Tombol Login Merah PEI */
        button[kind="primaryFormSubmit"] {{
            background-color: #C62127 !important;
            color: white !important;
            border-radius: 8px !important;
            width: 100% !important;
            height: 45px !important;
            border: none !important;
            margin-top: 10px;
        }}
        
        /* Kotak Notifikasi di bawah form */
        .stAlert {{
            width: 380px !important;
            background-color: white !important;
            border-left: 5px solid #C62127 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
except Exception:
    pass

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

# --- 6. TAMPILAN HALAMAN LOGIN ---

# Mengatur tata letak menggunakan kolom agar form ada di sebelah kiri
col1, col2 = st.columns([1, 1.5]) 

with col1:
    # Judul diletakkan di sini agar rapi di atas kotak
    st.markdown('<p class="custom-title">RMCC DASHBOARD</p>', unsafe_allow_html=True)
    
    name, authentication_status, username = authenticator.login('main')

    if st.session_state.get("authentication_status"):
        st.session_state["login_status"] = True
        st.rerun()

    elif st.session_state.get("authentication_status") is False:
        st.error('User/Pass salah')

    elif st.session_state.get("authentication_status") is None:
        st.info('Silakan login')

# Kosongkan col2 agar gambar kantor di background (sisi kanan) terlihat jelas
with col2:
    st.write("")
