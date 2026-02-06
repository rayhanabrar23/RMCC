import streamlit as st
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from io import BytesIO
from datetime import datetime

# ===============================================================
# 1. PROTEKSI LOGIN & KONFIGURASI HALAMAN
# ===============================================================
st.set_page_config(page_title="Laman Perhitungan Haircut dan Concentration Limit", layout="wide")

if "login_status" not in st.session_state or not st.session_state["login_status"]:
    st.error("🚨 Akses Ditolak! Silakan login di halaman utama terlebih dahulu.")
    st.stop()

# Jika ada file style_utils
try:
    from style_utils import apply_custom_style
    apply_custom_style()
except ImportError:
    pass

# ===============================================================
# 2. KONFIGURASI GLOBAL (LOGIKA ASLI)
# ===============================================================
COL_RMCC = 'CONCENTRATION LIMIT USULAN RMCC'
COL_LISTED = 'CONCENTRATION LIMIT TERKENA % LISTED SHARES'
COL_FF = 'CONCENTRATION LIMIT TERKENA % FREE FLOAT'
COL_PERHITUNGAN = 'CONCENTRATION LIMIT SESUAI PERHITUNGAN'
THRESHOLD_5M = 5_000_000_000
KODE_EFEK_KHUSUS = ['LPKR', 'MLPL', 'NOBU', 'PTPP', 'SILO']
OVERRIDE_MAPPING = {
    'LPKR': 10_000_000_000, 'MLPL': 10_000_000_000,
    'NOBU': 10_000_000_000, 'PTPP': 50_000_000_000, 'SILO': 10_000_000_000
}
TARGET_100 = 100.0
TOLERANCE = 1e-6 

# ===============================================================
# 3. FUNGSI LOGIKA PERHITUNGAN (LOGIKA ASLI KAMU)
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

def override_rmcc_limit(row):
    kode = row['KODE EFEK']
    nilai_rmcc = row[COL_RMCC]
    if kode in OVERRIDE_MAPPING:
        nilai_override = OVERRIDE_MAPPING[kode]
        if nilai_rmcc == 0.0: return 0.0
        return min(nilai_rmcc, nilai_override)
    return nilai_rmcc

def reset_concentration_limit(df_main, haircut_col="HAIRCUT PEI USULAN DIVISI", conc_limit_col=COL_RMCC, conc_calc_col=COL_PERHITUNGAN, tolerance=1e-6, threshold_limit=5_000_000_000, inplace=True):
    if not inplace: df_main = df_main.copy()
    if haircut_col not in df_main.columns: df_main[haircut_col] = 0.0
    df_main[haircut_col] = pd.to_numeric(df_main[haircut_col], errors='coerce')
    df_main[conc_calc_col] = pd.to_numeric(df_main[conc_calc_col], errors='coerce')
    valid_haircut = df_main[haircut_col].dropna()
    target_100_reset = 100.0 if not valid_haircut.empty and valid_haircut.max() > 1 + tolerance else 1.0
    mask_haircut_100 = (df_main[haircut_col].sub(target_100_reset).abs() < tolerance)
    mask_below_threshold = (df_main[conc_calc_col] < threshold_limit)
    df_main.loc[mask_haircut_100 | mask_below_threshold, conc_limit_col] = 0.0
    return df_main

def keterangan_uma(uma_date):
    if pd.notna(uma_date):
        if not isinstance(uma_date, datetime):
            try: uma_date = pd.to_datetime(str(uma_date))
            except Exception: return "Sesuai Metode Perhitungan"
        return f"Sesuai Haircut KPEI, mempertimbangkan pengumuman UMA dari BEI tanggal {uma_date.strftime('%d %b %Y')}"
    return "Sesuai Metode Perhitungan"

