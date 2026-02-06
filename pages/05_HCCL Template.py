import streamlit as st
import pandas as pd
from io import BytesIO
from openpyxl import load_workbook

st.set_page_config(page_title="Margin Merger - High Volume", layout="centered")

st.title("📊 Margin Trades Merger (Big Data Mode)")

template_file = st.file_uploader("1. Upload Template (.xlsx)", type=['xlsx'])
daily_files = st.file_uploader("2. Upload CSV Harian (Banyak)", type=['csv'], accept_multiple_files=True)

if st.button("🚀 Proses & Gabungkan"):
    if template_file and daily_files:
        try:
            with st.spinner('Sedang mencicil penggabungan data...'):
                # 1. Load Template ke Memory
                template_bytes = template_file.read()
                book = load_workbook(BytesIO(template_bytes))
                
                # Kita siapkan writer yang menempel ke template
                output = BytesIO()
                
                # Pisahkan proses: Ambil header dulu dari file pertama
                # agar kita bisa membuat dataframe yang konsisten
                sorted_files = sorted(daily_files, key=lambda x: x.name)
                
                # Loop dan gabungkan secara bertahap (batching)
                # Kita baca template data lama dulu jika ada
                try:
                    final_df = pd.read_excel(BytesIO(template_bytes), sheet_name='Januari')
                except:
                    final_df = pd.DataFrame()

                # Tambahkan progres bar biar user gak bingung
                progress_bar = st.progress(0)
                
                for i, f in enumerate(sorted_files):
                    # Baca CSV satu per satu dengan tipe data yang dioptimalkan
                    temp_df = pd.read_csv(f, sep=None, engine='python', low_memory=True)
                    final_df = pd.concat([final_df, temp_df], ignore_index=True)
                    
                    # Update Progress
                    progress_bar.progress((i + 1) / len(sorted_files))
                    
                    # Opsional: Bersihkan variabel sementara untuk hemat RAM
                    del temp_df

                # 2. Tulis hasil akhir ke Sheet Januari
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    writer.book = book
                    final_df.to_excel(writer, sheet_name='Januari', index=False)
                
                processed_data = output.getvalue()

            st.success(f"Selesai! Berhasil menggabungkan total {len(final_df)} baris data.")
            
            st.download_button(
                label="📥 Download Hasil",
                data=processed_data,
                file_name="Updated_2026_Q1_Margin_Trades.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"Error: {e}. Coba kurangi jumlah file yang diupload sekaligus.")
    else:
        st.warning("Upload template dan CSV dulu.")
