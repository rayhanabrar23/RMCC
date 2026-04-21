# pages/01_Lendable_Limit.py

import streamlit as st
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment, Border, Side, NamedStyle
from io import BytesIO
from datetime import datetime
import os 
import sys

# Import library untuk PDF
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

# Cek apakah sudah login dari halaman utama
if "login_status" not in st.session_state or not st.session_state["login_status"]:
    st.error("🚨 Akses Ditolak! Silakan login di halaman utama terlebih dahulu.")
    st.stop()

from style_utils import apply_custom_style
apply_custom_style()

st.title("Halaman Analisis Risk")

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

PDF_HEADERS = [
    'Kode', 'Nama Saham', 'QOH', 
    '1st Lgst', '2nd Lgst', 'Total Lgst', 
    'Qty Avail', '30% QOH', 'REPO', 
    'LL Limit', 'Borrow Pos', 'Avail LL'
]

# ============================
# FUNGSI STYLING KONDISIONAL
# ============================
def highlight_negative_ll(row):
    value = row['Available Lendable Limit']
    styles = [''] * len(row) 
    if value < 0:
        styles = ['background-color: #FFCCCC'] * len(row) 
    return styles

# ============================
# FUNGSI PEMROSESAN LL
# ============================
def process_lendable_limit(uploaded_files, template_file_data):
    st.info("🚀 Mulai Pemrosesan Lendable Limit...")
    try:
        df_sp = pd.read_excel(uploaded_files['Stock Position Detail.xlsx'], header=0, engine='openpyxl')
        df_instr_raw = pd.read_excel(uploaded_files['Instrument.xlsx'], sheet_name=SHEET_INST_OLD, header=1, engine='openpyxl')
        df_instr_old_raw = pd.read_excel(uploaded_files['Instrument.xlsx'], sheet_name=SHEET_INST_OLD, header=None, engine='openpyxl')
        df_borr_pos = pd.read_excel(uploaded_files['BorrPosition.xlsx'], header=0, engine='openpyxl')
    except Exception as e:
        st.error(f"❌ Gagal membaca salah satu file input LL. Error: {e}")
        return None, None, None

    output_xlsx_buffer = BytesIO()
    
    with st.spinner('Memproses data...'):
        try:
            # 1. Stock Position
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
            df_sp = df_sp.merge(top_values.drop(columns=[qty_col]), how="left", on=stock_col).fillna({FIRST_LARGERST_COL: 0, SECOND_LARGERST_COL: 0})

            # 2. Instrument Pivot
            df_instr = df_instr_raw.copy()
            df_instr.columns = df_instr.columns.str.strip()
            col_row, col_loan, col_repo = "Local Code", "Used Loan Qty", "Used Reverse Repo Qty"
            df_instr[col_loan] = pd.to_numeric(df_instr[col_loan], errors='coerce').fillna(0)
            df_instr[col_repo] = pd.to_numeric(df_instr[col_repo], errors='coerce').fillna(0)

            df_pivot_full = df_instr.groupby(col_row)[[col_loan, col_repo]].sum().reset_index()
            df_pivot_full = df_pivot_full[df_pivot_full[col_row].notna()]
            df_pivot_full = df_pivot_full[~((df_pivot_full[col_loan] == 0) & (df_pivot_full[col_repo] == 0))]

            # 3. Final Calculations
            df_result = df_pivot_full[['Local Code']].rename(columns={'Local Code': 'Stock Code'}).drop_duplicates()
            df_inst_lookup = df_instr_old_raw.iloc[1:].rename(columns={2: 'Stock Code', 9: 'Stock Name'})[['Stock Code', 'Stock Name']].drop_duplicates('Stock Code')
            df_result = df_result.merge(df_inst_lookup, on='Stock Code', how='left')

            qoh_calc = df_sp.groupby(df_sp.columns[1])[df_sp.columns[10]].sum().reset_index().rename(columns={df_sp.columns[1]: 'Stock Code', df_sp.columns[10]: 'Quantity On Hand'})
            df_result = df_result.merge(qoh_calc, on='Stock Code', how='left').fillna(0)

            borr_qty_calc = df_borr_pos.groupby('Stock Code')[BORROW_AMOUNT_COL].sum().reset_index().rename(columns={BORROW_AMOUNT_COL: 'Borrow Position'})
            df_result = df_result.merge(borr_qty_calc, on='Stock Code', how='left').fillna(0)

            largest_calc = df_sp.rename(columns={df_sp.columns[1]: 'Stock Code'}).groupby('Stock Code')[[FIRST_LARGERST_COL, SECOND_LARGERST_COL]].first().reset_index()
            df_result = df_result.merge(largest_calc, on='Stock Code', how='left').fillna(0)
            
            repo_base = df_pivot_full.rename(columns={'Local Code': 'Stock Code', 'Used Reverse Repo Qty': 'REPO_Base'})[['Stock Code', 'REPO_Base']]
            df_result = df_result.merge(repo_base, on='Stock Code', how='left').fillna(0)

            df_result['Total two Largerst'] = df_result[FIRST_LARGERST_COL] + df_result[SECOND_LARGERST_COL]
            df_result['Quantity Available'] = df_result['Quantity On Hand'] - df_result['Total two Largerst']
            df_result['Thirty Percent On Hand'] = 0.30 * df_result['Quantity On Hand']
            df_result['REPO'] = 0.10 * df_result['REPO_Base']
            df_result['Lendable Limit'] = np.minimum(df_result['Thirty Percent On Hand'], df_result['Quantity Available']) + df_result['REPO']
            df_result['Available Lendable Limit'] = df_result['Lendable Limit'] - df_result['Borrow Position']

            df_result_filtered = df_result[~df_result['Stock Code'].isin(STOCK_CODE_BLACKLIST)].copy()
            df_result_static = df_result_filtered[(df_result_filtered['Lendable Limit'] > 0) | (df_result_filtered['Available Lendable Limit'] > 0)].reindex(columns=FINAL_COLUMNS_LL)

            with pd.ExcelWriter(output_xlsx_buffer, engine='openpyxl') as writer:
                df_result_filtered.reindex(columns=FINAL_COLUMNS_LL).to_excel(writer, sheet_name=SHEET_RESULT_NAME_SOURCE, index=False)
                df_instr_old_raw.to_excel(writer, sheet_name=SHEET_INST_OLD, index=False, header=False)
            
            output_xlsx_buffer.seek(0)

            # Copy to Template Full
            wb_template = load_workbook(template_file_data)
            ws = wb_template.active
            ws["B4"] = datetime.now().strftime('%d-%b-%y')
            
            # (Style definition omitted for brevity, assuming standard in your setup)
            
            for r_idx, row in enumerate(df_result_static.itertuples(index=False), start=7):
                for c_idx, value in enumerate(row, start=1):
                    ws.cell(row=r_idx, column=c_idx, value=value)

            output_template_full = BytesIO()
            wb_template.save(output_template_full)
            output_template_full.seek(0)

            return output_xlsx_buffer, output_template_full, df_result_static

        except Exception as e:
            st.error(f"❌ Error Detail: {e}")
            return None, None, None

