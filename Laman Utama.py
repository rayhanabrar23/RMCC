import streamlit as st
import streamlit_authenticator as stauth
import base64

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

bin_str_main = get_base64('background.png')
bin_str_sidebar = get_base64('sidebar.png')

# Logika CSS Background
if bin_str_main:
    bg_img_style = f"background-image: url('data:image/png;base64,{bin_str_main}');"
else:
    bg_img_style = "background-color: #000000;"

if bin_str_sidebar:
    sidebar_img_style = f"background-image: url('data:image/png;base64,{bin_str_sidebar}'); background-size: cover;"
else:
    sidebar_img_style = "background-color: #111111;"

# --- 2. STYLING (CSS CUSTOM) ---
st.markdown(
    f"""
    <style>
    .stApp {{ {bg_img_style} background-size: cover; background-attachment: fixed; }}
    [data-testid="stSidebar"] {{ {sidebar_img_style} }}
    
    /* Membuat Kotak Login */
    [data-testid="stForm"] {{
        background-color: rgba(0, 0, 0, 0.8) !important;
        padding: 40px !important;
        border-radius: 15px !important;
        border: 1px solid #444 !important;
        box-shadow: 0px 4px 20px rgba(0,0,0,0.5) !important;
    }}
    
    button[kind="primaryFormSubmit"] {{
        background-color: #FFFFFF !important;
        color: black !important;
        font-weight: bold;
        width: 100% !important;
    }}
    
    h1 {{ 
        color: #FFFFFF !important; 
        text-align: center; 
        font-weight: 800 !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.7); 
    }}
    
    /* Warna teks sidebar agar putih */
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {{ color: white !important; }}
    </style>
    """,
    unsafe_allow_html=True
)

# --- 3. LOGIKA SIDEBAR AWAL (Sembunyikan jika belum login) ---
if st.session_state.get("authentication_status") is not True:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="stSidebarNav"] { display: none !important; }
        </style>
        """, 
        unsafe_allow_html=True
    )

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

# --- 6. TAMPILAN DASHBOARD / LOGIN ---
st.title("RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD")

# Jalankan login (Otomatis cek cookie)
name, authentication_status, username = authenticator.login('main')

if st.session_state.get("authentication_status"):
    st.session_state["login_status"] = True
    
    # PAKSA SIDEBAR MUNCUL (Override CSS Sembunyi)
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] { display: block !important; }
        [data-testid="stSidebarNav"] { display: block !important; }
        </style>
        """, 
        unsafe_allow_html=True
    )
    
    with st.sidebar:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.write(f"Selamat Datang, **{st.session_state['name']}**")
        
        # Tombol Logout Bawaan
        authenticator.logout('Logout', 'sidebar')

    st.success(f"Login Berhasil. Halo {st.session_state['name']}!")
    st.info("Pilih menu di samping untuk melihat data analisis.")

elif st.session_state.get("authentication_status") is False:
    st.error('Username/Password salah')

elif st.session_state.get("authentication_status") is None:
    st.warning('Silakan masukkan kredensial untuk mengakses dashboard.')
