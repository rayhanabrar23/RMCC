import streamlit as st
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from io import BytesIO
from datetime import datetime

# ===============================================================
# 1. KONFIGURASI HALAMAN & GLOBAL
# ===============================================================
st.set_page_config(page_title="Laman Perhitungan Haircut dan Concentration Limit", layout="wide")

# Konstanta Logika
THRESHOLD_5M = 5_000_000_000
TARGET_100 = 100.0
TOLERANCE = 1e-6 
COL_RMCC = 'CONCENTRATION LIMIT USULAN RMCC'
COL_LISTED = 'CONCENTRATION LIMIT TERKENA % LISTED SHARES'
COL_FF = 'CONCENTRATION LIMIT TERKENA % FREE FLOAT'
COL_PERHITUNGAN = 'CONCENTRATION LIMIT SESUAI PERHITUNGAN'

# Inisialisasi State Profil Emiten (Agar inputan user di web tersimpan)
if "df_profil_emiten" not in st.session_state:
    st.session_state["df_profil_emiten"] = pd.DataFrame([
        {"KODE": "LPKR", "LIMIT": 10_000_000_000},
        {"KODE": "MLPL", "LIMIT": 10_000_000_000},
        {"KODE": "NOBU", "LIMIT": 10_000_000_000},
        {"KODE": "PTPP", "LIMIT": 50_000_000_000},
        {"KODE": "SILO", "LIMIT": 10_000_000_000}
    ])

# ===============================================================
# 2. FUNGSI LOGIKA PERHITUNGAN
# ===============================================================

def calc_concentration_limit_listed(row):
    try:
        if row['PERBANDINGAN DENGAN LISTED SHARES (Sesuai Perhitungan)'] >= 0.05:
            return 0.0499 * row['LISTED SHARES'] * row['CLOSING PRICE']
        return np.nan
    except: return np.nan

def calc_concentration_limit_ff(row):
    try:
        if row['PERBANDINGAN DENGAN FREE FLOAT (Sesuai Perhitungan)'] >= 0.20:
            return 0.1999 * row['FREE FLOAT (DALAM LEMBAR)'] * row['CLOSING PRICE']
        return np.nan
    except: return np.nan

def calculate_concentration_limit(df_source, mapping_df):
    df = df_source.copy()
    
    # Clean Kode Efek
    if 'KODE EFEK' not in df.columns: 
        df = df.rename(columns={df.columns[0]: 'KODE EFEK'})
    df['KODE EFEK'] = df['KODE EFEK'].astype(str).str.strip().str.upper()
    
    # 1. Hitung Kriteria Listed & FF
    df[COL_LISTED] = df.apply(calc_concentration_limit_listed, axis=1)
    df[COL_FF] = df.apply(calc_concentration_limit_ff, axis=1)

    # 2. Logika Saham Marjin Baru
    df['SAHAM MARJIN BARU?'] = df['SAHAM MARJIN BARU?'].astype(str).str.upper().str.strip()
    df['CL_MARJIN_BARU'] = np.where(df['SAHAM MARJIN BARU?'] == 'YA', 
                                    df[COL_PERHITUNGAN] * 0.50, 
                                    df[COL_PERHITUNGAN])

    # 3. Cari Nilai Minimum dari 4 Kriteria
    limit_cols_for_min = ['CL_MARJIN_BARU', COL_LISTED, COL_FF, COL_PERHITUNGAN]
    df['MIN_CL_OPTION'] = df[limit_cols_for_min].fillna(np.inf).min(axis=1)
    
    # Default RMCC adalah nilai terkecil
    df[COL_RMCC] = df['MIN_CL_OPTION']

    # 4. OVERRIDE PROFIL EMITEN (Dari Tabel Streamlit)
    user_mapping = dict(zip(mapping_df['KODE'].str.strip().str.upper(), mapping_df['LIMIT']))
    
    def apply_user_override(row):
        kode = row['KODE EFEK']
        current_val = row[COL_RMCC]
        if kode in user_mapping:
            limit_user = user_mapping[kode]
            if current_val == 0.0: return 0.0
            return min(current_val, limit_user)
        return current_val

    df[COL_RMCC] = df.apply(apply_user_override, axis=1)

    # 5. PROTEKSI: Set Nol jika < 5M atau Haircut 100%
    df['HAIRCUT PEI USULAN DIVISI'] = np.where(
        (df['UMA'].fillna('-') != '-') & pd.notna(df['UMA']), 
        df['HAIRCUT KPEI'], 
        df['HAIRCUT PEI']
    )
    
    mask_to_zero = (df[COL_RMCC] < THRESHOLD_5M) | (df['HAIRCUT PEI USULAN DIVISI'] >= 1.0)
    df.loc[mask_to_zero, COL_RMCC] = 0.0

    return df

