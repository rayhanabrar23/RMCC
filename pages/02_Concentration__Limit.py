import streamlit as st
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment, Border, Side, NamedStyle, PatternFill
from openpyxl.utils import get_column_letter
from io import BytesIO
from datetime import datetime

# ============================
# KONFIGURASI GLOBAL CL
# ============================
COL_RMCC = 'CONCENTRATION LIMIT USULAN RMCC'
COL_LISTED = 'CONCENTRATION LIMIT TERKENA % LISTED SHARES'
COL_FF = 'CONCENTRATION LIMIT TERKENA % FREE FLOAT'
COL_PERHITUNGAN = 'CONCENTRATION LIMIT SESUAI PERHITUNGAN'
THRESHOLD_5M = 5_000_000_000
KODE_EFEK_KHUSUS = ['KPIG', 'LPKR', 'MLPL', 'NOBU', 'PTPP', 'SILO']
OVERRIDE_MAPPING = {
    'KPIG': 10_000_000_000, 'LPKR': 10_000_000_000, 'MLPL': 10_000_000_000,
    'NOBU': 10_000_000_000, 'PTPP': 50_000_000_000, 'SILO': 10_000_000_000
}

# Nilai dan toleransi untuk pengecekan 100%
TARGET_100 = 100.0
TOLERANCE = 1e-6 

# ===============================================================
# FUNGSI UTILITAS UNTUK CONCENTRATION LIMIT (CL)
# ===============================================================

def calc_concentration_limit_listed(row):
    try:
        if row['PERBANDINGAN DENGAN LISTED SHARES (Sesuai Perhitungan)'] >= 0.05:
            return 0.0499 * row['LISTED SHARES'] * row['CLOSING PRICE']
        return None
    except Exception:
        return None

def calc_concentration_limit_ff(row):
    try:
        if row['PERBANDINGAN DENGAN FREE FLOAT (Sesuai Perhitungan)'] >= 0.20:
            return 0.1999 * row['FREE FLOAT (DALAM LEMBAR)'] * row['CLOSING PRICE']
        return None
    except Exception:
        return None

def override_rmcc_limit(row):
    kode = row['KODE EFEK']
    nilai_rmcc = row[COL_RMCC]
    nilai_perhitungan = row[COL_PERHITUNGAN]

    if kode in OVERRIDE_MAPPING:
        nilai_override = OVERRIDE_MAPPING[kode]

        if pd.notna(nilai_rmcc) and pd.notna(nilai_perhitungan):
            if nilai_rmcc < nilai_perhitungan:
                return min(nilai_rmcc, nilai_override)
        return nilai_override
    return nilai_rmcc

def reset_concentration_limit(
    df_main: pd.DataFrame,
    haircut_col: str = "HAIRCUT PEI USULAN DIVISI",
    conc_limit_col: str = "CONCENTRATION LIMIT USULAN RMCC",
    conc_calc_col: str = "CONCENTRATION LIMIT SESUAI PERHITUNGAN",
    tolerance: float = 1e-6,
    threshold_limit: float = 5_000_000_000,
    inplace: bool = True
) -> pd.DataFrame:
    if not inplace:
        df_main = df_main.copy()
        
    if haircut_col not in df_main.columns:
        df_main[haircut_col] = 0.0
        
    df_main[haircut_col] = pd.to_numeric(df_main[haircut_col], errors='coerce')
    df_main[conc_calc_col] = pd.to_numeric(df_main[conc_calc_col], errors='coerce')

    valid_haircut = df_main[haircut_col].dropna()
    target_100_reset = 100.0 if not valid_haircut.empty and valid_haircut.max() > 1 + tolerance else 1.0

    mask_haircut_100 = (df_main[haircut_col].sub(target_100_reset).abs() < tolerance)
    mask_below_threshold = (df_main[conc_calc_col] < threshold_limit)
    mask_final = mask_haircut_100 | mask_below_threshold

    df_main.loc[mask_final, conc_limit_col] = 0.0
    return df_main

def keterangan_uma(uma_date):
    if pd.notna(uma_date):
        if not isinstance(uma_date, datetime):
            try:
                uma_date = pd.to_datetime(str(uma_date))
            except Exception:
                return "Sesuai Metode Perhitungan"
        return f"Sesuai Haircut KPEI, mempertimbangkan pengumuman UMA dari BEI tanggal {uma_date.strftime('%d %b %Y')}"
    return "Sesuai Metode Perhitungan"

def apply_conc_limit_keterangan_prioritas_final(row):
    terkena_listed = pd.notna(row.get(COL_LISTED))
    terkena_ff = pd.notna(row.get(COL_FF))

    if terkena_listed and terkena_ff:
        return 'Penyesuaian karena melebihi 5% listed & 20% free float'
    elif terkena_listed:
        return 'Penyesuaian karena melebihi 5% listed shares'
    elif terkena_ff:
        return 'Penyesuaian karena melebihi 20% free float'
    elif row.get('SAHAM MARJIN BARU?') == 'YA':
        return 'Penyesuaian karena saham baru masuk marjin'
    else:
        return 'Sesuai metode perhitungan'

