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

if "df_profil_emiten" not in st.session_state:
    st.session_state["df_profil_emiten"] = pd.DataFrame([
        {"KODE": "LPKR", "LIMIT": 10_000_000_000},
        {"KODE": "MLPL", "LIMIT": 10_000_000_000},
        {"KODE": "NOBU", "LIMIT": 10_000_000_000},
        {"KODE": "PTPP", "LIMIT": 50_000_000_000},
        {"KODE": "SILO", "LIMIT": 10_000_000_000}
    ])

# ===============================================================
# 3. FUNGSI LOGIKA PERHITUNGAN (REVISED)
# ===============================================================

def calc_concentration_limit_listed(row):
    try:
        val_perbandingan = float(row.get('PERBANDINGAN DENGAN LISTED SHARES (SESUAI PERHITUNGAN)', 0))
        if val_perbandingan >= 0.05:
            return 0.0499 * float(row['LISTED SHARES']) * float(row['CLOSING PRICE'])
        return None
    except Exception: return None

def calc_concentration_limit_ff(row):
    try:
        val_ff_ratio = float(row.get('PERBANDINGAN DENGAN FREE FLOAT (SESUAI PERHITUNGAN)', 0))
        if val_ff_ratio >= 0.20:
            return 0.1999 * float(row['FREE FLOAT (DALAM LEMBAR)']) * float(row['CLOSING PRICE'])
        return None
    except Exception: return None

def reset_concentration_limit(df_main, haircut_col="HAIRCUT PEI USULAN DIVISI", conc_limit_col=COL_RMCC, conc_calc_col=COL_PERHITUNGAN):
    """
    Fungsi ini memastikan jika Haircut >= 100% atau Perhitungan < 5M, 
    maka Concentration Limit RMCC dipaksa menjadi 0.
    """
    df = df_main.copy()
    
    # Konversi ke numerik untuk keamanan kalkulasi
    df[haircut_col] = pd.to_numeric(df[haircut_col], errors='coerce').fillna(0)
    df[conc_calc_col] = pd.to_numeric(df[conc_calc_col], errors='coerce').fillna(0)
    
    # Cek apakah data menggunakan skala 0-1 atau 0-100
    is_decimal_scale = df[haircut_col].max() <= 1.1 
    target_val = 1.0 if is_decimal_scale else 100.0

    mask_haircut_100 = (df[haircut_col] >= target_val - TOLERANCE)
    mask_below_threshold = (df[conc_calc_col] < THRESHOLD_5M)
    
    df.loc[mask_haircut_100 | mask_below_threshold, conc_limit_col] = 0.0
    return df

def keterangan_uma(uma_date):
    if pd.notna(uma_date) and str(uma_date).strip() not in ["", "-", "0"]:
        if not isinstance(uma_date, datetime):
            try: 
                uma_date = pd.to_datetime(str(uma_date))
            except Exception: 
                return "Sesuai Haircut KPEI (UMA)"
        return f"Sesuai Haircut KPEI, mempertimbangkan pengumuman UMA dari BEI tanggal {uma_date.strftime('%d %b %Y')}"
    return "Sesuai Metode Perhitungan"

