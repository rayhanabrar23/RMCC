import streamlit as st
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string
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
        nilai_override = OVERRIDE_MAPPING[kode]
        
        if nilai_rmcc == 0.0:
            return 0.0
            
        return min(nilai_rmcc, nilai_override)
        
    return nilai_rmcc

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
# FUNGSI UTAMA UNTUK PERHITUNGAN CL
# ===============================================================

def calculate_concentration_limit(df_cl_source: pd.DataFrame) -> pd.DataFrame:
    """Menjalankan seluruh logika perhitungan Concentration Limit."""
    
    df = df_cl_source.copy()
    
    if 'KODE EFEK' not in df.columns:
        df = df.rename(columns={df.columns[0]: 'KODE EFEK'})
        
    df['KODE EFEK'] = df['KODE EFEK'].astype(str).str.strip()
    
    # 1. Perhitungan limit marjin
    df['SAHAM MARJIN BARU?'] = df['SAHAM MARJIN BARU?'].astype(str).str.upper().str.strip()
    df['CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU'] = np.where(
        df['SAHAM MARJIN BARU?'] == 'YA',
        df[COL_PERHITUNGAN] * 0.50,
        df[COL_PERHITUNGAN]
    )

    # 2. Hitung limit listed & FF
    df[COL_LISTED] = df.apply(calc_concentration_limit_listed, axis=1)
    df[COL_FF] = df.apply(calc_concentration_limit_ff, axis=1)

    # 3. & 4. TENTUKAN CONCENTRATION LIMIT USULAN RMCC
    limit_cols_for_min = [
        'CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU', 
        COL_LISTED, COL_FF, COL_PERHITUNGAN
    ]

    df['MIN_CL_OPTION'] = df[limit_cols_for_min].fillna(np.inf).min(axis=1)
    
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

    # 5. Override emiten khusus (CAP)
    mask_not_zero = (df[COL_RMCC] != 0.0)
    df.loc[mask_not_zero, COL_RMCC] = df.loc[mask_not_zero].apply(override_rmcc_limit, axis=1).round(0)

    # 6. Tambah kolom haircut usulan 
    df['HAIRCUT KPEI'] = pd.to_numeric(df['HAIRCUT KPEI'], errors='coerce').fillna(0)
    df['HAIRCUT PEI USULAN DIVISI'] = np.where(
        (df['UMA'].fillna('-') != '-') & pd.notna(df['UMA']),
        df['HAIRCUT KPEI'],
        df['HAIRCUT PEI']
    )

    # 7. Nolkan CL USULAN RMCC jika haircut awal 100% atau CL perhitungan < 5M
    df['HAIRCUT PEI USULAN DIVISI'] = pd.to_numeric(df['HAIRCUT PEI USULAN DIVISI'], errors='coerce')
    df[COL_PERHITUNGAN] = pd.to_numeric(df[COL_PERHITUNGAN], errors='coerce')

    target_100_reset = 1.0 
    mask_haircut_100 = (df['HAIRCUT PEI USULAN DIVISI'].sub(target_100_reset).abs() < TOLERANCE)
    mask_below_threshold = (df[COL_PERHITUNGAN] < THRESHOLD_5M)
    mask_final_reset_cl = mask_haircut_100 | mask_below_threshold
    df.loc[mask_final_reset_cl, COL_RMCC] = 0.0
    
    # 7B. SET HAIRCUT JADI 100% KARENA CL=0
    HAIRCUT_COL_USULAN = 'HAIRCUT PEI USULAN DIVISI'
    mask_rmcc_nol = (df[COL_RMCC] == 0)
    df['TEMP_HAIRCUT_VAL_ASLI'] = pd.to_numeric(df[HAIRCUT_COL_USULAN], errors='coerce') 
    df.loc[mask_rmcc_nol, HAIRCUT_COL_USULAN] = 1.0 

    # 8. Keterangan Haircut & CONC LIMIT
    df['PERTIMBANGAN DIVISI (HAIRCUT)'] = df['UMA'].apply(keterangan_uma)
    df['PERTIMBANGAN DIVISI (CONC LIMIT)'] = 'Sesuai metode perhitungan' 

    # 9. & 10. PENERAPAN KETERANGAN (LOGIKA KOMPLEKS)
    mask_emiten = df['KODE EFEK'].isin(KODE_EFEK_KHUSUS)
    mask_nol_final = (df[COL_RMCC] == 0) & (~mask_emiten)
    
    mask_lt5m_strict = (
        (df['CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU'].fillna(np.inf) < THRESHOLD_5M) |
        (df[COL_PERHITUNGAN].fillna(np.inf) < THRESHOLD_5M) |
        (df[COL_LISTED].fillna(np.inf) < THRESHOLD_5M) |
        (df[COL_FF].fillna(np.inf) < THRESHOLD_5M) |
        (df[COL_RMCC].fillna(np.inf) < THRESHOLD_5M)
    ) & mask_nol_final 
                         
    mask_hc100_origin = ((df['TEMP_HAIRCUT_VAL_ASLI'].sub(1.0).abs() < TOLERANCE) |
                         (df['TEMP_HAIRCUT_VAL_ASLI'].sub(TARGET_100).abs() < TOLERANCE)) & \
                         mask_nol_final & \
                         (~mask_lt5m_strict)

    mask_non_nol = (df[COL_RMCC] != 0)
    df['CL_OVERRIDE_VAL'] = df['KODE EFEK'].map(OVERRIDE_MAPPING).fillna(np.inf)
    mask_emiten_override = mask_non_nol & mask_emiten & \
                           (df[COL_RMCC].round(0) == df['CL_OVERRIDE_VAL'].round(0))
    mask_other_non_nol = mask_non_nol & (~mask_emiten_override)
    mask_kriteria_listed = pd.notna(df[COL_LISTED])
    mask_kriteria_ff = pd.notna(df[COL_FF])
    
    mask_listed_saja = mask_other_non_nol & (df[COL_RMCC].round(0) == df[COL_LISTED].round(0))
    mask_ff_saja = mask_other_non_nol & (df[COL_RMCC].round(0) == df[COL_FF].round(0)) & (~mask_listed_saja)
    mask_marjin_baru = mask_other_non_nol & (df[COL_RMCC].round(0) == df['CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU'].round(0)) & (df['SAHAM MARJIN BARU?'] == 'YA') & (~mask_listed_saja) & (~mask_ff_saja)
    mask_listed_ff_upgrade = (mask_listed_saja | mask_ff_saja) & mask_kriteria_listed & mask_kriteria_ff
    
    # Penerapan Keterangan
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

    final_cols = [
        'KODE EFEK',
        'CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU', 
        'CONCENTRATION LIMIT TERKENA % LISTED SHARES', 
        'CONCENTRATION LIMIT TERKENA % FREE FLOAT', 
        'CONCENTRATION LIMIT USULAN RMCC', 
        'HAIRCUT PEI USULAN DIVISI', 
        'PERTIMBANGAN DIVISI (HAIRCUT)', 
        'PERTIMBANGAN DIVISI (CONC LIMIT)'
    ]
    
    # Filter dan pastikan semua kolom hasil ada
    for col in final_cols:
        if col not in df.columns:
            df[col] = None 

    return df[final_cols]


