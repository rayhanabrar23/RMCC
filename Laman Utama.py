import streamlit as st
import streamlit_authenticator as stauth
import base64
import copy  # Tambahkan library ini untuk duplikasi data secara mendalam

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD", layout="centered")

# --- FUNGSI HELPER BACKGROUND LOKAL ---
def get_base64(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return None

# Ambil data Base64 untuk Background Utama dan Sidebar
bin_str_main = get_base64('background.png')
bin_str_sidebar = get_base64('sidebar.png')

# Logika CSS untuk Background Utama
if bin_str_main:
    bg_img_style = f"background-image: url('data:image/png;base64,{bin_str_main}');"
else:
    bg_img_style = "background-color: #000000;"

# Logika CSS untuk Sidebar
if bin_str_sidebar:
    sidebar_img_style = f"""
        background-image: url("data:image/png;base64,{bin_str_sidebar}");
        background-size: cover;
        background-repeat: no-repeat;
    """
else:
    sidebar_img_style = "background-color: #111111;"

# --- 2. STYLING (CSS CUSTOM) ---
st.markdown(
    f"""
    <style>
    .stApp {{
        {bg_img_style}
        background-size: cover;
        background-attachment: fixed;
    }}
    [data-testid="stSidebar"] {{
        {sidebar_img_style}
    }}
    [data-testid="stForm"] {{
        background-color: rgba(0, 0, 0, 0.8) !important;
        padding: 40px !important;
        border-radius: 15px !important;
        box-shadow: 0px 4px 20px rgba(0,0,0,0.5) !important;
        border: 1px solid #444 !important;
    }}
    button[kind="primaryFormSubmit"] {{
        background-color: #FFFFFF !important;
        color: black !important;
        border-radius: 8px !important;
        width: 100% !important;
        border: none !important;
        font-weight: bold;
    }}
    h1 {{
        color: #FFFFFF !important;
        text-align: center;
        font-weight: 800 !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.7);
        margin-bottom: 2rem !important;
    }}
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {{
        color: white !important;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# --- 3. LOGIKA SIDEBAR ---
if "login_status" not in st.session_state or st.session_state["login_status"] is not True:
    st.markdown("<style>section[data-testid='stSidebar'] {display: none !important;}</style>", unsafe_allow_html=True)

# --- 4. LOAD KONFIGURASI DARI SECRETS (FIXED) ---
# Menggunakan deepcopy agar library stauth bebas mengubah data tanpa error 'read-only'
if len(st.secrets) > 0:
    # Kita ambil dictionary murni dari secrets
    raw_config = st.secrets.to_dict() if hasattr(st.secrets, "to_dict") else dict(st.secrets)
    config = copy.deepcopy(raw_config)
else:
    st.error("Konfigurasi Secrets tidak ditemukan!")
    st.stop()

# --- 5. AUTHENTICATOR ---
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'], 
    config['cookie']['key'], 
    config['cookie']['expiry_days'],
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
