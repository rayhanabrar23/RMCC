# streamlitll.py (File Utama/Index)

import streamlit as st

def main():
    # Mengatur layout dan judul halaman
    st.set_page_config(page_title="LL & CL Dashboard", layout="wide")
    
    logo_url = "https://www.pei.co.id/images/logo-grey-3x.png" 
    
    # -----------------------------------------------------------
    # KODE STABIL UNTUK MENEMPATKAN LOGO DI PALING ATAS
    # -----------------------------------------------------------
    # Menggunakan fitur bawaan st.logo()
    st.logo(logo_url, icon_image=None) 
    
    # Anda juga bisa menyesuaikan lebar jika logo terlalu besar:
    # st.logo(logo_url, icon_image=None, link="https://www.pei.co.id/") 
    # -----------------------------------------------------------
    
    # Konten halaman utama Anda
    st.title("📊 LL & CL Report Generator Dashboard")
    st.markdown("""
    Selamat datang! Aplikasi ini telah dibagi menjadi dua halaman (aplikasi) terpisah yang dapat Anda akses melalui **menu navigasi di sebelah kiri** (ikon **>**).

    Pilih halaman:
    
    - **Lendable Limit (LL):** Untuk menghitung posisi Lendable Limit.
    - **Concentration Limit (CL):** Untuk menghitung Batas Konsentrasi dan Haircut.

    _Setiap halaman memerlukan set file input yang berbeda._
    """)

if __name__ == '__main__':
    main()
