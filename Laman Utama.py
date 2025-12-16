# Laman Utama.py (File Utama/Index - FINAL DENGAN LOGIN & PERBAIKAN BUG)

import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
# Anda mungkin perlu menambahkan import pustaka lain di sini jika dibutuhkan 
# oleh app_content (misalnya, numpy, io, dll.)

# ----------------------------------------------------
# FUNGSI KONTEN UTAMA APLIKASI (Hanya Tampil Setelah Login)
# ----------------------------------------------------
def app_content():
    # Mengatur layout dan judul halaman
    # Catatan: st.set_page_config sebaiknya dipanggil hanya sekali sebelum widget apa pun,
    # namun dalam struktur multi-page, Streamlit menangani layout.
    
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
# FUNGSI MAIN() UNTUK LOGIN & AUTENTIKASI
# ----------------------------------------------------
def main():
    # Mengatur layout halaman sebelum login
    # Layout 'centered' cocok untuk tampilan login
    st.set_page_config(page_title="Dashboard Login", layout="centered")

    # 1. Muat Secrets dari Streamlit Cloud
    try:
        config = st.secrets 
    except AttributeError:
        st.error("❌ ERROR: Streamlit secrets tidak ditemukan. Pastikan Anda sudah memasukkan konfigurasi credentials dan cookie di Streamlit Cloud Secrets.")
        return

    # 2. PERBAIKAN BUG: Membuat salinan data credentials
    # Kita menggunakan .to_dict() untuk membuat salinan yang dapat dimodifikasi
    # agar library stauth.Authenticate tidak memicu TypeError pada st.secrets.
    try:
        credentials_copy = config['credentials'].to_dict()
    except Exception as e:
        # Jika struktur secrets salah (misal, tidak ada kunci 'credentials')
        st.error(f"❌ ERROR: Struktur Secrets salah atau kunci 'credentials' tidak ada. Detail: {e}")
        return

    # 3. Inisialisasi Authenticator menggunakan salinan data
    authenticator = stauth.Authenticate(
        credentials_copy,  # <-- Menggunakan salinan yang aman
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )

    # 4. Tampilkan Widget Login
    name, authentication_status, username = authenticator.login('Login Dashboard', 'main')

    if authentication_status:
        # Jika berhasil login
        st.sidebar.success(f'Anda login sebagai: {name}')
        authenticator.logout('Logout', 'sidebar') 
        
        # Panggil konten utama aplikasi yang terproteksi
        app_content() 
        
    elif authentication_status is False:
        # Jika gagal
        st.error('Username atau password salah')

    elif authentication_status is None:
        # Tampilan awal
        st.warning('Silakan login untuk mengakses Dashboard')


if __name__ == '__main__':
    main()