# ===============================================================
# FUNGSI UTAMA UNTUK CONCENTRATION LIMIT (CL)
# ===============================================================

def calculate_concentration_limit(df_cl_source: pd.DataFrame) -> pd.DataFrame:
    """Menjalankan seluruh logika perhitungan Concentration Limit."""
    
    df = df_cl_source.copy()
    
    if 'KODE EFEK' not in df.columns:
        df = df.rename(columns={df.columns[0]: 'KODE EFEK'})
        
    df['KODE EFEK'] = df['KODE EFEK'].astype(str).str.strip()
    
    # 1. Perhitungan limit marjin (Tetap)
    df['CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU'] = np.where(
        df['SAHAM MARJIN BARU?'].str.upper().str.strip() == 'YA',
        df[COL_PERHITUNGAN] * 0.50,
        df[COL_PERHITUNGAN]
    )

    # 2. Hitung limit listed & FF (Tetap)
    df[COL_LISTED] = df.apply(calc_concentration_limit_listed, axis=1)
    df[COL_FF] = df.apply(calc_concentration_limit_ff, axis=1)

    # 3. & 4. TENTUKAN CONCENTRATION LIMIT USULAN RMCC
    limit_cols_for_min = [
        'CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU', 
        COL_LISTED, COL_FF, COL_PERHITUNGAN
    ]

    df['MIN_CL_OPTION'] = df[limit_cols_for_min].fillna(np.inf).min(axis=1)
    
    # Menambahkan CL KARENA SAHAM MARJIN BARU ke pemicu nol
    mask_pemicu_nol = (
        (df['CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU'].fillna(np.inf) < THRESHOLD_5M) |
        (df[COL_PERHITUNGAN].fillna(np.inf) < THRESHOLD_5M) |
        (df[COL_LISTED].fillna(np.inf) < THRESHOLD_5M) |
        (df[COL_FF].fillna(np.inf) < THRESHOLD_5M)
    )

    df[COL_RMCC] = np.where(
        mask_pemicu_nol,
        0.0, 
        df['MIN_CL_OPTION']
    )

    # 5. Override emiten khusus (Tetap)
    mask_not_zero = (df[COL_RMCC] != 0.0)
    df.loc[mask_not_zero, COL_RMCC] = df.loc[mask_not_zero].apply(override_rmcc_limit, axis=1).round(0)

    # 6. Tambah kolom haircut usulan
    df['HAIRCUT KPEI'] = pd.to_numeric(df['HAIRCUT KPEI'], errors='coerce').fillna(0)
    
    # Prioritaskan HAIRCUT KPEI 100%
    mask_hc_kpei_100 = (df['HAIRCUT KPEI'].sub(TARGET_100).abs() < TOLERANCE) | \
                       (df['HAIRCUT KPEI'].sub(1.0).abs() < TOLERANCE)
                       
    df['HAIRCUT PEI USULAN DIVISI'] = np.where(
        mask_hc_kpei_100, # Prioritas 1: Jika KPEI 100%
        df['HAIRCUT KPEI'], 
        np.where(
            (df['UMA'].fillna('-') != '-') & pd.notna(df['UMA']), # Prioritas 2: Jika ada UMA, pakai KPEI
            df['HAIRCUT KPEI'],
            df['HAIRCUT PEI'] # Prioritas 3: Pakai PEI biasa
        )
    )

    # 7. Nolkan CL USULAN RMCC jika haircut awal 100% atau CL perhitungan < 5M
    # PENTING: Pada titik ini, df['HAIRCUT PEI USULAN DIVISI'] memegang nilai ASLI sebelum dipaksa 100%
    df = reset_concentration_limit(df)

    # 7B. SET HAIRCUT JADI 100% KARENA CL=0
    HAIRCUT_COL_USULAN = 'HAIRCUT PEI USULAN DIVISI'
    mask_rmcc_nol = (df[COL_RMCC] == 0)
    
    # Simpan nilai ASLI Haircut Usulan sebelum ditimpa
    df['TEMP_HAIRCUT_VAL_ASLI'] = pd.to_numeric(df[HAIRCUT_COL_USULAN], errors='coerce') 
    
    # PENTING: Haircut Usulan DITIMPA menjadi 1.0 (100%) karena CL=0
    df.loc[mask_rmcc_nol, HAIRCUT_COL_USULAN] = 1.0 

    # 8. Keterangan Haircut & Concentration Limit (Tetap)
    df['PERTIMBANGAN DIVISI (HAIRCUT)'] = df['UMA'].apply(keterangan_uma)
    df['PERTIMBANGAN DIVISI (CONC LIMIT)'] = df.apply(apply_conc_limit_keterangan_prioritas_final, axis=1)

    # 9. Prioritas khusus: pemisahan keterangan CL=0
    mask_emiten = df['KODE EFEK'].isin(KODE_EFEK_KHUSUS)
    mask_nol_final = (df[COL_RMCC] == 0) & (~mask_emiten)
    
    # 1. Tentukan masker CL < 5M (Prioritas TERTINGGI untuk CL=0)
    mask_lt5m_strict = (
        (df['CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU'].fillna(np.inf) < THRESHOLD_5M) |
        (df[COL_PERHITUNGAN].fillna(np.inf) < THRESHOLD_5M) |
        (df[COL_LISTED].fillna(np.inf) < THRESHOLD_5M) |
        (df[COL_FF].fillna(np.inf) < THRESHOLD_5M) |
        (df[COL_RMCC].fillna(np.inf) < THRESHOLD_5M)
    ) & mask_nol_final
    
    # 2. Tentukan masker Haircut 100% ASLI (Berlaku hanya jika nilai ASLI sebelum forced 100% adalah 100%)
    mask_hc100_origin = ((df['TEMP_HAIRCUT_VAL_ASLI'].sub(1.0).abs() < TOLERANCE) |
                         (df['TEMP_HAIRCUT_VAL_ASLI'].sub(TARGET_100).abs() < TOLERANCE)) & \
                        mask_nol_final & \
                        (~mask_lt5m_strict) # Dikecualikan jika sudah kena pemicu < 5M

    
    # --- Penerapan Keterangan (Order: CL < 5M Dulu, Baru HC 100% ASLI) ---
    
    # A. Keterangan CL < 5M (Prioritas Tertinggi)
    df.loc[mask_lt5m_strict, 'PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Penyesuaian karena Batas Konsentrasi < Rp5 Miliar'
    df.loc[mask_lt5m_strict, 'PERTIMBANGAN DIVISI (HAIRCUT)'] = 'Penyesuaian karena Batas Konsentrasi 0'
    
    # B. Keterangan Haircut 100% ASLI (Prioritas Kedua)
    df.loc[mask_hc100_origin, 'PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Penyesuaian karena Haircut PEI 100%'
    
    # C. Keterangan Emiten Khusus
    df.loc[mask_emiten, 'PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Penyesuaian karena profil emiten'

    df = df.drop(columns=['MIN_CL_OPTION', 'TEMP_HAIRCUT_VAL_ASLI'], errors='ignore')

    return df

# ============================
# ANTARMUKA CL
# ============================

def main():
    st.title("🛡️ Concentration Limit (CL) & Haircut Calculation")
    
    # --- Membuat Nama File Contoh Dinamis (Input) ---
    current_month_name = datetime.now().strftime('%B').lower()
    example_filename = f'Pythonab_{current_month_name}.xlsx'
    
    st.markdown(f"Unggah file sumber data Concentration Limit (misal: `{example_filename}` atau sejenisnya) untuk menjalankan perhitungan CL.")
    
    required_file_cl = f'File Sumber Concentration Limit (misal: {example_filename})'
    # ---------------------------------------
    
    uploaded_file_cl = st.file_uploader(f"Unggah {required_file_cl}", type=['xlsx'], key='cl_source')
    
    if uploaded_file_cl is not None:
        if st.button("Jalankan Perhitungan CL", type="primary"):
            try:
                # Membaca file
                df_cl_source = pd.read_excel(uploaded_file_cl, engine='openpyxl')
                
                with st.spinner('Menghitung Concentration Limit...'):
                    # Panggil fungsi CL
                    df_cl_hasil = calculate_concentration_limit(df_cl_source)
                
                st.success("✅ Perhitungan Concentration Limit selesai. Siap diunduh!")
                st.subheader("Hasil Concentration Limit (Tabel)")
                st.dataframe(df_cl_hasil) 
                
                # Sediakan tombol download CL
                output_buffer_cl = BytesIO()
                df_cl_hasil.to_excel(output_buffer_cl, index=False)
                output_buffer_cl.seek(0)
                
                # --- Nama File Output Dinamis ---
                month_name_lower_output = datetime.now().strftime('%B').lower()
                dynamic_filename_output = f'clhc_{month_name_lower_output}.xlsx' 
                
                st.download_button(
                    label="⬇️ Unduh Hasil Concentration Limit",
                    data=output_buffer_cl,
                    file_name=dynamic_filename_output, 
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )

            except Exception as e:
                st.error(f"❌ Gagal dalam perhitungan CL. Pastikan format file benar. Error: {e}")

if __name__ == '__main__':
    main()
