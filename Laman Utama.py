import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# 1. Konfigurasi Halaman Dasar
st.set_page_config(page_title="RMCC Dashboard", layout="centered")

# --- 2. LOGIKA SIDEBAR (CSS) ---
# Sembunyikan sidebar secara default jika belum login agar user fokus pada form login
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
# Nama cookie 'RMCC_vFinal' dan expiry 0 memastikan setiap refresh/tutup tab harus login lagi
authenticator = stauth.Authenticate(
    config['credentials'],
    "RMCC_vFinal",             # Nama cookie unik
    "random_signature_key",    # Kunci tanda tangan
    0,                         # 0 = Wajib login ulang saat refresh/tutup tab
    config['preauthorized']
)

# --- 5. FORM LOGIN ---
name, authentication_status, username = authenticator.login('main')

# --- 6. LOGIKA SETELAH LOGIN ---
if authentication_status:
    # Simpan status login ke session state
    st.session_state["login_status"] = True
    
    # Munculkan kembali sidebar dengan paksa setelah login berhasil
    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {display: block !important;}
            [data-testid="stSidebar"] {display: flex !important;}
        </style>
    """, unsafe_allow_html=True)
    
    # --- LOGOUT CUSTOM (Hanya satu tombol untuk menghindari DuplicateWidgetID) ---
    with st.sidebar:
        st.write(f"Selamat Datang, **{name}**")
        if st.button("Logout", key="logout_tombol_utama"):
            # Bersihkan semua session state secara manual
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            
            # Panggil fungsi logout internal tanpa render tombol tambahan
            authenticator.logout(location='unrendered')
            
            # Paksa aplikasi kembali ke kondisi awal
            st.rerun()
            
        st.markdown("---")

    # --- KONTEN UTAMA DASHBOARD ---
    st.title("RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD")
    st.success(f"Anda masuk sebagai {name}. Silakan gunakan menu navigasi di samping.")
    
    # Anda bisa menambahkan visualisasi atau data dashboard utama Anda di sini

elif authentication_status is False:
    st.session_state["login_status"] = False
    st.error('Username atau password salah')

elif authentication_status is None:
    st.session_state["login_status"] = False
    st.info('Silakan masukkan username dan password untuk mengakses sistem.')
