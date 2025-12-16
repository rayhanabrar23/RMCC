# Laman Utama.py (FINAL FIX MENGGUNAKAN CONFIG.YAML)
import streamlit as st
import streamlit_authenticator as stauth
import yaml # Tambahkan import yaml
from yaml.loader import SafeLoader
import pandas as pd 
import os 

# ----------------------------------------------------
# FUNGSI KONTEN UTAMA APLIKASI
# ----------------------------------------------------
def app_content():
    st.logo("https://www.pei.co.id/images/logo-grey-3x.png", icon_image=None)  
    st.title("RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD")
    st.markdown("Login berhasil. Konten Anda akan muncul di sini.")

# ----------------------------------------------------
# FUNGSI MAIN() UNTUK LOGIN & AUTENTIKASI
# ----------------------------------------------------
def main():
    st.set_page_config(page_title="Dashboard Login", layout="centered")

    # 1. MEMUAT KONFIGURASI DARI config.yaml
    config_path = 'config.yaml'

    # Cek apakah file ada sebelum mencoba membacanya
    if not os.path.exists(config_path):
        st.error(f"❌ FATAL ERROR: File konfigurasi tidak ditemukan di {config_path}")
        st.warning("Pastikan Anda sudah membuat dan meng-commit file 'config.yaml' di root folder GitHub.")
        return
        
    try:
        # Memuat konfigurasi YAML
        with open(config_path) as file:
            config = yaml.load(file, Loader=SafeLoader)
    except Exception as e:
        st.error(f"❌ ERROR: Gagal memuat dan mengurai config.yaml. Cek INDENTATION dan SPASI! Detail: {e}")
        return

    # 2. Inisialisasi Authenticator
    try:
        # Menggunakan Authenticate (A besar, e kecil) karena kita menggunakan versi terbaru
        authenticator = stauth.Authenticate( 
            credentials=config['credentials'], # Memuat data credentials langsung dari YAML
            cookie_name=config['cookie']['name'],   
            key=config['cookie']['key'],            
            expiry_days=config['cookie']['expiry_days'] 
        )
    except Exception as e:
        st.error(f"❌ ERROR SAAT INISIALISASI AUTHENTICATOR: {e}")
        st.warning("Cek apakah library 'streamlit-authenticator' dan 'pyyaml' sudah ada di requirements.txt.")
        return

    # 3. Tampilkan Widget Login
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
