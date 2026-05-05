import streamlit as st

# Cek apakah sudah login dari halaman utama
if "login_status" not in st.session_state or not st.session_state["login_status"]:
    st.error("🚨 Akses Ditolak! Silakan login di halaman utama terlebih dahulu.")
    st.stop()

from style_utils import apply_custom_style
apply_custom_style()

import pandas as pd
import numpy as np
from openpyxl import load_workbook
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
KODE_EFEK_KHUSUS = ['LPKR', 'MLPL', 'NOBU', 'PTPP', 'SILO']
OVERRIDE_MAPPING = {
    'LPKR': 10_000_000_000, 'MLPL': 10_000_000_000,
    'NOBU': 10_000_000_000, 'PTPP': 50_000_000_000, 'SILO': 10_000_000_000
}
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
    if kode in OVERRIDE_MAPPING:
        if nilai_rmcc == 0.0:
            return 0.0
        return min(nilai_rmcc, OVERRIDE_MAPPING[kode])
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

# ===============================================================
# FUNGSI UTAMA PERHITUNGAN CONCENTRATION LIMIT
# ===============================================================

def calculate_concentration_limit(df_cl_source: pd.DataFrame) -> pd.DataFrame:
    df = df_cl_source.copy()

    if 'KODE EFEK' not in df.columns:
        df = df.rename(columns={df.columns[0]: 'KODE EFEK'})

    df['KODE EFEK'] = df['KODE EFEK'].astype(str).str.strip()

    # 1. Limit marjin baru
    df['SAHAM MARJIN BARU?'] = df['SAHAM MARJIN BARU?'].astype(str).str.upper().str.strip()
    df['CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU'] = np.where(
        df['SAHAM MARJIN BARU?'] == 'YA',
        df[COL_PERHITUNGAN] * 0.50,
        df[COL_PERHITUNGAN]
    )

    # 2. Hitung limit listed & FF
    df[COL_LISTED] = df.apply(calc_concentration_limit_listed, axis=1)
    df[COL_FF] = df.apply(calc_concentration_limit_ff, axis=1)

    # 3. Ambil nilai minimum
    limit_cols_for_min = [
        'CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU',
        COL_LISTED, COL_FF, COL_PERHITUNGAN
    ]
    df['MIN_CL_OPTION'] = df[limit_cols_for_min].fillna(np.inf).min(axis=1)

    # 4. Tentukan pemicu nol
    mask_pemicu_nol = (
        (df['CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU'].fillna(np.inf) < THRESHOLD_5M) |
        (df[COL_PERHITUNGAN].fillna(np.inf) < THRESHOLD_5M) |
        (df[COL_LISTED].fillna(np.inf) < THRESHOLD_5M) |
        (df[COL_FF].fillna(np.inf) < THRESHOLD_5M)
    )

    df[COL_RMCC] = np.where(mask_pemicu_nol, 0.0, df['MIN_CL_OPTION'])

    # 5. Override emiten khusus (CAP 10M/50M)
    mask_not_zero = (df[COL_RMCC] != 0.0)
    df.loc[mask_not_zero, COL_RMCC] = df.loc[mask_not_zero].apply(override_rmcc_limit, axis=1).round(0)

    # 6. Haircut usulan divisi
    df['HAIRCUT KPEI'] = pd.to_numeric(df['HAIRCUT KPEI'], errors='coerce').fillna(0)
    df['HAIRCUT PEI USULAN DIVISI'] = np.where(
        (df['UMA'].fillna('-') != '-') & pd.notna(df['UMA']),
        df['HAIRCUT KPEI'],
        df['HAIRCUT PEI']
    )

    # 7. Nolkan CL jika haircut 100% atau CL perhitungan < 5M
    df = reset_concentration_limit(df)

    # 7B. Set haircut jadi 100% jika CL = 0
    HAIRCUT_COL_USULAN = 'HAIRCUT PEI USULAN DIVISI'
    mask_rmcc_nol = (df[COL_RMCC] == 0)
    df['TEMP_HAIRCUT_VAL_ASLI'] = pd.to_numeric(df[HAIRCUT_COL_USULAN], errors='coerce')
    df.loc[mask_rmcc_nol, HAIRCUT_COL_USULAN] = 1.0

    # 8. Keterangan awal
    df['PERTIMBANGAN DIVISI (HAIRCUT)'] = df['UMA'].apply(keterangan_uma)
    df['PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Sesuai metode perhitungan'

    # 9. Definisikan masker untuk keterangan
    mask_emiten = df['KODE EFEK'].isin(KODE_EFEK_KHUSUS)
    mask_nol_final = (df[COL_RMCC] == 0) & (~mask_emiten)

    mask_lt5m_strict = (
        (df['CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU'].fillna(np.inf) < THRESHOLD_5M) |
        (df[COL_PERHITUNGAN].fillna(np.inf) < THRESHOLD_5M) |
        (df[COL_LISTED].fillna(np.inf) < THRESHOLD_5M) |
        (df[COL_FF].fillna(np.inf) < THRESHOLD_5M) |
        (df[COL_RMCC].fillna(np.inf) < THRESHOLD_5M)
    ) & mask_nol_final

    mask_hc100_origin = (
        (df['TEMP_HAIRCUT_VAL_ASLI'].sub(1.0).abs() < TOLERANCE) |
        (df['TEMP_HAIRCUT_VAL_ASLI'].sub(TARGET_100).abs() < TOLERANCE)
    ) & mask_nol_final & (~mask_lt5m_strict)

    mask_non_nol = (df[COL_RMCC] != 0)
    df['CL_OVERRIDE_VAL'] = df['KODE EFEK'].map(OVERRIDE_MAPPING).fillna(np.inf)
    mask_emiten_override = mask_non_nol & mask_emiten & \
                           (df[COL_RMCC].round(0) == df['CL_OVERRIDE_VAL'].round(0))
    mask_other_non_nol = mask_non_nol & (~mask_emiten_override)

    mask_kriteria_listed = pd.notna(df[COL_LISTED])
    mask_kriteria_ff = pd.notna(df[COL_FF])

    mask_listed_saja = mask_other_non_nol & \
                       (df[COL_RMCC].round(0) == df[COL_LISTED].round(0))

    mask_ff_saja = mask_other_non_nol & \
                   (df[COL_RMCC].round(0) == df[COL_FF].round(0)) & \
                   (~mask_listed_saja)

    mask_marjin_baru = mask_other_non_nol & \
                       (df[COL_RMCC].round(0) == df['CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU'].round(0)) & \
                       (df['SAHAM MARJIN BARU?'] == 'YA') & \
                       (~mask_listed_saja) & (~mask_ff_saja)

    mask_listed_ff_upgrade = (mask_listed_saja | mask_ff_saja) & \
                              mask_kriteria_listed & mask_kriteria_ff

    # 10. Penerapan keterangan (prioritas rendah ke tinggi)
    df.loc[mask_lt5m_strict, 'PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Penyesuaian karena Batas Konsentrasi < Rp5 Miliar'
    df.loc[mask_lt5m_strict, 'PERTIMBANGAN DIVISI (HAIRCUT)'] = 'Penyesuaian karena Batas Konsentrasi 0'
    df.loc[mask_hc100_origin, 'PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Penyesuaian karena Haircut PEI 100%'
    df.loc[mask_emiten & mask_nol_final, 'PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Penyesuaian karena profil emiten'
    df.loc[mask_emiten_override, 'PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Penyesuaian karena profil emiten'
    df.loc[mask_marjin_baru, 'PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Penyesuaian karena saham baru masuk marjin'
    df.loc[mask_listed_saja, 'PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Penyesuaian karena melebihi 5% listed shares'
    df.loc[mask_ff_saja, 'PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Penyesuaian karena melebihi 20% free float'
    df.loc[mask_listed_ff_upgrade, 'PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Penyesuaian karena melebihi 5% listed & 20% free float'

    # Cleanup kolom bantuan
    df = df.drop(columns=['MIN_CL_OPTION', 'TEMP_HAIRCUT_VAL_ASLI', 'CL_OVERRIDE_VAL'], errors='ignore')

    return df

# ===============================================================
# FUNGSI INJECTOR KE TEMPLATE EXCEL (dari Code 1, disesuaikan)
# ===============================================================

def update_excel_template(file_template, df_hasil):
    """
    Menyuntikkan hasil perhitungan ke template Excel.
    Sheet CONC  : Kolom C (Kode Efek), P (CL Marjin Baru), Q (CL Listed),
                  R (CL FF), S (CL RMCC), V (Pertimbangan CL)
    Sheet HC    : Kolom C (Kode Efek), R (Haircut Usulan Divisi)
    Data mulai baris ke-5.
    """
    output = BytesIO()
    wb = load_workbook(file_template)
    ws_conc = wb["CONC"]
    ws_hc = wb["HC"]

    for i, row in enumerate(df_hasil.to_dict('records'), start=5):
        # --- SHEET CONC ---
        ws_conc.cell(row=i, column=3,  value=row.get('KODE EFEK'))
        ws_conc.cell(row=i, column=16, value=row.get('CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU'))  # Col P
        ws_conc.cell(row=i, column=17, value=row.get(COL_LISTED))                                      # Col Q
        ws_conc.cell(row=i, column=18, value=row.get(COL_FF))                                          # Col R
        ws_conc.cell(row=i, column=19, value=row.get(COL_RMCC))                                        # Col S
        ws_conc.cell(row=i, column=22, value=row.get('PERTIMBANGAN DIVISI (CONC LIMIT)'))              # Col V

        # --- SHEET HC ---
        ws_hc.cell(row=i, column=3,  value=row.get('KODE EFEK'))
        ws_hc.cell(row=i, column=18, value=row.get('HAIRCUT PEI USULAN DIVISI'))                       # Col R

    wb.save(output)
    output.seek(0)
    return output

# ============================
# ANTARMUKA STREAMLIT
# ============================

def main():
    st.title("🛡️ Concentration Limit (CL) & Haircut Calculation")

    current_month_name = datetime.now().strftime('%B').lower()
    example_filename = f'HCCL_{current_month_name}.xlsx'

    st.markdown(f"Unggah file sumber data dan template target untuk menjalankan perhitungan CL & Haircut.")

    col1, col2 = st.columns(2)
    with col1:
        uploaded_file_cl = st.file_uploader(
            f"📂 Unggah File Sumber (misal: `{example_filename}`)",
            type=['xlsx'], key='cl_source'
        )
    with col2:
        uploaded_template = st.file_uploader(
            "📋 Unggah Template Target (XLSX)",
            type=['xlsx'], key='cl_template'
        )

    if uploaded_file_cl is not None:
        if st.button("🚀 Jalankan Perhitungan CL", type="primary"):
            try:
                df_cl_source = pd.read_excel(uploaded_file_cl, engine='openpyxl')

                with st.spinner('Menghitung Concentration Limit...'):
                    df_cl_hasil = calculate_concentration_limit(df_cl_source)

                st.success("✅ Perhitungan Concentration Limit selesai!")
                st.subheader("Hasil Concentration Limit (Tabel)")
                st.dataframe(df_cl_hasil)

                month_name_lower_output = datetime.now().strftime('%B').lower()

                # --- Opsi 1: Download hasil sebagai file Excel biasa ---
                output_buffer_cl = BytesIO()
                df_cl_hasil.to_excel(output_buffer_cl, index=False)
                output_buffer_cl.seek(0)

                st.download_button(
                    label="⬇️ Unduh Hasil (Excel Biasa)",
                    data=output_buffer_cl,
                    file_name=f'clhc_{month_name_lower_output}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )

                # --- Opsi 2: Inject ke template (jika template diunggah) ---
                if uploaded_template is not None:
                    uploaded_template.seek(0)
                    final_xlsx = update_excel_template(uploaded_template, df_cl_hasil)

                    st.download_button(
                        label="⬇️ Unduh Hasil (Injected ke Template)",
                        data=final_xlsx,
                        file_name=f'Hasil_Template_{month_name_lower_output}.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                else:
                    st.info("💡 Upload Template Target di atas untuk menghasilkan file yang sudah ter-inject ke template.")

            except Exception as e:
                st.error(f"❌ Gagal dalam perhitungan CL. Pastikan format file benar. Error: {e}")

if __name__ == '__main__':
    main()