# ===============================================================
# FUNGSI UNTUK UPDATE EXCEL DENGAN OPENPYXL
# ===============================================================

def update_excel_template(file_template: BytesIO, df_cl_hasil: pd.DataFrame) -> BytesIO:
    """Mengupdate file template Excel menggunakan data hasil perhitungan, mencari KODE EFEK di Kolom C."""
    
    mapping_update = {
        # Sheet HC 
        'HAIRCUT PEI USULAN DIVISI': ('HC', 'R'), 
        'PERTIMBANGAN DIVISI (HAIRCUT)': ('HC', 'T'), 
        
        # Sheet CONC 
        'CONCENTRATION LIMIT KARENA SAHAM MARJIN BARU': ('CONC', 'P'), 
        'CONCENTRATION LIMIT TERKENA % LISTED SHARES': ('CONC', 'Q'), 
        'CONCENTRATION LIMIT TERKENA % FREE FLOAT': ('CONC', 'R'), 
        'CONCENTRATION LIMIT USULAN RMCC': ('CONC', 'S'), 
        'PERTIMBANGAN DIVISI (CONC LIMIT)': ('CONC', 'V'), 
    }
    
    wb = load_workbook(file_template)
    df_cl_hasil = df_cl_hasil.set_index('KODE EFEK')
    
    unmatched_codes = []
    
    for sheet_name in ['HC', 'CONC']:
        if sheet_name not in wb.sheetnames:
            st.warning(f"Sheet '{sheet_name}' tidak ditemukan di file template. Melanjutkan...")
            continue
            
        ws = wb[sheet_name]
        
        # PERUBAHAN KRITIS: Kolom KODE EFEK di C (Kolom ke-3)
        kode_efek_col_index = 3 
        start_row = 5 # Data dimulai dari baris 5 (setelah header di baris 4)
        
        for row_idx in range(start_row, ws.max_row + 1):
            # Ambil nilai dari Kolom C
            kode_efek_cell = ws.cell(row=row_idx, column=kode_efek_col_index).value
            
            if kode_efek_cell is not None:
                kode_efek = str(kode_efek_cell).strip()
            else:
                continue 

            if kode_efek in df_cl_hasil.index:
                # MATCH BERHASIL, LAKUKAN UPDATE
                data_hasil = df_cl_hasil.loc[kode_efek]
                
                for col_name, (target_sheet, target_col_letter) in mapping_update.items():
                    if target_sheet == sheet_name:
                        target_col_index = column_index_from_string(target_col_letter)
                        
                        try:
                            new_value = data_hasil[col_name]
                            
                            # Logika penulisan nilai
                            if col_name == 'HAIRCUT PEI USULAN DIVISI' and pd.notna(new_value):
                                ws.cell(row=row_idx, column=target_col_index).value = float(new_value)
                            elif pd.notna(new_value):
                                ws.cell(row=row_idx, column=target_col_index).value = new_value
                            else:
                                ws.cell(row=row_idx, column=target_col_index).value = None

                        except Exception as e:
                            print(f"Error writing {col_name} for {kode_efek}: {e}")
            else:
                # MATCH GAGAL, CATAT KODE EFEK YANG ADA DI TEMPLATE TAPI TIDAK DI HASIL
                unmatched_codes.append(f"{sheet_name}: {kode_efek} (Baris {row_idx})")

    # Laporkan hasil debugging di Streamlit
    if unmatched_codes:
        st.warning(f"⚠️ Perhatian: {len(unmatched_codes)} KODE EFEK di template tidak ditemukan di hasil perhitungan. Kemungkinan perbedaan format/spasi di Kolom C.")
        st.code('\n'.join(unmatched_codes[:20]) + ('\n...' if len(unmatched_codes) > 20 else ''))
        
    # Simpan Workbook ke buffer
    output_buffer = BytesIO()
    wb.save(output_buffer)
    output_buffer.seek(0)
    return output_buffer