# ===============================================================
# 3. FUNGSI INJECTOR KE EXCEL (FIXED: KOLOM P, Q, R, S)
# ===============================================================

def update_excel_template(file_template, df_hasil):
    output = BytesIO()
    wb = load_workbook(file_template)
    
    if "HC" not in wb.sheetnames or "CONC" not in wb.sheetnames:
        raise ValueError("Template harus punya sheet 'HC' dan 'CONC'")
        
    ws_hc = wb["HC"]
    ws_conc = wb["CONC"]

    # Loop data mulai baris 5
    for i, row in enumerate(df_hasil.to_dict('records'), start=5):
        # --- SHEET HC ---
        ws_hc.cell(row=i, column=3, value=row.get('KODE EFEK'))
        ws_hc.cell(row=i, column=18, value=row.get('HAIRCUT PEI USULAN DIVISI'))

        # --- SHEET CONC (FIXED MAPPING) ---
        ws_conc.cell(row=i, column=3, value=row.get('KODE EFEK'))                   # Col C
        ws_conc.cell(row=i, column=16, value=row.get('CL_MARJIN_BARU'))             # Col P
        ws_conc.cell(row=i, column=17, value=row.get(COL_LISTED))                   # Col Q
        ws_conc.cell(row=i, column=18, value=row.get(COL_FF))                       # Col R
        ws_conc.cell(row=i, column=19, value=row.get(COL_RMCC))                     # Col S
        
    wb.save(output)
    output.seek(0)
    return output

# ===============================================================
# 4. ANTARMUKA STREAMLIT
# ===============================================================

def main():
    st.title("🛡️ Laman Perhitungan Haircut dan Concentration Limit")
    st.markdown("---")
    
    # 1. Bagian Konfigurasi Profil Emiten
    st.subheader("⚙️ Konfigurasi Profil Emiten (Override)")
    st.info("Input kode saham dan limit (misal 10M = 10000000000). Gunakan tombol + di bawah tabel untuk tambah.")
    
    edited_df = st.data_editor(
        st.session_state["df_profil_emiten"],
        num_rows="dynamic",
        column_config={
            "KODE": st.column_config.TextColumn("Kode Saham", required=True),
            "LIMIT": st.column_config.NumberColumn("Limit (IDR)", format="%d", min_value=0)
        },
        key="editor_emiten"
    )

    st.markdown("---")
    
    # 2. Upload Files
    col1, col2 = st.columns(2)
    with col1:
        source_file = st.file_uploader("1. Upload Raw Data (XLSX)", type=['xlsx'])
    with col2:
        template_file = st.file_uploader("2. Upload Template Target (XLSX)", type=['xlsx'])

    if source_file and template_file:
        if st.button("🚀 Proses & Update Template", type="primary"):
            try:
                # Baca Data
                df_input = pd.read_excel(source_file)
                
                with st.spinner("Menghitung..."):
                    # Proses Logika
                    df_final = calculate_concentration_limit(df_input, edited_df)
                    
                    # Suntik ke Excel
                    template_file.seek(0)
                    processed_file = update_excel_template(template_file, df_final)
                
                st.success("✅ Berhasil! Data Listed Shares dan Freefloat sudah masuk ke template.")
                
                # Preview singkat
                st.dataframe(df_final[['KODE EFEK', COL_LISTED, COL_FF, COL_RMCC]].head(10))

                # Download
                st.download_button(
                    label="⬇️ Download Updated Excel",
                    data=processed_file,
                    file_name=f"Updated_Template_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"❌ Terjadi Kesalahan: {e}")

if __name__ == '__main__':
    main()
