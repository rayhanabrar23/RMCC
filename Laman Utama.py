# Laman Utama.py (FINAL FIX MENGGUNAKAN CONFIG.YAML DAN STAUTH 0.1.0)
import streamlit as st
import streamlit_authenticator as stauth
import yaml 
from yaml.loader import SafeLoader
import os 

def app_content():
    st.logo("https://www.pei.co.id/images/logo-grey-3x.png", icon_image=None)  
    st.title("RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD")
    st.markdown("Login berhasil. Konten Anda akan muncul di sini.")

def main():
    st.set_page_config(page_title="Dashboard Login", layout="centered")

    config_path = 'config.yaml'
    
    if not os.path.exists(config_path):
        st.error(f"❌ FATAL ERROR: File konfigurasi tidak ditemukan di {config_path}")
        st.warning("Pastikan Anda sudah membuat dan meng-commit file 'config.yaml'.")
        return
        
    try:
        with open(config_path) as file:
            config = yaml.load(file, Loader=SafeLoader)
        st.sidebar.success("✅ Config.yaml berhasil dimuat.")
    except Exception as e:
        st.error(f"❌ ERROR: Gagal memuat/mengurai config.yaml. Detail: {e}")
        return

    # 2. Inisialisasi Authenticator
    try:
        # PENTING: Gunakan 'Authenticator' (A besar) untuk versi 0.1.0
        # dan gunakan KEYWORD ARGUMENTS yang sudah terbukti stabil.
        authenticator = stauth.Authenticator( 
            credentials=config['credentials'],
            cookie_name=config['cookie']['name'],   
            key=config['cookie']['key'],            
            expiry_days=config['cookie']['expiry_days'] 
        )
    except Exception as e:
        st.error(f"❌ ERROR SAAT INISIALISASI AUTHENTICATOR: {e}")
        st.warning("Ini adalah masalah library. Pastikan stauth=0.1.0 di requirements.txt")
        return

    # 3. Tampilkan Widget Login
    # SINTAKS INI SUDAH PASTI BENAR.
    name, authentication_status, username = authenticator.login(
        'Login Dashboard',         
        location='main',           
        key='unique_login_key'     
    )

    if authentication_status:
        st.sidebar.success(f'Anda login sebagai: {name}')
        authenticator.logout('Logout', 'sidebar') 
        app_content() 
        
    elif authentication_status is False:
        st.error('Username atau password salah')

    elif authentication_status is None:
        st.warning('Silakan login untuk mengakses Dashboard')


if __name__ == '__main__':
    main()
