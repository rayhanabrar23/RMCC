import streamlit as st
import pandas as pd
from io import BytesIO
from openpyxl import load_workbook

st.set_page_config(page_title="Margin Merger Pro", layout="centered")

st.title("📊 Margin Trades Merger")
st.write("Gabungkan banyak CSV ke Sheet 'Januari' di Template Excel.")

# Upload file
template_file = st.file_uploader("1. Upload File Template (.xlsx)", type=['xlsx'])
daily_files = st.file_uploader("2. Upload File CSV Harian", type=['csv'], accept_multiple_files=True)

if st.button("🚀 Proses & Gabungkan"):
    if template_file and daily_files:
        try:
            with st.spinner('Sedang memproses data...'):
                # 1. Baca dan gabung semua CSV
                sorted_files = sorted(daily_files, key=lambda x: x.name)
                # sep=None otomatis mendeteksi pemisah CSV (koma/titik koma)
                list_df = [pd.read_csv(f, sep=None, engine='python') for f in sorted_files]
                combined_csv_df = pd.concat(list_df, ignore_index=True)

                # 2. Load template asli ke memory agar sheet lain tidak hilang
                template_bytes = template_file.read()
                book = load_workbook(BytesIO(template_bytes))
                
                # Simpan ke buffer memory
                output = BytesIO()
                
                # Gunakan ExcelWriter dengan engine openpyxl
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    writer.book = book
                    
                    # Cek jika sheet Januari ada, kita timpa. Jika tidak, buat baru.
                    # Kita tidak menghapus sheet (remove), tapi langsung overwrite datanya.
                    combined_csv_df.to_excel(writer, sheet_name='Januari', index=False)
                
                data_ready = output.getvalue()

            st.success(f"Berhasil menggabungkan {len(daily_files)} file ke sheet Januari!")
            
            # Tombol Download
            st.download_button(
                label="📥 Download Hasil Gabungan",
                data=data_ready,
                file_name="Updated_2026_Q1_Margin_Trades.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"Terjadi kesalahan teknis: {e}")
    else:
        st.warning("Mohon upload file template dan CSV-nya dulu ya.")
