# Laman Utama.py (FULL CODE FINAL: Mengatasi Konflik Caching)
import streamlit as st
import streamlit_authenticator as stauth
import yaml 
from yaml.loader import SafeLoader
import pandas as pd 
import os 

# ----------------------------------------------------
# FUNGSI KONTEN UTAMA APLIKASI
# ----------------------------------------------------
def app_content():
    st.logo("https://www.pei.co.id/images/logo-grey-3x.png", icon_image=None)  
    st.title("RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD")
    st.markdown("Autentikasi Berhasil. Konten dashboard Anda di sini.")

# ----------------------------------------------------
# FUNGSI MAIN() UNTUK LOGIN & AUTENTIKASI
# ----------------------------------------------------
def main():
    st.set_page_config(page_title="Dashboard Login", layout="centered")

    # 1. MEMUAT KONFIGURASI DARI config.yaml
    config_path = 'config.yaml'
    
    # Cek apakah file ada
    if not os.path.exists(config_path):
        st.error(f"❌ FATAL ERROR: File konfigurasi tidak ditemukan di {config_path}")
        st.warning("Pastikan Anda sudah membuat dan meng-commit file 'config.yaml' di root folder GitHub.")
        return
        
    try:
        # Memuat konfigurasi YAML
        with open(config_path) as file:
            config = yaml.load(file, Loader=SafeLoader)
        st.sidebar.success("✅ Config.yaml berhasil dimuat.") # Indikator bahwa loading YAML sukses
    except Exception as e:
        st.error(f"❌ ERROR: Gagal memuat dan mengurai config.yaml. Cek INDENTATION dan SPASI! Detail: {e}")
        return

    # 2. Inisialisasi Authenticator
    try:
        # PENTING: Menggunakan 'Authenticate' (A besar, e kecil) untuk mengakomodasi versi terbaru (0.2.x) 
        # yang dipaksa dijalankan oleh server Streamlit Anda.
        authenticator = stauth.Authenticate( 
            credentials=config['credentials'],
            cookie_name=config['cookie']['name'],   
            key=config['cookie']['key'],            
            expiry_days=config['cookie']['expiry_days'] 
        )
    except Exception as e:
        st.error(f"❌ ERROR SAAT INISIALISASI AUTHENTICATOR: {e}")
        st.warning("Periksa apakah stauth.Authenticate sudah benar, atau coba ganti ke stauth.Authenticator jika error terus berlanjut.")
        return

    # 3. Tampilkan Widget Login
    # SINTAKS INI SUDAH PASTI BENAR (menggunakan keyword arguments).
    name, authentication_status, username = authenticator.login(
        'Login Dashboard',         
        location='main',           
        key='unique_login_key'     
    )

    if authentication_status:
        # Jika berhasil login
        st.sidebar.success(f'Anda login sebagai: {name}')
        authenticator.logout('Logout', 'sidebar') 
        app_content() 
        
    elif authentication_status is False:
        st.error('Username atau password salah')

    elif authentication_status is None:
        st.warning('Silakan login untuk mengakses Dashboard')


if __name__ == '__main__':
    main()
