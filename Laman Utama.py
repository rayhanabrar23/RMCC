# Laman Utama.py (KODE UJI COBA UNTUK MENDIAGNOSIS MASALAH SECRETS)

import streamlit as st
import streamlit_authenticator as stauth

def app_content():
    # ... (Konten app_content tetap sama) ...
    st.logo("https://www.pei.co.id/images/logo-grey-3x.png", icon_image=None)  
    st.title("SUCCESS: DASHBOARD BERHASIL DIMUAT")
    st.markdown("Ini berarti *Authenticator* telah dibuat dan login berhasil.")

def main():
    st.set_page_config(page_title="Dashboard Login", layout="centered")

    # 1. DATA DUMMY (SAMA DENGAN FORMAT SECRETS)
    # HANYA UNTUK TUJUAN DIAGNOSIS
    dummy_credentials = {
        'usernames': {
            'rayhan': {
                'email': 'rayhan@pei.co.id',
                'name': 'Rayhan Abrar',
                # Password di sini harus HASHED, bukan plain text.
                # Contoh: 'abc' hashed menggunakan bcrypt adalah $2b$12$L7v...
                'password': '$2b$12$L7vyRk.s9LqUf753nO0E6OnT9r3eUf6NqN9.G7s2bS2k8x3vQ/T4m' 
            }
        }
    }
    dummy_cookie = {
        'name': 'some_cookie',
        'key': 'some_key',
        'expiry_days': 30
    }

    # 2. Inisialisasi Authenticator dengan data DUMMY
    authenticator = stauth.Authenticate(
        dummy_credentials,  
        dummy_cookie['name'],
        dummy_cookie['key'],
        dummy_cookie['expiry_days']
    )

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
