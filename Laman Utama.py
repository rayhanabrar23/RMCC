import pickle
from pathlib import Path
import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
import os

# --- 1. KONFIGURASI PENGGUNA ---
names = ["Rayhan Abrar", "Ismi Arnum"]
usernames = ["abrar", "ismi"]

# --- 2. MEMUAT PASSWORD HASHED ---
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
# Fungsi ini harus didefinisikan di level atas (tidak di-indent)
def app_content(user_name):
    st.logo("https://www.pei.co.id/images/logo-grey-3x.png", icon_image=None)  
    st.title("RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD")
    st.success(f"Anda login sebagai: {user_name}")
    st.markdown("---")
    
    # Tambahkan konten dashboard Anda di sini
    # st.dataframe(data_rmcc)


# --- 4. FUNGSI UTAMA (MAIN) ---
# Fungsi ini juga harus didefinisikan di level atas (tidak di-indent)
def main():
    st.set_page_config(page_title="Dashboard Utama", layout="centered")

    # Inisialisasi Authenticator
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

    elif authentication_status is None:
        st.warning("Silakan masukkan username dan password")

    # Ini adalah blok IF yang dimaksud pada error Anda. Baris berikutnya di dalamnya HARUS di-indent.
    elif authentication_status: 
        
        # Tampilkan Tombol Logout di sidebar (DI-INDENT)
        authenticator.logout("Logout", "sidebar")
        
        # Tampilkan nama pengguna di sidebar (DI-INDENT)
        st.sidebar.title(f"Selamat Datang, {name}")
        
        # Panggil konten aplikasi (DI-INDENT)
        app_content(name) 
        
        # Tambahkan menu navigasi sidebar Anda di sini (DI-INDENT)
        # st.sidebar.header("Navigasi")
        # st.sidebar.button("Lendable Limit")

        
# --- 6. EKSEKUSI MAIN ---
if __name__ == '__main__':
    main()
