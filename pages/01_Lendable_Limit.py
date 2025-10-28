# pages/01_Lendable_Limit.py (Halaman LL)

import streamlit as st
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment, Border, Side, NamedStyle, numbers
from io import BytesIO
from datetime import datetime
import os
import sys

# ============================
# KONFIGURASI GLOBAL LL
# ============================
STOCK_CODE_BLACKLIST = ['BEBS', 'IPPE', 'WMPP', 'WMUU']
SHEET_INST_OLD = 'Instrument'
SHEET_INST_NEW = 'Hasil Pivot'
FIRST_LARGERST_COL = "First Largerst"
SECOND_LARGERST_COL = "Second Largerst"
SHEET_RESULT_NAME_SOURCE = 'Lendable Limit Result'
BORROW_AMOUNT_COL = 'Borrow Amount (shares)'

FINAL_COLUMNS_LL = [
    'Stock Code', 'Stock Name', 'Quantity On Hand',
    FIRST_LARGERST_COL, SECOND_LARGERST_COL, 'Total two Largerst',
    'Quantity Available', 'Thirty Percent On Hand', 'REPO',
    'Lendable Limit', 'Borrow Position', 'Available Lendable Limit'
]

# ============================
# FUNGSI PEMROSESAN LL
# ============================

def process_lendable_limit(uploaded_files, template_file_data):
    """Fungsi utama untuk memproses data LL."""
    st.info("🚀 Mulai Pemrosesan Lendable Limit...")
    
    try:
        # Baca File LL
        df_sp = pd.read_excel(uploaded_files['Stock Position Detail.xlsx'], header=0, engine='openpyxl')
        df_instr_raw = pd.read_excel(uploaded_files['Instrument.xlsx'], sheet_name=SHEET_INST_OLD, header=1, engine='openpyxl')
        df_instr_old_raw = pd.read_excel(uploaded_files['Instrument.xlsx'], sheet_name=SHEET_INST_OLD, header=None, engine='openpyxl')
        df_borr_pos = pd.read_excel(uploaded_files['BorrPosition.xlsx'], header=0, engine='openpyxl')
    except Exception as e:
        st.error(f"❌ Gagal membaca salah satu file input LL. Error: {e}")
        return None, None, None # <-- PERUBAHAN: Tambah None

    output_xlsx_buffer = BytesIO()
    
    # --- BAGIAN 1 & 2: Pemrosesan LL Awal ---
    with st.spinner('1/3 - Memproses Stock Position dan Instrument...'):
        try:
            # 1. Stock Position (Largest)
            df_sp.columns = df_sp.columns.str.strip()
            stock_col = df_sp.columns[1]
            qty_col = df_sp.columns[10]
            df_sp[qty_col] = pd.to_numeric(df_sp[qty_col], errors='coerce').fillna(0)

            top_values = (
                df_sp.groupby(stock_col)[qty_col]
                .apply(lambda x: sorted(x.dropna(), reverse=True)[:2])
                .reset_index()
            )
            top_values[FIRST_LARGERST_COL] = top_values[qty_col].apply(lambda x: x[0] if len(x) > 0 else 0)
            top_values[SECOND_LARGERST_COL] = top_values[qty_col].apply(lambda x: x[1] if len(x) > 1 else 0)
            df_sp = df_sp.merge(top_values.drop(columns=[qty_col]), how="left", left_on=stock_col, right_on=stock_col).fillna({FIRST_LARGERST_COL: 0, SECOND_LARGERST_COL: 0})

            # 2. Instrument Pivot
            df_instr = df_instr_raw.copy()
            df_instr.columns = df_instr.columns.str.strip()
            col_row = "Local Code"
            col_loan = "Used Loan Qty"
            col_repo = "Used Reverse Repo Qty"
            df_instr[col_loan] = pd.to_numeric(df_instr[col_loan], errors='coerce').fillna(0)
            df_instr[col_repo] = pd.to_numeric(df_instr[col_repo], errors='coerce').fillna(0)

            df_hasil_pivot_sheet = df_instr.groupby(col_row)[[col_loan, col_repo]].sum().reset_index()
            df_pivot_full = df_hasil_pivot_sheet[df_hasil_pivot_sheet[col_row].notna()]
            df_pivot_full = df_pivot_full[~((df_pivot_full[col_loan] == 0) & (df_pivot_full[col_repo] == 0))]
            df_pivot_full = df_pivot_full.sort_values(by=col_row, ascending=True)

            st.success("✅ Persiapan data selesai.")
        except Exception as e:
            st.error(f"❌ Gagal di Bagian 1/2: Persiapan data. Error: {e}")
            return None, None, None # <-- PERUBAHAN: Tambah None


    # --- BAGIAN 3: Hitung LL ---
    with st.spinner('2/3 - Menghitung Lendable Limit...'):
        try:
            # === Hitung Lendable Limit (LL) ===
            df_main = df_pivot_full.rename(columns={'Local Code': 'Stock Code'})
            df_result = df_main[['Stock Code']].dropna(subset=['Stock Code']).drop_duplicates(subset=['Stock Code']).copy()
            df_result['Stock Code'] = df_result['Stock Code'].astype(str)

            # stock name lookup
            df_inst_lookup = df_instr_old_raw.iloc[1:].rename(columns={2: 'Stock Code', 9: 'Stock Name'})
            df_inst_lookup = df_inst_lookup[['Stock Code', 'Stock Name']].drop_duplicates(subset=['Stock Code'])
            df_inst_lookup['Stock Code'] = df_inst_lookup['Stock Code'].astype(str)
            df_result = df_result.merge(df_inst_lookup, on='Stock Code', how='left')
            df_result['Stock Name'] = df_result['Stock Name'].fillna('')
            
            # QOH sum
            qoh_col_sp = df_sp.columns[10]
            stock_code_col_sp = df_sp.columns[1]
            qoh_calc = df_sp.groupby(stock_code_col_sp)[qoh_col_sp].sum().reset_index().rename(
                columns={stock_code_col_sp: 'Stock Code', qoh_col_sp: 'Quantity On Hand'}
            )
            qoh_calc['Stock Code'] = qoh_calc['Stock Code'].astype(str)
            df_result = df_result.merge(qoh_calc, on='Stock Code', how='left')
            df_result['Quantity On Hand'] = df_result['Quantity On Hand'].fillna(0)

            # borrow position
            stock_code_col_borr = 'Stock Code' if 'Stock Code' in df_borr_pos.columns else df_borr_pos.columns[0]
            df_borr_pos[BORROW_AMOUNT_COL] = pd.to_numeric(df_borr_pos[BORROW_AMOUNT_COL], errors='coerce').fillna(0)
            borr_qty_calc = df_borr_pos[[stock_code_col_borr, BORROW_AMOUNT_COL]].rename(columns={stock_code_col_borr: 'Stock Code', BORROW_AMOUNT_COL: 'Borrow Position'})
            borr_qty_calc = borr_qty_calc.groupby('Stock Code')['Borrow Position'].sum().reset_index()
            borr_qty_calc['Stock Code'] = borr_qty_calc['Stock Code'].astype(str)
            df_result = df_result.merge(borr_qty_calc, on='Stock Code', how='left')
            df_result['Borrow Position'] = df_result['Borrow Position'].fillna(0)
            
            # largest
            largest_cols_map = {df_sp.columns[1]: 'Stock Code', FIRST_LARGERST_COL: FIRST_LARGERST_COL, SECOND_LARGERST_COL: SECOND_LARGERST_COL}
            largest_calc = df_sp.rename(columns=largest_cols_map).groupby('Stock Code')[[FIRST_LARGERST_COL, SECOND_LARGERST_COL]].first().reset_index()
            largest_calc['Stock Code'] = largest_calc['Stock Code'].astype(str)
            df_result = df_result.merge(largest_calc, on='Stock Code', how='left').fillna({FIRST_LARGERST_COL: 0, SECOND_LARGERST_COL: 0})
            
            # repo base
            repo_base_calc = df_pivot_full[['Local Code', 'Used Reverse Repo Qty']].rename(columns={'Local Code': 'Stock Code', 'Used Reverse Repo Qty': 'REPO_Base_TEMP'})
            repo_base_calc['Stock Code'] = repo_base_calc['Stock Code'].astype(str)
            df_result = df_result.merge(repo_base_calc, on='Stock Code', how='left').fillna({'REPO_Base_TEMP': 0})
            
            # final calc LL
            df_result['Total two Largerst'] = df_result[FIRST_LARGERST_COL] + df_result[SECOND_LARGERST_COL]
            df_result['Quantity Available'] = df_result['Quantity On Hand'] - df_result['Total two Largerst']
            df_result['Thirty Percent On Hand'] = 0.30 * df_result['Quantity On Hand']
            df_result['REPO'] = 0.10 * df_result['REPO_Base_TEMP']
            df_result['Lendable Limit'] = np.minimum(df_result['Thirty Percent On Hand'], df_result['Quantity Available']) + df_result['REPO']
            
            # Hitungan LL Akhir
            df_result['Available Lendable Limit'] = df_result['Lendable Limit'] - df_result['Borrow Position']

            # --- Filtering Data ---
            df_result_filtered = df_result[~df_result['Stock Code'].isin(STOCK_CODE_BLACKLIST)].copy()
            df_result_static = df_result_filtered[
                (df_result_filtered['Lendable Limit'] > 0) | (df_result_filtered['Available Lendable Limit'] > 0)
            ].copy()
            
            df_result_all = df_result_filtered.reindex(columns=FINAL_COLUMNS_LL)
            df_result_static = df_result_static.reindex(columns=FINAL_COLUMNS_LL)

            # Tulis file konsolidasi ke buffer
            with pd.ExcelWriter(output_xlsx_buffer, engine='openpyxl') as writer:
                df_result_all.to_excel(writer, sheet_name=SHEET_RESULT_NAME_SOURCE, index=False)
                df_instr_old_raw.to_excel(writer, sheet_name=SHEET_INST_OLD, index=False, header=False)
                df_pivot_full.to_excel(writer, sheet_name=SHEET_INST_NEW, index=False)
                df_sp.to_excel(writer, sheet_name='Stock Position Detail', index=False)
                df_borr_pos.to_excel(writer, sheet_name='BorrPosition', index=False)
            output_xlsx_buffer.seek(0)
            st.success("✅ Perhitungan selesai. File konsolidasi LL dibuat di memori.")

        except Exception as e:
            st.error(f"❌ Gagal di Bagian 2: Perhitungan Lendable Limit. Error: {e}")
            return None, None, None # <-- PERUBAHAN: Tambah None

    # --- BAGIAN 4: COPY HASIL KE TEMPLATE ---
    with st.spinner('3/3 - Menyalin Lendable Limit Result ke Template...'):
        try:
            wb_template = load_workbook(template_file_data)
            ws_template = wb_template.active
            
            thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

            default_style_ll = NamedStyle(name="DefaultStyleLL_LLpage")
            default_style_ll.font = Font(name='Roboto Condensed', size=9)
            default_style_ll.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            default_style_ll.border = thin_border
            if "DefaultStyleLL_LLpage" not in wb_template.named_styles: wb_template.add_named_style(default_style_ll)

            text_left_style_ll = NamedStyle(name="TextLeftStyleLL_LLpage")
            text_left_style_ll.font = Font(name='Roboto Condensed', size=9)
            text_left_style_ll.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
            text_left_style_ll.border = thin_border
            if "TextLeftStyleLL_LLpage" not in wb_template.named_styles: wb_template.add_named_style(text_left_style_ll)

            number_style_ll = NamedStyle(name="NumberStyleLL_LLpage")
            number_style_ll.font = default_style_ll.font
            number_style_ll.alignment = default_style_ll.alignment
            number_style_ll.border = default_style_ll.border
            number_style_ll.number_format = '#,##0'
            if "NumberStyleLL_LLpage" not in wb_template.named_styles: wb_template.add_named_style(number_style_ll)


            # Update tanggal di cell B4
            today_formatted = datetime.now().strftime('%d-%b-%y')
            ws_template["B4"] = today_formatted

            start_row = 7
            start_col = 1
            if ws_template.max_row >= start_row:
                ws_template.delete_rows(start_row, ws_template.max_row - start_row + 1)
            
            number_cols_idx = range(2, 12) # Kolom LL (C s/d L)
            
            for r_idx, row in enumerate(df_result_static.itertuples(index=False), start=start_row):
                for c_idx, value in enumerate(row, start=start_col):
                    cell = ws_template.cell(row=r_idx, column=c_idx, value=value)
                    
                    if c_idx - 1 == 0:  
                        cell.style = default_style_ll
                        cell.value = str(value) if pd.notna(value) else ""
                    elif c_idx - 1 == 1:  
                        cell.style = text_left_style_ll
                        cell.value = str(value) if pd.notna(value) else ""
                    elif c_idx - 1 in number_cols_idx:
                        cell.style = number_style_ll
                        try:
                            if pd.notna(value):
                                cell.value = int(value) if value == int(value) else float(value)
                            else:
                                cell.value = 0
                        except (ValueError, TypeError):
                            cell.value = 0
                    else:
                        cell.style = default_style_ll


            output_template_buffer = BytesIO()
            wb_template.save(output_template_buffer)
            output_template_buffer.seek(0)
            
            st.success("✅ Berhasil menyalin data ke template.")
            
            return output_xlsx_buffer, output_template_buffer, df_result_static # <-- PERUBAHAN: Mengembalikan df_result_static

        except Exception as e:
            st.error(f"❌ Gagal menyalin dan memformat ke template. Error: {e}")
            return None, None, None # <-- PERUBAHAN: Tambah None