# ============================
# ANTARMUKA STREAMLIT
# ============================

def main():
    st.set_page_config(page_title="HC CL Updater", layout="wide")
    st.title("🛡️ Concentration Limit (CL) & Haircut Calculation Updater")
    st.markdown("---")
    
    current_month_name = datetime.now().strftime('%B').lower()
    
    st.markdown("""
    **Instruksi:** Unggah kedua file di bawah ini. File **Template Output** Anda akan di-update pada Sheet `HC` dan `CONC` berdasarkan hasil perhitungan.
    """)

    col1, col2 = st.columns(2)

    with col1:
        uploaded_file_cl_source = st.file_uploader(
            "1. Unggah File Sumber Data CL (Input)",
            type=['xlsx'],
            key='cl_source'
        )

    with col2:
        uploaded_file_cl_template = st.file_uploader(
            "2. Unggah File Template Output (yang akan di-update)",
            type=['xlsx'],
            key='cl_template'
        )

    st.markdown("---")

    if uploaded_file_cl_source is not None and uploaded_file_cl_template is not None:
        if st.button("🚀 Jalankan Perhitungan & Update Template Excel", type="primary"):
            try:
                # 1. BACA FILE SUMBER
                df_cl_source = pd.read_excel(uploaded_file_cl_source, engine='openpyxl')
                
                # 2. JALANKAN PERHITUNGAN
                with st.spinner('Menghitung Concentration Limit dan Haircut...'):
                    df_cl_hasil = calculate_concentration_limit(df_cl_source)

                st.success("✅ Perhitungan Concentration Limit selesai.")
                st.caption("Preview Hasil Perhitungan CL/HC (5 Baris Pertama)")
                st.dataframe(df_cl_hasil.head())

                # 3. BACA FILE TEMPLATE DARI BUFFER DAN UPDATE
                uploaded_file_cl_template.seek(0) 
                
                with st.spinner('⏳ Mengupdate File Template Excel (Menggunakan openpyxl)...'):
                    output_buffer_template = update_excel_template(uploaded_file_cl_template, df_cl_hasil)
                
                st.success("🎉 File Template Output berhasil di-update tanpa merusak formula!")
                
                dynamic_filename_output = f'clhc_updated_{current_month_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx' 
                
                st.download_button(
                    label="⬇️ Unduh File Template Output yang Sudah Di-update",
                    data=output_buffer_template,
                    file_name=dynamic_filename_output, 
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                
            except Exception as e:
                st.error(f"❌ Gagal dalam proses. Pastikan file memiliki format, nama sheet (`HC`, `CONC`), dan kolom kunci (`KODE EFEK` di Kolom A) yang benar. Detail Error: {e}")
                st.exception(e)

    elif uploaded_file_cl_source is None and uploaded_file_cl_template is None:
        st.info("⬆️ Silakan unggah kedua file untuk memulai.")
    else:
        st.warning("⚠️ Harap unggah **kedua** file (Sumber Data dan Template Output).")

if __name__ == '__main__':
    main()