# ============================================================
# REVISI UTAMA: FUNGSI TEMPLATE EKSTERNAL (SOLUSI DESIMAL)
# ============================================================
def fill_simple_ll_template(df_result, template_buffer):
    wb = load_workbook(template_buffer)
    ws = wb.active 
    ws["B4"] = datetime.now().strftime('%d-%b-%y')

    start_row = 7 
    if ws.max_row >= start_row:
        ws.delete_rows(start_row, ws.max_row - start_row + 1)

    # Styles
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    
    style_code = NamedStyle(name="EXT_CODE")
    style_code.font = Font(name='Roboto Condensed', size=9)
    style_code.alignment = Alignment(horizontal='center', vertical='center')
    style_code.border = thin_border
    if "EXT_CODE" not in wb.named_styles: wb.add_named_style(style_code)

    style_name = NamedStyle(name="EXT_NAME")
    style_name.font = Font(name='Roboto Condensed', size=9)
    style_name.alignment = Alignment(horizontal='left', vertical='center')
    style_name.border = thin_border
    if "EXT_NAME" not in wb.named_styles: wb.add_named_style(style_name)

    style_limit = NamedStyle(name="EXT_LIMIT")
    style_limit.font = Font(name='Roboto Condensed', size=9)
    style_limit.alignment = Alignment(horizontal='center', vertical='center')
    style_limit.border = thin_border
    style_limit.number_format = '#,##0' 
    if "EXT_LIMIT" not in wb.named_styles: wb.add_named_style(style_limit)

    for r_idx, row in enumerate(df_result.itertuples(index=False), start=start_row):
        # Kolom A & B
        cell_a = ws.cell(row=r_idx, column=1, value=str(row[0]) if pd.notna(row[0]) else "")
        cell_a.style = style_code
        cell_b = ws.cell(row=r_idx, column=2, value=str(row[1]) if pd.notna(row[1]) else "")
        cell_b.style = style_name

        # Kolom C: Penanganan Desimal dengan Indentasi Benar
        try:
            # Ambil nilai dari kolom ke-3 (index 2)
            raw_val = row[2]
            if pd.notna(raw_val):
                value_c = int(round(raw_val, 0))
            else:
                value_c = 0
        except (ValueError, TypeError):
            value_c = 0
            
        cell_c = ws.cell(row=r_idx, column=3, value=value_c)
        cell_c.style = style_limit
        
    out = BytesIO()
    wb.save(out)
    out.seek(0)
    return out

