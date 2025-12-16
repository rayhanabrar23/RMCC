# Laman Utama.py (KEMBALI KE VERSI TERBARU DENGAN FIX SECRETS)

import streamlit as st
import streamlit_authenticator as stauth # Gunakan alias stauth lagi
import pandas as pd 
# ... (app_content tetap sama) ...

def main():
    st.set_page_config(page_title="Dashboard Login", layout="centered")

    # 1. Muat Secrets dari Streamlit Cloud
    try:
        config = st.secrets 
    except AttributeError:
        st.error("❌ ERROR: Streamlit secrets tidak ditemukan.")
        return

    # 2. PERBAIKAN: Menggunakan to_dict() lagi (versi 0.2.x lebih baik dalam hal ini)
    try:
        credentials_copy = config['credentials'].to_dict()
    except Exception as e:
        st.error(f"❌ ERROR: Struktur Secrets salah. Detail: {e}")
        return

    # 3. Inisialisasi Authenticator
    try:
        # KEMBALI MENGGUNAKAN Authenticate (A besar, e kecil) untuk versi terbaru
        authenticator = stauth.Authenticate( 
            credentials=credentials_copy,       # Menggunakan data yang sudah di to_dict()
            cookie_name=config['cookie']['name'],   
            key=config['cookie']['key'],            
            expiry_days=config['cookie']['expiry_days'] 
        )
    except Exception as e:
        st.error(f"❌ ERROR SAAT INISIALISASI AUTHENTICATOR: {e}")
        return

    # 4. Tampilkan Widget Login
    # Format argumen yang stabil (keyword arguments)
    name, authentication_status, username = authenticator.login(
        'Login Dashboard',         
        location='main',           
        key='unique_login_key'     
    )
    
    # ... (lanjutan kode IF/ELIF/ELSE tetap sama) ...
    
if __name__ == '__main__':
    main()
