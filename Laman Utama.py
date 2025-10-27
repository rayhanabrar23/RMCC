# streamlitll.py (File Utama/Index)

import streamlit as st

def main():
    # Mengatur layout dan judul halaman
    st.set_page_config(page_title="LL & CL Dashboard", layout="wide")
    
    logo_url = "https://www.pei.co.id/images/logo-grey-3x.png" 
    
    # -----------------------------------------------------------
    # KODE INJEKSI CSS UNTUK MENEMPATKAN LOGO DI PALING ATAS
    # -----------------------------------------------------------
    
    # Menggunakan HTML/CSS untuk menempatkan logo di bagian paling atas
    # dan mendorong menu navigasi ke bawah.
    st.markdown(
        f"""
        <style>
            /* 1. Mengubah padding atas default pada sidebar agar logo bisa di atas */
            [data-testid="stSidebar"] {{
                padding-top: 0px !important; 
            }}
            
            /* 2. Mengubah posisi logo di sidebar. Kita akan menggunakan HTML/CSS di sidebar */
            [data-testid="stSidebarNav"] {{
                padding-top: 100px; /* Menambahkan padding di atas menu navigasi agar logo terlihat */
            }}
            
            /* 3. Gaya umum untuk logo di sidebar (untuk memastikan gambar terlihat rapi) */
            .sidebar-logo {{
                display: block;
                padding: 15px 10px 10px 10px;
                background-color: white; /* Warna background sidebar */
            }}

        </style>
        """,
        unsafe_allow_html=True
    )

    # 4. Menampilkan logo di sidebar menggunakan HTML (bukan st.sidebar.image)
    # Ini harus ditaruh di st.sidebar.markdown agar berada di sidebar
    st.sidebar.markdown(
        f'<div class="sidebar-logo"><img src="{logo_url}" width="150" style="display: block; margin: auto;"/></div>',
        unsafe_allow_html=True
    )
    
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