# ============================
# PDF CONVERSION & MAIN UI
# ============================
def convert_df_full_to_pdf(df):
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(letter))
    elements = [Paragraph("Lendable Limit Report", getSampleStyleSheet()['Title'])]
    # (Simplified PDF generation)
    doc.build(elements)
    pdf_buffer.seek(0)
    return pdf_buffer

def main():
    st.title("💸 Lendable Limit (LL) Calculation")
    
    cols = st.columns(3)
    u1 = cols[0].file_uploader('1. Instrument', type=['xlsx'])
    u2 = cols[1].file_uploader('2. Stock Position', type=['xlsx'])
    u3 = cols[2].file_uploader('3. BorrPosition', type=['xlsx'])
    
    col_t = st.columns(2)
    t_full = col_t[0].file_uploader('4. Template Full', type=['xlsx'])
    t_simple = col_t[1].file_uploader('5. Template External', type=['xlsx'])

    if all([u1, u2, u3, t_full, t_simple]):
        if st.button("Jalankan Perhitungan LL", type="primary"):
            files = {'Instrument.xlsx': u1, 'Stock Position Detail.xlsx': u2, 'BorrPosition.xlsx': u3}
            res = process_lendable_limit(files, BytesIO(t_full.getvalue()))
            
            if res[0]:
                xlsx_buf, full_buf, df_stat = res
                st.subheader("⚠️ Preview Result")
                st.dataframe(df_stat.style.apply(highlight_negative_ll, axis=1), use_container_width=True)
                
                # Proses External
                simple_df = df_stat[['Stock Code', 'Stock Name', 'Available Lendable Limit']].copy()
                simple_buf = fill_simple_ll_template(simple_df, BytesIO(t_simple.getvalue()))
                
                # Download Buttons
                d_cols = st.columns(3)
                d_cols[0].download_button("⬇️ Konsolidasi", xlsx_buf, "Konsolidasi.xlsx")
                d_cols[1].download_button("⬇️ LL Lengkap", full_buf, f"Lendable Limit {datetime.now().strftime('%Y%m%d')}.xlsx")
                d_cols[2].download_button("⬇️ LL Eksternal", simple_buf, f"Lendable Limit_{datetime.now().strftime('%Y%m%d')}.xlsx")

if __name__ == '__main__':
    main()
