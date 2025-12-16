# Laman Utama.py
import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd # Tetap diimpor karena mungkin digunakan di konten halaman lain

# ----------------------------------------------------
# FUNGSI KONTEN UTAMA APLIKASI (DIPROTEKSI)
# ----------------------------------------------------
def app_content():
    # Mengatur layout dan judul halaman
    # Ganti dengan logo Anda yang sebenarnya jika tersedia
    logo_url = "https://www.pei.co.id/images/logo-grey-3x.png"  
    st.logo(logo_url, icon_image=None)  
    
    st.title("RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD")
    st.markdown("""
    Selamat datang! Aplikasi ini telah dibagi menjadi empat halaman (aplikasi) terpisah yang dapat Anda akses melalui **menu navigasi di sebelah kiri** (ikon **>**).
    
    Konten dashboard yang sesungguhnya (misalnya, grafik dan tabel) akan muncul di sini.
    """)

# ----------------------------------------------------
# FUNGSI MAIN() UNTUK LOGIN & AUTENTIKASI
# ----------------------------------------------------
def main():
    st.set_page_config(page_title="Dashboard Login", layout="centered")

    # 1. Muat Secrets dari Streamlit Cloud
    try:
        config = st.secrets 
    except AttributeError:
        st.error("❌ ERROR: Streamlit secrets tidak ditemukan. Pastikan konfigurasi sudah benar.")
        return

    # 2. Perbaikan BUG: Membuat salinan data credentials dari st.secrets
    try:
        # Gunakan .to_dict() untuk mengatasi masalah TyeError saat inisialisasi authenticator
        credentials_copy = config['credentials'].to_dict()
    except Exception as e:
        st.error(f"❌ ERROR: Struktur Secrets salah atau kunci 'credentials' tidak ada. Detail: {e}")
        return

    # 3. Inisialisasi Authenticator
    authenticator = stauth.Authenticate(
        credentials_copy,  
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )

    # 4. Tampilkan Widget Login
    # PERBAIKAN FINAL TYPEERROR: Menggunakan Posisi untuk Form Name, Keyword untuk location dan key
    name, authentication_status, username = authenticator.login(
        'Login Dashboard',         # Argumen POSISI (Nama Form)
        location='main',           # Argumen KEYWORD (Lokasi widget)
        key='unique_login_key'     # Argumen KEYWORD (Kunci unik untuk Streamlit)
    )

    if authentication_status:
        # Jika berhasil login
        st.sidebar.success(f'Anda login sebagai: {name}')
        authenticator.logout('Logout', 'sidebar') 
        
        # Panggil konten utama aplikasi yang terproteksi
        app_content() 
        
    elif authentication_status is False:
        st.error('Username atau password salah')

    elif authentication_status is None:
        st.warning('Silakan login untuk mengakses Dashboard')


if __name__ == '__main__':
    main()
