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

# ===============================================================
# 2. KONFIGURASI GLOBAL (DEFAULT)
# ===============================================================
THRESHOLD_5M = 5_000_000_000
TARGET_100 = 100.0
TOLERANCE = 1e-6 
COL_RMCC = 'CONCENTRATION LIMIT USULAN RMCC'
COL_LISTED = 'CONCENTRATION LIMIT TERKENA % LISTED SHARES'
COL_FF = 'CONCENTRATION LIMIT TERKENA % FREE FLOAT'
COL_PERHITUNGAN = 'CONCENTRATION LIMIT SESUAI PERHITUNGAN'

# Inisialisasi Data Profil Emiten di Session State agar tidak hilang saat refresh
if "df_profil_emiten" not in st.session_state:
    st.session_state["df_profil_emiten"] = pd.DataFrame([
        {"KODE": "LPKR", "LIMIT": 10_000_000_000},
        {"KODE": "MLPL", "LIMIT": 10_000_000_000},
        {"KODE": "NOBU", "LIMIT": 10_000_000_000},
        {"KODE": "PTPP", "LIMIT": 50_000_000_000},
        {"KODE": "SILO", "LIMIT": 10_000_000_000}
    ])

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

def calculate_concentration_limit(df_cl_source, mapping_user):
    df = df_cl_source.copy()
    if 'KODE EFEK' not in df.columns: 
        df = df.rename(columns={df.columns[0]: 'KODE EFEK'})
    
    df['KODE EFEK'] = df['KODE EFEK'].astype(str).str.strip()
    kode_khusus_user = list(mapping_user.keys())

    # Logika Dasar
    df['SAHAM MARJIN BARU?'] = df['SAHAM MARJIN BARU?'].astype(str).str.upper().str.strip()
    df['CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU'] = np.where(df['SAHAM MARJIN BARU?'] == 'YA', df[COL_PERHITUNGAN] * 0.50, df[COL_PERHITUNGAN])
    df[COL_LISTED] = df.apply(calc_concentration_limit_listed, axis=1)
    df[COL_FF] = df.apply(calc_concentration_limit_ff, axis=1)

    limit_cols_for_min = ['CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU', COL_LISTED, COL_FF, COL_PERHITUNGAN]
    df['MIN_CL_OPTION'] = df[limit_cols_for_min].fillna(np.inf).min(axis=1)
    
    # Threshold 5M Global
    mask_pemicu_nol = (df[limit_cols_for_min].fillna(np.inf) < THRESHOLD_5M).any(axis=1)
    df[COL_RMCC] = np.where(mask_pemicu_nol, 0.0, df['MIN_CL_OPTION'])

    # --- LOGIKA OVERRIDE PROFIL EMITEN (DARI STREAMLIT) ---
    def apply_override(row):
        kode = row['KODE EFEK']
        nilai_rmcc = row[COL_RMCC]
        if kode in mapping_user:
            nilai_override = mapping_user[kode]
            if nilai_rmcc == 0.0: return 0.0
            return min(nilai_rmcc, nilai_override)
        return nilai_rmcc

    mask_not_zero = (df[COL_RMCC] != 0.0)
    df.loc[mask_not_zero, COL_RMCC] = df.loc[mask_not_zero].apply(apply_override, axis=1).round(0)

    # Haircut Logic
    df['HAIRCUT KPEI'] = pd.to_numeric(df['HAIRCUT KPEI'], errors='coerce').fillna(0)
    df['HAIRCUT PEI USULAN DIVISI'] = np.where((df['UMA'].fillna('-') != '-') & pd.notna(df['UMA']), df['HAIRCUT KPEI'], df['HAIRCUT PEI'])
    df = reset_concentration_limit(df)

    # Temporary column for labeling
    df['TEMP_HAIRCUT_VAL_ASLI'] = pd.to_numeric(df['HAIRCUT PEI USULAN DIVISI'], errors='coerce') 
    
    # --- LOGIKA MASKER PRIORITAS KETERANGAN ---
    mask_emiten = df['KODE EFEK'].isin(kode_khusus_user)
    mask_nol_final = (df[COL_RMCC] == 0) & (~mask_emiten)
    mask_lt5m_strict = (df[COL_RMCC] < THRESHOLD_5M) & mask_nol_final
    
    df['PERTIMBANGAN DIVISI (HAIRCUT)'] = df['UMA'].apply(keterangan_uma)
    df['PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Sesuai metode perhitungan'

    # Penerapan Label
    df.loc[mask_emiten, 'PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Penyesuaian karena profil emiten'
    df.loc[mask_lt5m_strict, 'PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Penyesuaian karena Batas Konsentrasi < Rp5 Miliar'
    
    return df

# ===============================================================
# 4. FUNGSI INJECTOR EXCEL
# ===============================================================
def update_excel_template(file_template, df_hasil):
    output = BytesIO()
    wb = load_workbook(file_template)
    ws_hc = wb["HC"]
    ws_conc = wb["CONC"]

    for i, row in enumerate(df_hasil.to_dict('records'), start=5):
        # Sheet HC
        ws_hc.cell(row=i, column=3, value=row.get('KODE EFEK'))
        ws_hc.cell(row=i, column=18, value=row.get('HAIRCUT PEI USULAN DIVISI'))
        ws_hc.cell(row=i, column=20, value=row.get('PERTIMBANGAN DIVISI (HAIRCUT)'))
        # Sheet CONC
        ws_conc.cell(row=i, column=3, value=row.get('KODE EFEK'))
        ws_conc.cell(row=i, column=19, value=row.get(COL_RMCC))
        ws_conc.cell(row=i, column=22, value=row.get('PERTIMBANGAN DIVISI (CONC LIMIT)'))

    wb.save(output)
    output.seek(0)
    return output

# ===============================================================
# 5. ANTARMUKA STREAMLIT
# ===============================================================
def main():
    st.title("🛡️ Laman Perhitungan Haircut dan Concentration Limit")
    
    # --- BAGIAN INPUT PROFIL EMITEN (DYNAMIC) ---
    st.markdown("### Konfigurasi Profil Emiten")
    st.info("Tambahkan kode saham dan nominal limit (misal: 10M = 10000000000). Gunakan tombol + di bawah tabel untuk menambah.")
    
    edited_profil = st.data_editor(
        st.session_state["df_profil_emiten"],
        num_rows="dynamic",
        column_config={
            "KODE": st.column_config.TextColumn("Kode Saham", help="Contoh: BBCA", required=True),
            "LIMIT": st.column_config.NumberColumn("Nominal Limit (IDR)", format="%d", min_value=0)
        },
        key="editor_profil"
    )
    
    # Konversi hasil editor ke dictionary mapping
    user_mapping = dict(zip(edited_profil['KODE'].str.strip().str.upper(), edited_profil['LIMIT']))

    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        source_file = st.file_uploader("1. Upload Raw Data (XLSX)", type=['xlsx'])
    with col2:
        template_file = st.file_uploader("2. Upload Template Target (XLSX)", type=['xlsx'])

    if source_file and template_file:
        if st.button("🚀 Proses & Update Template", type="primary"):
            try:
                df_input = pd.read_excel(source_file)
                
                with st.spinner("Menghitung dengan aturan Profil Emiten terbaru..."):
                    df_final = calculate_concentration_limit(df_input, user_mapping)
                    
                    template_file.seek(0)
                    processed_file = update_excel_template(template_file, df_final)
                
                st.success("✅ Berhasil diproses!")
                st.dataframe(df_final[['KODE EFEK', COL_RMCC, 'PERTIMBANGAN DIVISI (CONC LIMIT)']].head(15))

                st.download_button(
                    label="⬇️ Download Updated Excel",
                    data=processed_file,
                    file_name=f"Updated_Report_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"❌ Terjadi Kesalahan: {e}")

if __name__ == '__main__':
    main()

