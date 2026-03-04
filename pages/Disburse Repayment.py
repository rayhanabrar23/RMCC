import streamlit as st
import pandas as pd
import openpyxl
from io import BytesIO
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

st.set_page_config(page_title="Finance Report Linkage", layout="wide")

st.title("📊 Disburse & Repayment Automator")
st.markdown("Solusi untuk file broker format .xls (XML/HTML) dan .xlsx.")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Konfigurasi")
    bulan_dipilih = st.selectbox("Pilih Bulan Proses", 
                                ["JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI", 
                                 "JULI", "AGUSTUS", "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER"])
    tahun_proses = st.text_input("Tahun", "2026")

def get_column_letter(month_name):
    mapping = {
        'JANUARI': 'F', 'FEBRUARI': 'G', 'MARET': 'H', 'APRIL': 'I',
        'MEI': 'J', 'JUNI': 'K', 'JULI': 'L', 'AGUSTUS': 'M',
        'SEPTEMBER': 'N', 'OKTOBER': 'O', 'NOVEMBER': 'P', 'DESEMBER': 'Q'
    }
    return mapping.get(month_name.upper(), 'F')

def smart_read_excel(uploaded_file):
    """Membaca berbagai jenis format .xls (Biner, XML, atau HTML)"""
    file_bytes = uploaded_file.getvalue()
    
    # Percobaan 1: Excel Standar (xlsx atau old biner xls)
    try:
        return pd.read_excel(BytesIO(file_bytes), header=None)
    except Exception:
        # Percobaan 2: Jika file sebenarnya adalah HTML/XML Spreadsheet 2003
        try:
            # Menggunakan lxml engine untuk membaca tabel HTML
            dfs = pd.read_html(BytesIO(file_bytes))
            if dfs:
                return dfs[0]
        except Exception as e:
            st.error(f"Gagal membaca {uploaded_file.name}: {e}")
            return None
    return None

# --- UPLOAD FILE ---
col1, col2 = st.columns(2)
with col1:
    master_file = st.file_uploader("1. Unggah File Master (Template .xlsx)", type=['xlsx'])
with col2:
    broker_files = st.file_uploader("2. Unggah Semua File Broker (.xls / .xlsx)", type=['xls', 'xlsx'], accept_multiple_files=True)

if master_file and broker_files:
    if st.button("🚀 Proses & Generate Laporan"):
        try:
            wb = openpyxl.load_workbook(master_file)
            ws_main = wb['Disburse & Repay Jan-Des']
            
            target_col = get_column_letter(bulan_dipilih)
            row_map_disburse = {'EP': 5, 'HD': 6, 'HP': 7, 'XC': 8}
            row_map_repayment = {'EP': 16, 'HD': 17, 'HP': 18, 'XC': 19}
            
            process_log = []

            for f in broker_files:
                fname = f.name.upper()
                code = next((c for c in ['EP', 'HD', 'HP', 'XC'] if f" {c}" in fname or f"{c}." in fname or fname.startswith(c)), None)
                
                if not code:
                    process_log.append({"File": f.name, "Status": "⚠️ Skip", "Keterangan": "Broker tidak terdeteksi"})
                    continue

                df_raw = smart_read_excel(f)
                if df_raw is None: continue

                val = 0
                # Menghilangkan NaA/NaN agar pencarian teks lebih akurat
                df_str = df_raw.astype(str)

                if "DISBURSE" in fname:
                    # Cari baris yang mengandung 'Grand Total'
                    mask = df_str.apply(lambda x: x.str.contains('Grand Total', case=False, na=False)).any(axis=1)
                    df_total = df_raw[mask]
                    
                    if not df_total.empty:
                        # Ambil nilai numerik terakhir di baris tersebut
                        row_values = pd.to_numeric(df_total.iloc[-1], errors='coerce').dropna()
                        val = row_values.iloc[-1] if not row_values.empty else 0
                    
                    ws_main[f"{target_col}{row_map_disburse[code]}"] = val
                    process_log.append({"File": f.name, "Status": "✅ Berhasil", "Keterangan": f"Disburse {code}: {val:,.0f}"})

                elif "REPAYMENT" in fname:
                    # Ambil kolom numerik terjauh (biasanya kolom ke-9 atau terakhir)
                    # Kita cari secara dinamis kolom mana yang berisi angka repayment
                    numeric_df = df_raw.apply(pd.to_numeric, errors='coerce')
                    last_col_with_data = numeric_df.dropna(axis=1, how='all').columns[-1]
                    val = numeric_df[last_col_with_data].dropna().iloc[-1] if not numeric_df[last_col_with_data].dropna().empty else 0
                    
                    ws_main[f"{target_col}{row_map_repayment[code]}"] = val
                    process_log.append({"File": f.name, "Status": "✅ Berhasil", "Keterangan": f"Repayment {code}: {val:,.0f}"})

            # Update Summary Tahunan
            if "Summary Tahunan" in wb.sheetnames:
                ws_sum = wb["Summary Tahunan"]
                month_list = ['JANUARI', 'FEBRUARI', 'MARET', 'APRIL', 'MEI', 'JUNI', 'JULI', 'AGUSTUS', 'SEPTEMBER', 'OKTOBER', 'NOVEMBER', 'DESEMBER']
                summary_row = month_list.index(bulan_dipilih.upper()) + 2
                ws_sum[f'B{summary_row}'] = f"=SUM('Disburse & Repay Jan-Des'!{target_col}5:{target_col}8)"

            output = BytesIO()
            wb.save(output)
            output.seek(0)

            st.table(pd.DataFrame(process_log))
            st.download_button(label="📥 Download Hasil", data=output, file_name=f"Update_{bulan_dipilih}.xlsx")

        except Exception as e:
            st.error(f"Terjadi kesalahan: {e}")
