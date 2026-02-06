import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Excel Merger Pro", layout="centered")

st.title("📊 Excel Margin Trades Merger")
st.info("Gabungkan data harian ke dalam file template secara otomatis.")

# 1. Upload File Template
template_file = st.file_uploader("Upload File Template (2026_Q1_Margin_Trades)", type=['xlsx'])

# 2. Upload Banyak File Data Harian
daily_files = st.file_uploader("Upload Semua File MarginTrades Harian", type=['xlsx'], accept_multiple_files=True)

if st.button("Proses & Gabungkan Data"):
    if template_file and daily_files:
        try:
            # Load template
            # Kita gunakan ExcelFile agar bisa baca sheet spesifik tanpa merusak sheet lain
            template_df = pd.read_excel(template_file, sheet_name='Januari')
            
            # List untuk menampung semua data baru
            all_daily_data = []

            # Urutkan file harian berdasarkan nama agar tanggalnya runut
            sorted_files = sorted(daily_files, key=lambda x: x.name)

            for f in sorted_files:
                df = pd.read_excel(f)
                all_daily_data.append(df)
            
            # Gabungkan semua file harian
            combined_daily = pd.concat(all_daily_data, ignore_index=True)
            
            # Gabungkan dengan template (Opsional: jika di template sudah ada data lama)
            # Jika ingin lgsg menimpa/mengisi sheet Januari:
            final_df = pd.concat([template_df, combined_daily], ignore_index=True)

            # Proses Simpan ke Memory (agar bisa didownload)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Jika template punya sheet lain, kamu bisa menambahkannya di sini
                final_df.to_excel(writer, sheet_name='Januari', index=False)
            
            processed_data = output.getvalue()

            st.success(f"Berhasil menggabungkan {len(daily_files)} file!")
            
            # 3. Tombol Download
            st.download_button(
                label="📥 Download Hasil Gabungan",
                data=processed_data,
                file_name="Updated_2026_Q1_Margin_Trades.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"Terjadi kesalahan: {e}")
    else:
        st.warning("Mohon upload template dan file harian terlebih dahulu.")
