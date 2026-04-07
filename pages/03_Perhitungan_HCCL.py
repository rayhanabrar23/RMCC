import streamlit as st
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from io import BytesIO
from datetime import datetime

# ===============================================================
# 1. KONFIGURASI HALAMAN & GLOBAL
# ===============================================================
st.set_page_config(page_title="Laman Perhitungan RMCC", layout="wide")

THRESHOLD_5M = 5_000_000_000
COL_RMCC = 'CONCENTRATION LIMIT USULAN RMCC'
COL_LISTED = 'CONCENTRATION LIMIT TERKENA % LISTED SHARES'
COL_FF = 'CONCENTRATION LIMIT TERKENA % FREE FLOAT'
COL_PERHITUNGAN = 'CONCENTRATION LIMIT SESUAI PERHITUNGAN'

if "df_profil_emiten" not in st.session_state:
    st.session_state["df_profil_emiten"] = pd.DataFrame([
        {"KODE": "LPKR", "LIMIT": 10_000_000_000},
        {"KODE": "MLPL", "LIMIT": 10_000_000_000},
        {"KODE": "NOBU", "LIMIT": 10_000_000_000},
        {"KODE": "PTPP", "LIMIT": 50_000_000_000},
        {"KODE": "SILO", "LIMIT": 10_000_000_000}
    ])

# ===============================================================
# 2. FUNGSI LOGIKA PERHITUNGAN (DIPERKUAT)
# ===============================================================

def calculate_concentration_limit(df_source, mapping_df):
    df = df_source.copy()
    
    # 1. Pastikan Nama Kolom Kunci
    if 'KODE EFEK' not in df.columns: 
        df = df.rename(columns={df.columns[0]: 'KODE EFEK'})
    df['KODE EFEK'] = df['KODE EFEK'].astype(str).str.strip().str.upper()
    
    # 2. Hitung Kriteria Listed & FF
    def calc_listed(row):
        try:
            if row['PERBANDINGAN DENGAN LISTED SHARES (Sesuai Perhitungan)'] >= 0.05:
                return 0.0499 * row['LISTED SHARES'] * row['CLOSING PRICE']
            return np.nan
        except: return np.nan

    def calc_ff(row):
        try:
            if row['PERBANDINGAN DENGAN FREE FLOAT (Sesuai Perhitungan)'] >= 0.20:
                return 0.1999 * row['FREE FLOAT (DALAM LEMBAR)'] * row['CLOSING PRICE']
            return np.nan
        except: return np.nan

    df[COL_LISTED] = df.apply(calc_listed, axis=1)
    df[COL_FF] = df.apply(calc_ff, axis=1)

    # 3. Logika Saham Marjin Baru
    df['SAHAM MARJIN BARU?'] = df['SAHAM MARJIN BARU?'].astype(str).str.upper().str.strip()
    df['CL_MARJIN_BARU'] = np.where(df['SAHAM MARJIN BARU?'] == 'YA', 
                                    df[COL_PERHITUNGAN] * 0.50, 
                                    df[COL_PERHITUNGAN])

    # 4. Cari Nilai Minimum (RMCC Awal)
    limit_cols = ['CL_MARJIN_BARU', COL_LISTED, COL_FF, COL_PERHITUNGAN]
    df['MIN_VAL'] = df[limit_cols].fillna(np.inf).min(axis=1)
    df[COL_RMCC] = df['MIN_VAL']

    # 5. Tentukan Keterangan Default
    df['KET_CONC'] = "Sesuai metode perhitungan"

    # 6. Apply Override Profil Emiten dari Tabel Web
    user_mapping = dict(zip(mapping_df['KODE'].str.strip().str.upper(), mapping_df['LIMIT']))
    for kode, limit_val in user_mapping.items():
        mask = (df['KODE EFEK'] == kode) & (df[COL_RMCC] > 0)
        # Jika nilai hitungan lebih besar dari limit user, turunkan nilainya
        df.loc[mask & (df[COL_RMCC] > limit_val), 'KET_CONC'] = "Penyesuaian karena profil emiten"
        df.loc[mask, COL_RMCC] = df.loc[mask, COL_RMCC].apply(lambda x: min(x, limit_val))

    # 7. Proteksi Haircut 100% & Threshold 5M
    df['HAIRCUT_FINAL'] = np.where((df['UMA'].fillna('-') != '-') & pd.notna(df['UMA']), 
                                   df['HAIRCUT KPEI'], df['HAIRCUT PEI'])
    
    mask_lt_5m = (df[COL_RMCC] < THRESHOLD_5M)
    mask_hc_100 = (df['HAIRCUT_FINAL'] >= 1.0)
    
    # Update keterangan jika kena potong threshold
    df.loc[mask_lt_5m & (df[COL_RMCC] > 0), 'KET_CONC'] = "Penyesuaian karena Batas Konsentrasi < Rp5 Miliar"
    
    # Eksekusi Nol-kan
    df.loc[mask_lt_5m | mask_hc_100, COL_RMCC] = 0.0
    
    # Update keterangan untuk UMA di sheet HC
    df['KET_HC'] = df['UMA'].apply(lambda x: f"Sesuai Haircut KPEI, mempertimbangkan pengumuman UMA dari BEI tanggal {x}" if pd.notna(x) and x != '-' else "Sesuai Metode Perhitungan")

    return df

