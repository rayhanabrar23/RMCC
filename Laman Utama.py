# Laman Utama.py (FULL CODE FINAL - DENGAN FIX KONVERSI KREDENSIAL)

import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd 

def app_content():
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

    # 2. PERBAIKAN: MEMFORMAT STRUKTUR KREDENSIAL SECARA EKSPLISIT
    try:
        data_credentials = config['credentials']
        
        # MEMBANGUN STRUKTUR DICTIONARY YANG DIHARAPKAN STAUTH SECARA MANUAL
        credentials_formatted = {
            'usernames': {
                user_key: {
                    'email': data_credentials['usernames'][user_key]['email'],
                    'name': data_credentials['usernames'][user_key]['name'],
                    'password': data_credentials['usernames'][user_key]['password']
                }
                for user_key in data_credentials['usernames']
            }
        }
        
    except Exception as e:
        st.error(f"❌ ERROR: Gagal memformat struktur Secrets. Kemungkinan salah kunci di .toml. Detail: {e}")
        return

    # 3. Inisialisasi Authenticator
    authenticator = stauth.Authenticate(
        credentials_formatted,  # GUNAKAN DATA YANG SUDAH DIFORMAT
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )

    # 4. Tampilkan Widget Login (FORMAT INI ADALAH YANG PALING STABIL)
    name, authentication_status, username = authenticator.login(
        'Login Dashboard',         # Argumen POSISI (Nama Form)
        location='main',           # Argumen KEYWORD
        key='unique_login_key'     # Argumen KEYWORD
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
