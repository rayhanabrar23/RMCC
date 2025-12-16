# Laman Utama.py (FINAL FIX MENGGUNAKAN ST.SECRETS DENGAN STRUKTUR LOOP DEFENSIVE)
import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd 

def app_content():
    st.logo("https://www.pei.co.id/images/logo-grey-3x.png", icon_image=None)  
    st.title("RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD")
    st.markdown("Login berhasil.")

def main():
    st.set_page_config(page_title="Dashboard Login", layout="centered")

    try:
        config = st.secrets 
    except AttributeError:
        st.error("❌ ERROR: Streamlit secrets tidak ditemukan.")
        return

    # 1. PERBAIKAN STRUKTUR: Mengambil dan Memformat Kredensial Secara Defensif
    try:
        data_credentials = config['credentials']
        
        # MEMBANGUN STRUKTUR DICTIONARY YANG DIHARAPKAN OLEH STAUTH SECARA MANUAL
        credentials_formatted = {
            'usernames': {
                # MENGGUNAKAN KEY YANG ANDA DEFENISIKAN DI TOML (admin_rmcc, staff_cl)
                user_key: { 
                    'email': data_credentials['usernames'][user_key]['email'],
                    'name': data_credentials['usernames'][user_key]['name'],
                    'password': data_credentials['usernames'][user_key]['password']
                }
                for user_key in data_credentials['usernames']
            }
        }
        
    except Exception as e:
        st.error(f"❌ ERROR: Gagal memformat struktur Secrets. Detail: {e}")
        return

    # 2. Inisialisasi Authenticator
    try:
        # Gunakan Authenticate untuk versi terbaru
        authenticator = stauth.Authenticate( 
            credentials=credentials_formatted, # Gunakan data yang sudah diformat secara manual
            cookie_name=config['cookie']['name'],   
            key=config['cookie']['key'],            
            expiry_days=config['cookie']['expiry_days'] 
        )
    except Exception as e:
        st.error(f"❌ ERROR SAAT INISIALISASI AUTHENTICATOR: {e}")
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
