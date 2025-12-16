# Laman Utama.py (FINAL FIX UNTUK VERSI 0.1.0)
import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd 

def app_content():
    st.logo("https://www.pei.co.id/images/logo-grey-3x.png", icon_image=None)  
    st.title("SUCCESS: DASHBOARD BERHASIL DIMUAT")
    st.markdown("Login berhasil. Konten Anda akan muncul di sini.")

def main():
    st.set_page_config(page_title="Dashboard Login", layout="centered")

    # 1. DATA DUMMY (DIGUNAKAN KARENA MASALAH SECRETS BERULANG)
    dummy_credentials = {
        'usernames': {
            'admin': {
                'email': 'admin@pei.co.id',
                'name': 'Administrator RMCC',
                # Pastikan password yang di-hash di sini adalah yang benar
                'password': '$2b$12$L7vyRk.s9LqUf753nO0E6OnT9r3eUf6NqN9.G7s2bS2k8x3vQ/T4m' 
            }
        }
    }
    dummy_cookie = {
        'name': 'some_cookie',
        'key': 'some_key',
        'expiry_days': 30
    }

    # 2. Inisialisasi Authenticator
    try:
        # PERBAIKAN AKHIR: Menggunakan Authenticator (A besar) untuk versi 0.1.0
        authenticator = stauth.Authenticator( 
            credentials=dummy_credentials,      
            cookie_name=dummy_cookie['name'],   
            key=dummy_cookie['key'],            
            expiry_days=dummy_cookie['expiry_days'] 
        )
    except Exception as e:
        st.error(f"❌ ERROR SAAT INISIALISASI AUTHENTICATOR: {e}")
        st.warning("Pastikan Anda menggunakan `streamlit-authenticator==0.1.0` di requirements.txt")
        return

    # 3. Tampilkan Widget Login
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
