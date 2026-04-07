import streamlit as st
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from io import BytesIO
from datetime import datetime

# ===============================================================
# 1. KONFIGURASI HALAMAN
# ===============================================================
st.set_page_config(page_title="Laman Perhitungan Haircut dan Concentration Limit", layout="wide")

# ===============================================================
# 2. KONFIGURASI GLOBAL (LOGIKA ASLI)
# ===============================================================
COL_RMCC = 'CONCENTRATION LIMIT USULAN RMCC'
COL_LISTED = 'CONCENTRATION LIMIT TERKENA % LISTED SHARES'
COL_FF = 'CONCENTRATION LIMIT TERKENA % FREE FLOAT'
COL_PERHITUNGAN = 'CONCENTRATION LIMIT SESUAI PERHITUNGAN'
THRESHOLD_5M = 5_000_000_000
OVERRIDE_MAPPING = {
    'LPKR': 10_000_000_000, 'MLPL': 10_000_000_000,
    'NOBU': 10_000_000_000, 'PTPP': 50_000_000_000, 'SILO': 10_000_000_000
}

# ===============================================================
# 3. FUNGSI LOGIKA PERHITUNGAN
# ===============================================================

def calc_concentration_limit_listed(row):
    try:
        if row['PERBANDINGAN DENGAN LISTED SHARES (Sesuai Perhitungan)'] >= 0.05:
            return 0.0499 * row['LISTED SHARES'] * row['CLOSING PRICE']
        return None
    except Exception: return None

def calc_concentration_limit_ff(row):
    try:
        if row['PERBANDINGAN DENGAN FREE FLOAT (Sesuai Perhitungan)'] >= 0.20:
            return 0.1999 * row['FREE FLOAT (DALAM LEMBAR)'] * row['CLOSING PRICE']
        return None
    except Exception: return None

def calculate_concentration_limit(df_cl_source):
    df = df_cl_source.copy()
    if 'KODE EFEK' not in df.columns: 
        df = df.rename(columns={df.columns[0]: 'KODE EFEK'})
    
    df['KODE EFEK'] = df['KODE EFEK'].astype(str).str.strip()
    
    # 1. Hitung Kriteria
    df['SAHAM MARJIN BARU?'] = df['SAHAM MARJIN BARU?'].astype(str).str.upper().str.strip()
    df['CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU'] = np.where(
        df['SAHAM MARJIN BARU?'] == 'YA', df[COL_PERHITUNGAN] * 0.50, df[COL_PERHITUNGAN]
    )
    df[COL_LISTED] = df.apply(calc_concentration_limit_listed, axis=1)
    df[COL_FF] = df.apply(calc_concentration_limit_ff, axis=1)

    # 2. Cari Nilai Minimum
    limit_cols = ['CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU', COL_LISTED, COL_FF, COL_PERHITUNGAN]
    df[COL_RMCC] = df[limit_cols].fillna(np.inf).min(axis=1)

    # 3. Override Khusus & Threshold 5M
    def apply_final_logic(row):
        val = row[COL_RMCC]
        kode = row['KODE EFEK']
        # Override Emiten
        if kode in OVERRIDE_MAPPING:
            val = min(val, OVERRIDE_MAPPING[kode])
        # Threshold 5M
        if val < THRESHOLD_5M:
            return 0.0
        return val

    df[COL_RMCC] = df.apply(apply_final_logic, axis=1)
    
    # 4. Haircut Logic
    df['HAIRCUT PEI USULAN DIVISI'] = np.where(
        (df['UMA'].fillna('-') != '-') & pd.notna(df['UMA']), 
        df['HAIRCUT KPEI'], df['HAIRCUT PEI']
    )
    
    return df

# ===============================================================
# 4. FUNGSI INJECTOR EXCEL
# ===============================================================

def update_excel_template(file_template, df_hasil):
    output = BytesIO()
    wb = load_workbook(file_template)
    ws_conc = wb["CONC"]
    ws_hc = wb["HC"]

    for i, row in enumerate(df_hasil.to_dict('records'), start=5):
        # Sheet CONC
        ws_conc.cell(row=i, column=3, value=row.get('KODE EFEK'))
        ws_conc.cell(row=i, column=19, value=row.get(COL_RMCC))
        
        # Sheet HC
        ws_hc.cell(row=i, column=3, value=row.get('KODE EFEK'))
        ws_hc.cell(row=i, column=18, value=row.get('HAIRCUT PEI USULAN DIVISI'))

    wb.save(output)
    output.seek(0)
    return output

# ===============================================================
# 5. ANTARMUKA STREAMLIT
# ===============================================================

st.title("🛡️ Laman Perhitungan Haircut dan Concentration Limit")

source_file = st.file_uploader("Upload Raw Data (XLSX)", type=['xlsx'])
template_file = st.file_uploader("Upload Template Target (XLSX)", type=['xlsx'])

if source_file and template_file:
    if st.button("🚀 Proses Data"):
        df_input = pd.read_excel(source_file)
        df_final = calculate_concentration_limit(df_input)
        
        template_file.seek(0)
        final_xlsx = update_excel_template(template_file, df_final)
        
        st.success("Selesai! Silakan download hasilnya.")
        st.download_button("⬇️ Download Hasil", final_xlsx, file_name="Hasil_Proses.xlsx")