def calculate_concentration_limit(df_cl_source, mapping_user):
    df = df_cl_source.copy()
    
    # 1. Normalisasi Nama Kolom (Uppercase & Trim)
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    if 'KODE EFEK' not in df.columns: 
        df = df.rename(columns={df.columns[0]: 'KODE EFEK'})
    
    df['KODE EFEK'] = df['KODE EFEK'].astype(str).str.strip().str.upper()
    df = df.dropna(subset=['KODE EFEK']) # Hapus baris kosong di bawah

    # 2. Logika Dasar (Marjin Baru)
    df['SAHAM MARJIN BARU?'] = df.get('SAHAM MARJIN BARU?', 'TIDAK').astype(str).str.upper().str.strip()
    df['CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU'] = np.where(
        df['SAHAM MARJIN BARU?'] == 'YA', 
        df[COL_PERHITUNGAN] * 0.50, 
        df[COL_PERHITUNGAN]
    )

    # 3. Hitung Limit Listed & Free Float
    df[COL_LISTED] = df.apply(calc_concentration_limit_listed, axis=1)
    df[COL_FF] = df.apply(calc_concentration_limit_ff, axis=1)

    # 4. Ambil Nilai Terendah (Min)
    limit_cols_for_min = ['CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU', COL_LISTED, COL_FF, COL_PERHITUNGAN]
    df['MIN_CL_OPTION'] = df[limit_cols_for_min].fillna(np.inf).min(axis=1)
    
    # 5. Threshold 5M Global
    mask_pemicu_nol = (df['MIN_CL_OPTION'] < THRESHOLD_5M)
    df[COL_RMCC] = np.where(mask_pemicu_nol, 0.0, df['MIN_CL_OPTION'])

    # 6. Override Profil Emiten (User Mapping)
    def apply_override(row):
        kode = row['KODE EFEK']
        nilai_rmcc = row[COL_RMCC]
        if kode in mapping_user:
            nilai_override = mapping_user[kode]
            if nilai_rmcc == 0.0: return 0.0 # Jika sudah 0 (karena 5M/HC 100), jangan dinaikkan lagi
            return min(float(nilai_rmcc), float(nilai_override))
        return nilai_rmcc

    df[COL_RMCC] = df.apply(apply_override, axis=1).round(0)

    # 7. Logika Haircut (UMA)
    # Gunakan KPEI jika ada UMA, jika tidak gunakan PEI asli
    df['HAIRCUT PEI USULAN DIVISI'] = np.where(
        (df['UMA'].astype(str) != '-') & (df['UMA'].notna()) & (df['UMA'].astype(str) != '0'), 
        df['HAIRCUT KPEI'], 
        df['HAIRCUT PEI']
    )

    # 8. Final Reset (Haircut 100% & < 5M)
    df = reset_concentration_limit(df)

    # 9. Keterangan Labeling
    df['PERTIMBANGAN DIVISI (HAIRCUT)'] = df['UMA'].apply(keterangan_uma)
    df['PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Sesuai metode perhitungan'

    mask_emiten = df['KODE EFEK'].isin(mapping_user.keys())
    mask_nol_final = (df[COL_RMCC] == 0) & (~mask_emiten)
    
    df.loc[mask_emiten, 'PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Penyesuaian karena profil emiten'
    df.loc[mask_nol_final, 'PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Penyesuaian karena Batas Konsentrasi < Rp5 Miliar atau Haircut 100%'
    
    return df

# ===============================================================
# 4. FUNGSI INJECTOR EXCEL
# ===============================================================
def update_excel_template(file_template, df_hasil):
    output = BytesIO()
    wb = load_workbook(file_template)
    
    # Validasi Nama Sheet
    if "HC" not in wb.sheetnames or "CONC" not in wb.sheetnames:
        raise ValueError("Sheet 'HC' atau 'CONC' tidak ditemukan di file template!")

    ws_hc = wb["HC"]
    ws_conc = wb["CONC"]

    # Mapping hasil ke Excel (Baris dimulai dari 5)
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
    st.title("📊 Laman Perhitungan Haircut & Concentration Limit")
    
    st.markdown("### 1. Konfigurasi Profil Emiten")
    with st.expander("Klik untuk atur limit khusus per kode saham", expanded=True):
        edited_profil = st.data_editor(
            st.session_state["df_profil_emiten"],
            num_rows="dynamic",
            column_config={
                "KODE": st.column_config.TextColumn("Kode Saham", help="Contoh: BBCA", required=True),
                "LIMIT": st.column_config.NumberColumn("Nominal Limit (IDR)", format="%d", min_value=0)
            },
            key="editor_profil"
        )
        # Update session state agar data tersimpan
        st.session_state["df_profil_emiten"] = edited_profil
        user_mapping = dict(zip(edited_profil['KODE'].str.strip().str.upper(), edited_profil['LIMIT']))

    st.markdown("---")
    
    st.markdown("### 2. Upload & Proses Data")
    col1, col2 = st.columns(2)
    with col1:
        source_file = st.file_uploader("Upload Raw Data (XLSX)", type=['xlsx'], help="File Excel hasil export sistem")
    with col2:
        template_file = st.file_uploader("Upload Template Target (XLSX)", type=['xlsx'], help="Template laporan resmi")

    if source_file and template_file:
        if st.button("🚀 Jalankan Proses Kalkulasi", type="primary"):
            try:
                # Membaca data
                df_input = pd.read_excel(source_file)
                
                with st.spinner("Sedang menghitung..."):
                    # Proses Kalkulasi
                    df_final = calculate_concentration_limit(df_input, user_mapping)
                    
                    # Update ke Template Excel
                    template_file.seek(0)
                    processed_file = update_excel_template(template_file, df_final)
                
                st.success("✅ Selesai! Silakan cek hasil di bawah dan download file.")
                
                # Tampilkan Preview Ringkas
                preview_cols = ['KODE EFEK', 'HAIRCUT PEI USULAN DIVISI', COL_RMCC, 'PERTIMBANGAN DIVISI (CONC LIMIT)']
                st.dataframe(df_final[preview_cols].head(20), use_container_width=True)

                st.download_button(
                    label="⬇️ Download Updated Excel",
                    data=processed_file,
                    file_name=f"Report_Final_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"❌ Terjadi kesalahan teknis: {e}")
                st.info("Pastikan nama kolom di file sumber sudah benar (KODE EFEK, UMA, HAIRCUT KPEI, dll)")

if __name__ == '__main__':
    main()