# ===============================================================
# 3. FUNGSI INJECTOR (LENGKAP SEMUA KOLOM)
# ===============================================================

def update_excel_template(file_template, df_hasil):
    output = BytesIO()
    wb = load_workbook(file_template)
    ws_hc = wb["HC"]
    ws_conc = wb["CONC"]

    for i, row in enumerate(df_hasil.to_dict('records'), start=5):
        # --- SHEET HC ---
        ws_hc.cell(row=i, column=3, value=row.get('KODE EFEK'))
        ws_hc.cell(row=i, column=18, value=row.get('HAIRCUT_FINAL'))
        ws_hc.cell(row=i, column=20, value=row.get('KET_HC'))

        # --- SHEET CONC (KOLOM C, P, Q, R, S, V) ---
        ws_conc.cell(row=i, column=3, value=row.get('KODE EFEK'))           # Col C
        ws_conc.cell(row=i, column=16, value=row.get('CL_MARJIN_BARU'))     # Col P
        ws_conc.cell(row=i, column=17, value=row.get(COL_LISTED))           # Col Q
        ws_conc.cell(row=i, column=18, value=row.get(COL_FF))               # Col R
        ws_conc.cell(row=i, column=19, value=row.get(COL_RMCC))             # Col S
        ws_conc.cell(row=i, column=22, value=row.get('KET_CONC'))           # Col V (YANG TADI KOSONG)
        
    wb.save(output)
    output.seek(0)
    return output

# ===============================================================
# 4. STREAMLIT UI
# ===============================================================

def main():
    st.title("🛡️ Laman Perhitungan RMCC")
    
    with st.expander("⚙️ Konfigurasi Profil Emiten"):
        edited_df = st.data_editor(st.session_state["df_profil_emiten"], num_rows="dynamic", key="editor")

    col1, col2 = st.columns(2)
    with col1: src = st.file_uploader("Upload Raw Data", type=['xlsx'])
    with col2: tmpl = st.file_uploader("Upload Template", type=['xlsx'])

    if src and tmpl:
        if st.button("🚀 Proses", type="primary"):
            df_res = calculate_concentration_limit(pd.read_excel(src), edited_df)
            tmpl.seek(0)
            final_xlsx = update_excel_template(tmpl, df_res)
            
            st.success("Berhasil! Kolom Keterangan (V) dan RMCC sudah terisi.")
            st.download_button("⬇️ Download Hasil", final_xlsx, file_name="Report_RMCC_Final.xlsx")

if __name__ == '__main__':
    main()
