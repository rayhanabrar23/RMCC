import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# 1. Konfigurasi Halaman
st.set_page_config(page_title="RMCC Dashboard", layout="centered")

# 2. Load data dari config.yaml
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

# 3. Inisialisasi Authenticator
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)

# 4. Tampilkan Form Login
name, authentication_status, username = authenticator.login('main')

# 5. Logika setelah Login
if authentication_status:
    # Jika login berhasil, tampilkan tombol logout di sidebar
    authenticator.logout('Logout', 'sidebar')
    
    st.write(f'Selamat datang, *{name}*')
    st.title('RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD')
    
    # Masukkan konten utama dashboard Anda di sini
    st.success("Dashboard Aktif!")

elif authentication_status == False:
    st.error('Username/password salah')
elif authentication_status == None:
    st.warning('Silakan masukkan username dan password')
