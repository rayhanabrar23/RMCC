import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# 1. Konfigurasi Halaman Dasar
st.set_page_config(page_title="RMCC Dashboard", layout="centered")

# --- 2. LOGIKA SIDEBAR (CSS) ---
# Sembunyikan sidebar secara total jika belum login agar tidak bisa diintip
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
# Nama cookie 'RMCC_Final_Fix' dan expiry 0 untuk memastikan keamanan saat refresh
authenticator = stauth.Authenticate(
    config['credentials'],
    "RMCC_Final_Fix",          # Nama cookie unik baru
    "random_signature_key",    # Kunci tanda tangan
    0,                         # 0 = Sesi dihapus saat tab ditutup/refresh
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
    
    # --- LOGOUT CUSTOM (Anti-KeyError Fix) ---
    with st.sidebar:
        st.write(f"Selamat Datang, **{name}**")
        if st.button("Logout", key="logout_tombol_final"):
            # 1. Panggil logout internal library dulu (tanpa render tombol tambahan)
            authenticator.logout(location='unrendered')
            
            # 2. Hapus variabel login kustom kita
            if "login_status" in st.session_state:
                del st.session_state["login_status"]
            
            # 3. Paksa aplikasi balik ke kondisi awal
            st.rerun()
            
        st.markdown("---")

    # --- KONTEN UTAMA DASHBOARD ---
    st.title("RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD")
    st.success(f"Anda masuk sebagai {name}.")
    st.info("Gunakan navigasi di sisi kiri untuk berpindah halaman.")
    
    # (Opsional) Tambahkan ringkasan dashboard Anda di sini

elif authentication_status is False:
    st.session_state["login_status"] = False
    st.error('Username atau password salah')

elif authentication_status is None:
    st.session_state["login_status"] = False
    st.warning('Silakan masukkan username dan password untuk mengakses sistem.')
