# pages/03_UMA_Scraper.py

import streamlit as st
import pandas as pd
import requests
from datetime import datetime
from io import BytesIO

# --- KONSTANTA ---
UMA_API_URL = "https://www.idx.co.id/api/idx-corp/latest_uma"

# --- FUNGSI UTAMA UNTUK MENGAMBIL DATA ---
@st.cache_data(ttl=3600) # Data di-cache selama 1 jam
def fetch_uma_data(target_month_name):
    """Mengambil data UMA langsung dari API IDX dan memfilternya berdasarkan bulan."""
    
    st.info(f"Mengambil data UMA terbaru dari IDX...")
    
    try:
        # Panggilan API
        response = requests.get(UMA_API_URL, timeout=15)
        response.raise_for_status() # Cek error HTTP
        
        data = response.json()
        
        if 'data' not in data or not data['data']:
            st.warning("API berhasil diakses, tetapi tidak ada data UMA yang dikembalikan.")
            return pd.DataFrame()

        # Konversi ke DataFrame
        df_uma = pd.DataFrame(data['data'])
        
        # Kolom hasil dari API: 'AnnouncementDate', 'Description', 'Code'
        df_uma.rename(columns={
            'AnnouncementDate': 'Tanggal', 
            'Description': 'Keterangan UMA',
            'Code': 'Kode Emiten' # Kode emiten sudah bersih di kolom 'Code' dari API
        }, inplace=True)
        
        # Format Tanggal
        df_uma['Tanggal'] = pd.to_datetime(df_uma['Tanggal'], format='%Y-%m-%d %H:%M:%S').dt.strftime('%Y-%m-%d')
        
        # Filter berdasarkan bulan target
        df_filtered = df_uma[
            df_uma['Tanggal'].str.contains(target_month_name, case=False, na=False)
        ].copy()
        
        # Memilih dan menata ulang kolom
        df_result = df_filtered[['Tanggal', 'Kode Emiten', 'Keterangan UMA']]

        return df_result
        
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Gagal koneksi ke API IDX. Cek koneksi internet atau URL. Error: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Terjadi kesalahan dalam pemrosesan data: {e}")
        return pd.DataFrame()


# --- FUNGSI UTAMA STREAMLIT ---
def app():
    st.title("🕷️ UMA (Unusual Market Activity) Scraper")
    st.markdown("Alat ini mengambil data UMA langsung dari *API tersembunyi* IDX. **Metode ini lebih stabil dan cepat dibandingkan *Web Scraping* (Selenium).**")

    # Kontrol Input
    col1, col2 = st.columns(2)
    
    # Mendapatkan daftar bulan saat ini
    current_year = datetime.now().year
    
    target_month_num = col1.selectbox(
        "Pilih Bulan Target:",
        range(1, 13),
        format_func=lambda x: datetime(current_year, x, 1).strftime("%B")
    )
    
    target_year = col2.selectbox(
        "Pilih Tahun Target:",
        range(current_year, current_year - 3, -1)
    )

    # Format bulan menjadi nama 3 huruf (cth: Okt, Jan, Sep)
    target_month_name = datetime(target_year, target_month_num, 1).strftime("%b")

    if st.button(f"Ambil Data UMA Bulan {target_month_name} {target_year}", type="primary"):
        
        # Hapus st.spinner() karena st.cache_data sudah memberikan indikasi loading
        df_result = fetch_uma_data(target_month_name)
        
        if not df_result.empty:
            st.success(f"✅ Berhasil mendapatkan {len(df_result)} data UMA untuk bulan {target_month_name}.")
            
            # Tampilkan data
            st.subheader("Data UMA Hasil Filter")
            st.dataframe(df_result, use_container_width=True)
            
            # Sediakan tombol download
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                df_result.to_excel(writer, sheet_name=f'UMA_{target_month_name}', index=False)
            
            excel_buffer.seek(0)

            st.download_button(
                label=f"💾 Unduh Data UMA {target_month_name}.xlsx",
                data=excel_buffer,
                file_name=f"Output_UMA_Data_{target_month_name}_{target_year}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Tidak ada data UMA yang ditemukan untuk periode ini.")

if __name__ == '__main__':
    app()