import streamlit as st
import streamlit_authenticator as stauth
import base64

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD",
    layout="centered"
)

# --- 2. CUSTOM CSS (dark theme, konsisten dengan halaman lain) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Background app */
    .stApp {
        background-color: #0f1117;
        color: #e8eaf0;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1d2e 0%, #141624 100%);
        border-right: 1px solid #2a2d3e;
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span { color: #e8eaf0 !important; }

    /* Kotak login */
    [data-testid="stForm"] {
        background-color: #1a1d2e !important;
        padding: 40px !important;
        border-radius: 14px !important;
        border: 1px solid #2a2d3e !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4) !important;
    }

    /* Input field */
    .stTextInput > div > div {
        background: #0f1117 !important;
        border: 1px solid #2a2d3e !important;
        border-radius: 8px !important;
        color: #e8eaf0 !important;
    }
    .stTextInput label { color: #8a8fa8 !important; font-size: 0.82rem !important; }

    /* Tombol submit login */
    button[kind="primaryFormSubmit"] {
        background: linear-gradient(135deg, #3b5bdb, #5c7cfa) !important;
        color: white !important;
        font-weight: 600 !important;
        width: 100% !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 0 !important;
        transition: opacity 0.2s !important;
    }
    button[kind="primaryFormSubmit"]:hover { opacity: 0.88 !important; }

    /* Tombol lain (logout, dll) */
    .stButton > button {
        background: linear-gradient(135deg, #3b5bdb, #5c7cfa);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 8px 20px;
        transition: opacity 0.2s;
    }
    .stButton > button:hover { opacity: 0.88; }

    /* Judul halaman */
    h1 {
        color: #e8eaf0 !important;
        text-align: center;
        font-weight: 700 !important;
        font-size: 1.4rem !important;
        letter-spacing: 0.02em;
    }

    /* Alert/info/error/warning */
    [data-testid="stAlert"] {
        border-radius: 8px !important;
        border: 1px solid #2a2d3e !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. SEMBUNYIKAN SIDEBAR SEBELUM LOGIN ---
if st.session_state.get("authentication_status") is not True:
    st.markdown("""
    <style>
    [data-testid="stSidebar"]    { display: none !important; }
    [data-testid="stSidebarNav"] { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. LOAD KONFIGURASI DARI SECRETS (Recursive Copy) ---
def convert_secrets(secrets_obj):
    new_dict = {}
    for key, value in secrets_obj.items():
        if isinstance(value, (dict, st.runtime.secrets.Secrets, st.runtime.secrets.AttrDict)):
            new_dict[key] = convert_secrets(value)
        else:
            new_dict[key] = value
    return new_dict

if len(st.secrets) > 0:
    config = convert_secrets(st.secrets)
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

# --- 6. TAMPILAN LOGIN ---
st.markdown("<br>", unsafe_allow_html=True)
st.title("RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD")
st.markdown("<br>", unsafe_allow_html=True)

name, authentication_status, username = authenticator.login('main')

if st.session_state.get("authentication_status"):
    st.session_state["login_status"] = True

    # Tampilkan sidebar setelah login
    st.markdown("""
    <style>
    [data-testid="stSidebar"]    { display: block !important; }
    [data-testid="stSidebarNav"] { display: block !important; }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"Selamat datang, **{st.session_state['name']}**")
        st.markdown("---")
        authenticator.logout('Logout', 'sidebar')

    st.success(f"Login berhasil. Halo, {st.session_state['name']}!")
    st.info("Pilih menu di samping untuk melihat data analisis.")

elif st.session_state.get("authentication_status") is False:
    st.error("Username atau password salah.")

elif st.session_state.get("authentication_status") is None:
    st.warning("Silakan masukkan kredensial untuk mengakses dashboard.")