def calculate_concentration_limit(df_cl_source):
    df = df_cl_source.copy()
    if 'KODE EFEK' not in df.columns: 
        df = df.rename(columns={df.columns[0]: 'KODE EFEK'})
    df['KODE EFEK'] = df['KODE EFEK'].astype(str).str.strip()
    
    df['SAHAM MARJIN BARU?'] = df['SAHAM MARJIN BARU?'].astype(str).str.upper().str.strip()
    df['CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU'] = np.where(df['SAHAM MARJIN BARU?'] == 'YA', df[COL_PERHITUNGAN] * 0.50, df[COL_PERHITUNGAN])
    df[COL_LISTED] = df.apply(calc_concentration_limit_listed, axis=1)
    df[COL_FF] = df.apply(calc_concentration_limit_ff, axis=1)

    limit_cols_for_min = ['CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU', COL_LISTED, COL_FF, COL_PERHITUNGAN]
    df['MIN_CL_OPTION'] = df[limit_cols_for_min].fillna(np.inf).min(axis=1)
    mask_pemicu_nol = (df[limit_cols_for_min].fillna(np.inf) < THRESHOLD_5M).any(axis=1)
    df[COL_RMCC] = np.where(mask_pemicu_nol, 0.0, df['MIN_CL_OPTION'])

    mask_not_zero = (df[COL_RMCC] != 0.0)
    df.loc[mask_not_zero, COL_RMCC] = df.loc[mask_not_zero].apply(override_rmcc_limit, axis=1).round(0)

    df['HAIRCUT KPEI'] = pd.to_numeric(df['HAIRCUT KPEI'], errors='coerce').fillna(0)
    df['HAIRCUT PEI USULAN DIVISI'] = np.where((df['UMA'].fillna('-') != '-') & pd.notna(df['UMA']), df['HAIRCUT KPEI'], df['HAIRCUT PEI'])
    df = reset_concentration_limit(df)

    HAIRCUT_COL_USULAN = 'HAIRCUT PEI USULAN DIVISI'
    mask_rmcc_nol = (df[COL_RMCC] == 0)
    df['TEMP_HAIRCUT_VAL_ASLI'] = pd.to_numeric(df[HAIRCUT_COL_USULAN], errors='coerce') 
    df.loc[mask_rmcc_nol, HAIRCUT_COL_USULAN] = 1.0 

    df['PERTIMBANGAN DIVISI (HAIRCUT)'] = df['UMA'].apply(keterangan_uma)
    df['PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Sesuai metode perhitungan'

    # --- LOGIKA MASKER PRIORITAS ---
    mask_emiten = df['KODE EFEK'].isin(KODE_EFEK_KHUSUS)
    mask_nol_final = (df[COL_RMCC] == 0) & (~mask_emiten)
    mask_lt5m_strict = ((df['CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU'].fillna(np.inf) < THRESHOLD_5M) | (df[COL_PERHITUNGAN].fillna(np.inf) < THRESHOLD_5M) | (df[COL_LISTED].fillna(np.inf) < THRESHOLD_5M) | (df[COL_FF].fillna(np.inf) < THRESHOLD_5M) | (df[COL_RMCC].fillna(np.inf) < THRESHOLD_5M)) & mask_nol_final 
    mask_hc100_origin = ((df['TEMP_HAIRCUT_VAL_ASLI'].sub(1.0).abs() < TOLERANCE) | (df['TEMP_HAIRCUT_VAL_ASLI'].sub(TARGET_100).abs() < TOLERANCE)) & mask_nol_final & (~mask_lt5m_strict)
    mask_non_nol = (df[COL_RMCC] != 0)
    df['CL_OVERRIDE_VAL'] = df['KODE EFEK'].map(OVERRIDE_MAPPING).fillna(np.inf)
    mask_emiten_override = mask_non_nol & mask_emiten & (df[COL_RMCC].round(0) == df['CL_OVERRIDE_VAL'].round(0))
    mask_other_non_nol = mask_non_nol & (~mask_emiten_override)
    mask_kriteria_listed = pd.notna(df[COL_LISTED]); mask_kriteria_ff = pd.notna(df[COL_FF])
    mask_listed_saja = mask_other_non_nol & (df[COL_RMCC].round(0) == df[COL_LISTED].round(0))
    mask_ff_saja = mask_other_non_nol & (df[COL_RMCC].round(0) == df[COL_FF].round(0)) & (~mask_listed_saja)
    mask_marjin_baru = mask_other_non_nol & (df[COL_RMCC].round(0) == df['CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU'].round(0)) & (df['SAHAM MARJIN BARU?'] == 'YA') & (~mask_listed_saja) & (~mask_ff_saja)
    mask_listed_ff_upgrade = (mask_listed_saja | mask_ff_saja) & mask_kriteria_listed & mask_kriteria_ff

    df.loc[mask_lt5m_strict, 'PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Penyesuaian karena Batas Konsentrasi < Rp5 Miliar'
    df.loc[mask_lt5m_strict, 'PERTIMBANGAN DIVISI (HAIRCUT)'] = 'Penyesuaian karena Batas Konsentrasi 0'
    df.loc[mask_hc100_origin, 'PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Penyesuaian karena Haircut PEI 100%'
    df.loc[mask_emiten & mask_nol_final, 'PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Penyesuaian karena profil emiten'
    df.loc[mask_emiten_override, 'PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Penyesuaian karena profil emiten'
    df.loc[mask_marjin_baru, 'PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Penyesuaian karena saham baru masuk marjin'
    df.loc[mask_listed_saja, 'PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Penyesuaian karena melebihi 5% listed shares'
    df.loc[mask_ff_saja, 'PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Penyesuaian karena melebihi 20% free float'
    df.loc[mask_listed_ff_upgrade, 'PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Penyesuaian karena melebihi 5% listed & 20% free float'

    df = df.drop(columns=['MIN_CL_OPTION', 'TEMP_HAIRCUT_VAL_ASLI', 'CL_OVERRIDE_VAL'], errors='ignore')
    return df

# ===============================================================
# 4. FUNGSI INJECTOR (PINDAH KE TEMPLATE EXCEL)
# ===============================================================

def update_excel_template(file_template, df_hasil):
    output = BytesIO()
    wb = load_workbook(file_template)
    
    # Pastikan Sheet Ada
    if "HC" not in wb.sheetnames or "CONC" not in wb.sheetnames:
        raise ValueError("Template harus memiliki sheet bernama 'HC' dan 'CONC'")
        
    ws_hc = wb["HC"]
    ws_conc = wb["CONC"]

    # Loop data hasil (start=5 sesuai instruksi baris ke-5)
    for i, row in enumerate(df_hasil.to_dict('records'), start=5):
        # --- SHEET HC ---
        ws_hc.cell(row=i, column=3, value=row.get('KODE EFEK'))                   # C
        ws_hc.cell(row=i, column=18, value=row.get('HAIRCUT PEI USULAN DIVISI'))  # R
        ws_hc.cell(row=i, column=20, value=row.get('PERTIMBANGAN DIVISI (HAIRCUT)')) # T

        # --- SHEET CONC ---
        ws_conc.cell(row=i, column=3, value=row.get('KODE EFEK'))                 # C
        ws_conc.cell(row=i, column=16, value=row.get('CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU')) # P
        ws_conc.cell(row=i, column=17, value=row.get('CONCENTRATION LIMIT TERKENA % LISTED SHARES'))   # Q
        ws_conc.cell(row=i, column=18, value=row.get('CONCENTRATION LIMIT TERKENA % FREE FLOAT'))     # R
        ws_conc.cell(row=i, column=19, value=row.get(COL_RMCC))                   # S
        ws_conc.cell(row=i, column=22, value=row.get('PERTIMBANGAN DIVISI (CONC LIMIT)')) # V

    wb.save(output)
    output.seek(0)
    return output

# ===============================================================
# 5. ANTARMUKA STREAMLIT
# ===============================================================

def main():
    st.title("🛡️ HCCL Professional Data Integrator")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        source_file = st.file_uploader("1. Upload Raw Data (XLSX)", type=['xlsx'])
    with col2:
        template_file = st.file_uploader("2. Upload Template Target (XLSX)", type=['xlsx'])

    if source_file and template_file:
        if st.button("🚀 Proses & Update Template", type="primary"):
            try:
                # 1. Baca & Hitung
                df_input = pd.read_excel(source_file)
                with st.spinner("Menghitung logika HC & CL..."):
                    df_final = calculate_concentration_limit(df_input)
                
                # 2. Update Template
                with st.spinner("Menyuntikkan data ke file template..."):
                    template_file.seek(0)
                    processed_file = update_excel_template(template_file, df_final)
                
                st.success("✅ Berhasil! Data telah dihitung dan dipindahkan ke template.")
                
                # Preview Tabel
                st.subheader("Preview Hasil Perhitungan")
                st.dataframe(df_final[['KODE EFEK', COL_RMCC, 'HAIRCUT PEI USULAN DIVISI']].head(10))

                # Download
                st.download_button(
                    label="⬇️ Download Updated Excel",
                    data=processed_file,
                    file_name=f"Updated_Template_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"❌ Terjadi Kesalahan: {e}")
                st.exception(e)

if __name__ == '__main__':
    main()

