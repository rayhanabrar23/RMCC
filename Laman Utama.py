# Laman Utama.py (File Utama/Index - FINAL DENGAN LOGIN)

import streamlit as st
import streamlit_authenticator as stauth
# Tidak perlu import yaml karena kita menggunakan st.secrets

# ----------------------------------------------------
# FUNGSI KONTEN UTAMA APLIKASI (Hanya Tampil Setelah Login)
# ----------------------------------------------------
def app_content():
    # Mengatur layout dan judul halaman
    st.set_page_config(page_title="LL & CL Dashboard", layout="wide")
    
    logo_url = "https://www.pei.co.id/images/logo-grey-3x.png"  
    st.logo(logo_url, icon_image=None)  
    
    # Konten halaman utama Anda yang diproteksi
    st.title("RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD")
    st.markdown("""
    Selamat datang! Aplikasi ini telah dibagi menjadi empat halaman (aplikasi) terpisah yang dapat Anda akses melalui **menu navigasi di sebelah kiri** (ikon **>**).

    Pilih halaman:
    
    - **Lendable Limit (LL):** Untuk menghitung posisi Lendable Limit.
    - **Concentration Limit (CL):** Untuk menghitung Batas Konsentrasi dan Haircut.
    - **UMA Scraper:** Untuk mengambil data Unusual Market Activity dari IDX.
    - **Repo Daily Position:** Untuk menghitung data Laporan Harian yang dikirim oleh PHEI.

    _Setiap halaman LL & CL memerlukan set file input yang berbeda._
    """)

# ----------------------------------------------------
# FUNGSI MAIN() UNTUK LOGIN
# ----------------------------------------------------
def main():
    # Mengatur layout halaman sebelum login
    st.set_page_config(page_title="Dashboard Login", layout="centered")

    # 1. Muat Secrets dari Streamlit Cloud
    # st.secrets berisi semua data konfigurasi yang sudah Anda masukkan di Cloud
    try:
        config = st.secrets 
    except AttributeError:
        st.error("❌ ERROR: Streamlit secrets tidak ditemukan. Pastikan Anda sudah memasukkan konfigurasi credentials dan cookie di Streamlit Cloud Secrets.")
        return

    # 2. Inisialisasi Authenticator
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )

    # 3. Tampilkan Widget Login
    # Login widget akan muncul di tengah halaman ('main')
    name, authentication_status, username = authenticator.login('Login Dashboard', 'main')

    if authentication_status:
        # Jika berhasil login
        st.sidebar.success(f'Anda login sebagai: {name}')
        authenticator.logout('Logout', 'sidebar') 
        
        # Panggil konten utama aplikasi
        app_content() 
        
    elif authentication_status is False:
        # Jika gagal
        st.error('Username atau password salah')

    elif authentication_status is None:
        # Tampilan awal
        st.warning('Silakan login untuk mengakses Dashboard')


if __name__ == '__main__':
    main()
