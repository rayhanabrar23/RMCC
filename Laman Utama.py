import pickle
from pathlib import Path
import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd 
import os 


names = ["Rayhan Abrar", "Ismi Arnum"]
usernames = ["abrar", "ismi"]


file_path = Path(__file__).parent / "hashed_pw.pkl"
with file_path.open("rb") as file:
    hashed_passwords = pickle.load(file)

authenticator = stauth.Authenticate(names, usernames, hashed_passwords, 
    "RMCC_dashboard", "abcdef", cookie_expiry_days=30)

name, authentication_status, username = authenticator.login("Login", "main")

if authentication_status == False:
    st.error("Userame/password is incorrect")

if authentication_status == None:
    st.warning("Please enter your usernam and password")

if authentication_status:

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


authenticator.logout("Logout", "sidebar")
st.sidebar.title(f"Welcome {name}")

# ----------------------------------------------------
# FUNGSI MAIN()
# ----------------------------------------------------
def main():
    st.set_page_config(page_title="Dashboard Utama", layout="centered")

    # Langsung jalankan konten aplikasi tanpa proses login
    app_content() 

if __name__ == '__main__':
    main()

