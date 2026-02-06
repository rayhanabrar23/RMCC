import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="CSV to Excel Merger", layout="wide")

st.title("📊 Margin Trades Merger (CSV Version)")
st.markdown("Gabungkan data harian **.csv** ke dalam template **.xlsx**.")

# Layout kolom untuk upload
col1, col2 = st.columns(2)

with col1:
    template_file = st.file_uploader("1. Upload Template (Excel)", type=['xlsx'])

with col2:
    daily_files = st.file_uploader("2. Upload File CSV Harian", type=['csv'], accept_multiple_files=True)

if st.button("🚀 Proses & Gabungkan"):
    if template_file and daily_files:
        try:
            # 1. Baca data dari CSV (diurutkan berdasarkan nama file)
            sorted_files = sorted(daily_files, key=lambda x: x.name)
            
            # Gabungkan semua CSV menggunakan list comprehension
            list_df = [pd.read_csv(f) for f in sorted_files]
            combined_csv_data = pd.concat(list_df, ignore_index=True)
            
            # 2. Baca Template Excel
            # Kita baca sheet Januari (jika sudah ada isinya, kita timpa atau append)
            try:
                template_df = pd.read_excel(template_file, sheet_name='Januari')
                # Gabungkan data lama di template dengan data baru dari CSV
                final_df = pd.concat([template_df, combined_csv_data], ignore_index=True)
            except:
                # Jika sheet 'Januari' belum ada atau kosong
                final_df = combined_csv_data

            # 3. Simpan ke Memory
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                final_df.to_excel(writer, sheet_name='Januari', index=False)
            
            st.success(f"Berhasil memproses {len(daily_files)} file CSV!")

            # 4. Tombol Download
            st.download_button(
                label="📥 Download Hasil (.xlsx)",
                data=output.getvalue(),
                file_name="Updated_2026_Q1_Margin_Trades.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.warning("Pastikan kedua jenis file sudah di-upload.")
