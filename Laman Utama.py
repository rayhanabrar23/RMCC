# streamlitll.py (File Utama/Index)

import streamlit as st

def main():
    # Mengatur layout dan judul halaman
    st.set_page_config(page_title="LL & CL Dashboard", layout="wide")
    
    # -----------------------------------------------------------
    # KODE INJEKSI CSS UNTUK MENEMPATKAN LOGO DI PALING ATAS
    # -----------------------------------------------------------
    logo_url = "https://www.pei.co.id/images/logo-grey-3x.png" 
    
    # CSS Custom untuk menempatkan logo di atas menu
    st.markdown(
        f"""
        <style>
            /* Mengubah posisi sidebar (container utama) agar konten absolut bekerja */
            [data-testid="stSidebar"] {{
                padding-top: 0 !important; /* Hapus padding default */
            }}
            
            /* Logo Container (kita akan membuatnya sendiri dan menempatkannya di paling atas) */
            .logo-container {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                background-color: white; /* Ganti dengan warna background sidebar Anda jika tidak putih */
                padding: 15px 10px 10px 10px; /* Padding atas, kanan, bawah, kiri */
                z-index: 1000; /* Pastikan logo di atas elemen lain */
                border-bottom: 1px solid #ddd; /* Opsional: garis pemisah */
            }}
            
            /* Menyesuaikan jarak menu navigasi agar tidak tertutup logo */
            [data-testid="stSidebarNav"] {{
                padding-top: 100px; /* Tambahkan padding agar menu bergeser ke bawah */
            }}

        </style>
        
        <div class="logo-container">
            <img src="{logo_url}" width="150" style="display: block; margin: auto;"/>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Hapus kode st.sidebar.image yang lama karena kita sudah menggunakan HTML
    # st.sidebar.image(logo_url, use_container_width=False, width=150)
    
    # -----------------------------------------------------------
    
    st.title("📊 LL & CL Report Generator Dashboard")
    st.markdown("""
    Selamat datang! Aplikasi ini telah dibagi menjadi dua halaman (aplikasi) terpisah...
    """)

if __name__ == '__main__':
    main()
