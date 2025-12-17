import streamlit as st
import streamlit_authenticator as stauth
import yaml
import base64
from yaml.loader import SafeLoader

# --- 1. KONFIGURASI HALAMAN ---
# Harus diletakkan di paling atas
st.set_page_config(page_title="RMCC Dashboard", layout="centered")

# --- 2. FUNGSI BACKGROUND & STYLING (CSS) ---
def get_base64(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

try:
    # Mengambil file background.jpg dari repository GitHub kamu
    bin_str = get_base64('background.jpg')
    st.markdown(
        f"""
        <style>
        /* Mengatur Background Seluruh Layar */
        .stApp {{
            background-image: url("data:image/png;base64,{bin_str}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }}

        /* Membuat Kotak Login (Form) Jadi Putih Bersih */
        [data-testid="stForm"] {{
            background-color: white !important;
            padding: 30px !important;
            border-radius: 15px !important;
            box-shadow: 0px 4px 15px rgba(0,0,0,0.3);
            max-width: 500px;
            margin: auto;
        }}

        /* Mengubah Warna Label Input (Username/Password) Jadi Hitam */
        [data-testid="stForm"] label {{
            color: #31333F !important;
            font-weight: bold;
        }}

        /* Mengatur Judul Dashboard agar Berbayang dan Terbaca */
        h1 {{
            color: white !important;
            text-shadow: 2px 2px 8px #000000;
            text-align: center;
        }}

        /* Mengatur Pesan Error/Warning agar Tidak Transparan */
        .stAlert {{
            background-color: rgba(255, 255, 255, 0.95) !important;
            color: black !important;
            border-radius: 10px;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
except Exception as e:
    st.error(f"Gagal memuat background: {e}")

# --- 3. LOGIKA SIDEBAR (HANYA MUNCUL SETELAH LOGIN) ---
if "login_status" not in st.session_state or st.session_state["login_status"] is not True:
    st.markdown("""
        <style>
            section[data-testid="stSidebar"] {display: none !important;}
            [data-testid="stSidebarNav"] {display: none !important;}
        </style>
    """, unsafe_allow_html=True)

# --- 4. LOAD KONFIGURASI LOGIN ---
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
# 'main' artinya form muncul di halaman utama, bukan sidebar
name, authentication_status, username = authenticator.login('main')

# --- 7. LOGIKA SETELAH LOGIN ---
if st.session_state.get("authentication_status"):
    st.session_state["login_status"] = True
    
    # Munculkan kembali sidebar setelah sukses login
    st.markdown("""
        <style>
            section[data-testid="stSidebar"] {display: flex !important;}
            [data-testid="stSidebarNav"] {display: block !important;}
        </style>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.write(f"User Aktif: **{st.session_state['name']}**")
        if st.button("Logout", key="logout_btn"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        st.markdown("---")

    # KONTEN UTAMA DASHBOARD
    st.title("RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD")
    st.success(f"Selamat datang, {st.session_state['name']}!")
    st.info("Gunakan menu navigasi di sebelah kiri untuk mengelola data.")

elif st.session_state.get("authentication_status") is False:
    st.error('Username atau password salah')
    st.session_state["login_status"] = False

elif st.session_state.get("authentication_status") is None:
    st.warning('Silakan masukkan username dan password Anda.')
    st.session_state["login_status"] = False
