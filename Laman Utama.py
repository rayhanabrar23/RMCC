import pickle
from pathlib import Path
import streamlit as st
import streamlit_authenticator as stauth # Menggunakan alias stauth
import pandas as pd
import os

# --- 1. KONFIGURASI PENGGUNA (Menggunakan Format Lama) ---
# CATATAN: Format ini tidak direkomendasikan untuk produksi. 
# Sebaiknya gunakan format Dictionary yang sudah kita coba sebelumnya atau config.yaml
names = ["Rayhan Abrar", "Ismi Arnum"]
usernames = ["abrar", "ismi"]

# --- 2. MEMUAT PASSWORD HASHED ---
# Pastikan file 'hashed_pw.pkl' berada di folder yang sama dengan file Python ini.
try:
    file_path = Path(__file__).parent / "hashed_pw.pkl"
    with file_path.open("rb") as file:
        hashed_passwords = pickle.load(file)
except FileNotFoundError:
    st.error("File 'hashed_pw.pkl' tidak ditemukan. Pastikan file ada di direktori yang sama.")
    st.stop()
except Exception as e:
    st.error(f"Gagal memuat file password: {e}")
    st.stop()


# --- 3. FUNGSI KONTEN UTAMA APLIKASI ---
# Konten ini HANYA dipanggil jika login berhasil.
def app_content(user_name):
    # Pastikan logo ini masih berlaku
    st.logo("https://www.pei.co.id/images/logo-grey-3x.png", icon_image=None)  
    st.title("RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD")
    st.success(f"Anda login sebagai: {user_name}")
    st.markdown("---")
    
    # Tambahkan konten dashboard Anda di sini
    # Misalnya: st.dataframe(data_rmcc)


# --- 4. FUNGSI UTAMA (MAIN) ---
def main():
    st.set_page_config(page_title="Dashboard Utama", layout="centered")

    # Inisialisasi Authenticator dengan keyword arguments yang BENAR untuk versi terbaru
    # Menggunakan stauth.Authenticate()
    authenticator = stauth.Authenticate(
        names=names,
        usernames=usernames,
        passwords=hashed_passwords,
        cookie_name="RMCC_dashboard",
        key="abcdef",
        cookie_expiry_days=30
    )

    # Menampilkan widget login
    name, authentication_status, username = authenticator.login("Login", "main")

    # --- 5. LOGIKA DISPLAY BERDASARKAN STATUS AUTENTIKASI ---

    if authentication_status is False:
        st.error("Username/password salah")
        # st.stop() # Hentikan eksekusi jika gagal

    elif authentication_status is None:
        st.warning("Silakan masukkan username dan password")

    elif authentication_status:
        # Jika autentikasi berhasil
        
        # Tampilkan Tombol Logout di sidebar
        authenticator.logout("Logout", "sidebar")
        
        # Tampilkan nama pengguna di sidebar
        st.sidebar.title(f"Selamat Datang, {name}")
        
        # Panggil konten aplikasi
        app_content(name) 
        
        # Tambahkan menu navigasi sidebar Anda di sini
        # st.sidebar.header("Navigasi")
        # st.sidebar.button("Lendable Limit")
        # st.sidebar.button("Concentration Limit")
        
# --- 6. EKSEKUSI MAIN ---
if __name__ == '__main__':
    main()
