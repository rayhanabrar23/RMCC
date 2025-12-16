# Laman Utama.py (VERSI MINIMAL TANPA AUTENTIKASI)
import streamlit as st
import pandas as pd 
import os 
# Hapus: import streamlit_authenticator as auth_modul
# Hapus: import yaml 
# Hapus: from yaml.loader import SafeLoader

# ----------------------------------------------------
# FUNGSI KONTEN UTAMA APLIKASI
# ----------------------------------------------------
def app_content():
    # Pastikan logo ini masih berlaku
    st.logo("https://www.pei.co.id/images/logo-grey-3x.png", icon_image=None)  
    st.title("RISK MANAGEMENT AND CREDIT CONTROL DASHBOARD")
    st.markdown("Aplikasi berjalan dalam mode bebas (tanpa login).")
    
    # Tambahkan konten dashboard Anda di sini (misalnya, loading data, grafik, dll.)
    st.success("Anda berhasil melewati fungsi login!")


# ----------------------------------------------------
# FUNGSI MAIN()
# ----------------------------------------------------
def main():
    st.set_page_config(page_title="Dashboard Utama", layout="centered")

    # Langsung jalankan konten aplikasi tanpa proses login
    app_content() 

if __name__ == '__main__':
    main()
