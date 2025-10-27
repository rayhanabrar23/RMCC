# streamlitll.py (File Utama/Index)

import streamlit as st

def main():
    # Mengatur layout dan judul halaman
    st.set_page_config(page_title="LL & CL Dashboard", layout="wide")
    
    # -----------------------------------------------------------
    # KODE UNTUK MENAMBAH LOGO DI SIDEBAR MENGGUNAKAN URL LANGSUNG
    # -----------------------------------------------------------
    logo_url = "https://www.pei.co.id/images/logo-grey-3x.png" 
    
    # Menampilkan gambar logo di awal sidebar
    # PARAMETER use_column_width DIGANTI MENJADI use_container_width
    st.sidebar.image(logo_url, use_container_width=False, width=150)
    
    # -----------------------------------------------------------
    
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