# ============================
# ANTARMUKA LL
# ============================

def main():
    st.title("💸 Lendable Limit (LL) Calculation")
    st.markdown("Unggah **tiga** file sumber data LL dan **satu** template.")

    required_files = {
        'Instrument.xlsx': '1. File Instrument',
        'Stock Position Detail.xlsx': '2. File Stock Position Detail',
        'BorrPosition.xlsx': '3. File BorrPosition',
    }
    
    # Kolom untuk Input Data
    cols = st.columns(len(required_files))
    uploaded_files = {}
    for i, (name, help_text) in enumerate(required_files.items()):
        with cols[i]:
            uploaded_files[name] = st.file_uploader(help_text, type=['xlsx'], key=name)
            
    # Input Template (Di baris terpisah)
    template_file = st.file_uploader('4. File Template Output (Template LL.xlsx)', type=['xlsx'], key='template_ll')

    
    all_files_uploaded = all(f is not None for f in uploaded_files.values())
    
    st.markdown("---")
    st.header("Hasil LL")
    
    if all_files_uploaded and template_file is not None:
        if st.button("Jalankan Perhitungan LL", type="primary"):
            
            template_file_data = BytesIO(template_file.getvalue())

            # PERUBAHAN: Menerima df_result_static dari fungsi pemroses
            output_xlsx_buffer, output_template_buffer, df_result_static = process_lendable_limit(uploaded_files, template_file_data)
            
            # PERUBAHAN: Menambahkan pengecekan df_result_static
            if output_xlsx_buffer and output_template_buffer and df_result_static is not None:
                date_str = datetime.now().strftime('%Y%m%d')
                
                # --- LOGIKA UNTUK DOWNLOAD SEDERHANA BARU ---
                # 1. Pilih hanya 3 kolom yang diminta
                simple_ll_df = df_result_static[['Stock Code', 'Stock Name', 'Available Lendable Limit']].copy()
                
                # 2. Konversi DataFrame sederhana ke buffer Excel
                simple_ll_buffer = BytesIO()
                simple_ll_df.to_excel(simple_ll_buffer, index=False)
                simple_ll_buffer.seek(0)
                # ---------------------------------------------
                
                # PERUBAHAN: Menjadi 3 kolom untuk 3 tombol download
                col_down1, col_down2, col_down3 = st.columns(3)

                col_down1.download_button(
                    label="⬇️ Unduh File Konsolidasi (Semua Sheet LL)",
                    data=output_xlsx_buffer,
                    file_name=f'{date_str}- LL_Konsolidasi.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                
                col_down2.download_button(
                    label="⬇️ Unduh File Template LL Terisi",
                    data=output_template_buffer,
                    file_name=f'Lendable Limit {date_str}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                
                # TOMBOL DOWNLOAD BARU
                col_down3.download_button(
                    label="⬇️ Unduh Stock LL Sederhana",
                    data=simple_ll_buffer,
                    file_name=f'Stock_LL_Sederhana_{date_str}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                
            else:
                st.error("Gagal menghasilkan file. Cek pesan error di atas.")
    else:
        st.info("Mohon unggah semua 4 file yang diperlukan untuk LL.")

if __name__ == '__main__':
    main()
