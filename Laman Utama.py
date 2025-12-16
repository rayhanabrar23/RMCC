# Laman Utama.py (FINAL FIX MENGGUNAKAN VERSI STREAMLIT-AUTHENTICATOR TERBARU)
import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd 

def app_content():
    st.logo("https://www.pei.co.id/images/logo-grey-3x.png", icon_image=None)  
    st.title("RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD")
    st.markdown("""
    Selamat datang! Aplikasi ini telah berhasil melalui proses autentikasi.
    """)

def main():
    st.set_page_config(page_title="Dashboard Login", layout="centered")

    # 1. Muat Secrets dari Streamlit Cloud
    try:
        config = st.secrets 
    except AttributeError:
        st.error("❌ ERROR: Streamlit secrets tidak ditemukan.")
        return

    # 2. PERBAIKAN STRUKTUR: Menggunakan to_dict() untuk kompatibilitas versi terbaru
    try:
        credentials_copy = config['credentials'].to_dict()
    except Exception as e:
        st.error(f"❌ ERROR: Struktur Secrets salah atau kunci 'credentials' tidak ada. Detail: {e}")
        return

    # 3. Inisialisasi Authenticator
    try:
        # PENTING: Gunakan Authenticate (A besar, e kecil) untuk versi terbaru
        authenticator = stauth.Authenticate( 
            credentials=credentials_copy,       
            cookie_name=config['cookie']['name'],   
            key=config['cookie']['key'],            
            expiry_days=config['cookie']['expiry_days'] 
        )
    except Exception as e:
        st.error(f"❌ ERROR SAAT INISIALISASI AUTHENTICATOR: {e}")
        st.warning("Jika ini adalah AttributeError, coba ganti stauth.Authenticate menjadi stauth.Authenticator.")
        return

    # 4. Tampilkan Widget Login
    # PENTING: Menggunakan format Posisi + Keyword yang paling stabil
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
