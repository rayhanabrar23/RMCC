import streamlit as st
import pandas as pd
from io import BytesIO
from openpyxl import load_workbook

st.set_page_config(page_title="CSV to Excel Merger", layout="wide")

st.title("📊 Margin Trades Merger (Template Safe)")

col1, col2 = st.columns(2)
with col1:
    template_file = st.file_uploader("1. Upload Template (Excel)", type=['xlsx'])
with col2:
    daily_files = st.file_uploader("2. Upload File CSV Harian", type=['csv'], accept_multiple_files=True)

if st.button("🚀 Proses & Gabungkan"):
    if template_file and daily_files:
        try:
            # 1. Gabungkan semua CSV
            sorted_files = sorted(daily_files, key=lambda x: x.name)
            # engine='python' + sep=None supaya otomatis deteksi koma/titik-koma
            list_df = [pd.read_csv(f, sep=None, engine='python') for f in sorted_files]
            new_data_df = pd.concat(list_df, ignore_index=True)
            
            # 2. Baca Template
            template_bytes = template_file.read()
            
            # Ambil data lama dari sheet Januari (jika ada)
            try:
                old_data_df = pd.read_excel(BytesIO(template_bytes), sheet_name='Januari')
                final_df = pd.concat([old_data_df, new_data_df], ignore_index=True)
            except:
                final_df = new_data_df

            # 3. Masukkan ke Template TANPA menghapus sheet
            book = load_workbook(BytesIO(template_bytes))
            
            # Gunakan pd.ExcelWriter dengan mode 'a' (append) dan overlay
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                writer.book = book
                
                # Cek jika sheet Januari ada, arahkan writer ke sana
                if 'Januari' in book.sheetnames:
                    # Kita timpa isinya mulai dari baris pertama (index 0)
                    # Ini mencegah error "At least one sheet must be visible"
                    final_df.to_excel(writer, sheet_name='Januari', index=False)
                else:
                    final_df.to_excel(writer, sheet_name='Januari', index=False)
            
            st.success(f"Berhasil! Data digabung ke sheet 'Januari'.")

            st.download_button(
                label="📥 Download Hasil",
                data=output.getvalue(),
                file_name="Updated_2026_Q1_Margin_Trades.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"Waduh, ada error: {e}")
    else:
        st.warning("Upload dulu template dan file CSV-nya ya.")
