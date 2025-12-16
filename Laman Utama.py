# Laman Utama.py (FINAL DENGAN SEMUA PERBAIKAN)

import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd

def app_content():
    # ... (Konten app_content tetap sama) ...
    logo_url = "https://www.pei.co.id/images/logo-grey-3x.png"  
    st.logo(logo_url, icon_image=None)  
    
    st.title("RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD")
    st.markdown("""
    Selamat datang! Aplikasi ini telah dibagi menjadi empat halaman (aplikasi) terpisah yang dapat Anda akses melalui **menu navigasi di sebelah kiri** (ikon **>**).
    """)

def main():
    st.set_page_config(page_title="Dashboard Login", layout="centered")

    try:
        config = st.secrets 
    except AttributeError:
        st.error("❌ ERROR: Streamlit secrets tidak ditemukan. Pastikan konfigurasi sudah benar.")
        return

    try:
        # Perbaikan Bug: Membuat salinan data credentials
        credentials_copy = config['credentials'].to_dict()
    except Exception as e:
        st.error(f"❌ ERROR: Struktur Secrets salah atau kunci 'credentials' tidak ada. Detail: {e}")
        return

    authenticator = stauth.Authenticate(
        credentials_copy,  
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )

    # 4. Tampilkan Widget Login
    # PERBAIKAN FINAL: Membuat semua argumen menjadi keyword untuk menghindari TypeError
    name, authentication_status, username = authenticator.login(
        form_name='Login Dashboard',  # Argumen posisi pertama diubah menjadi keyword
        location='main',              # Argumen location
        key='unique_login_key'        # Argumen key
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
