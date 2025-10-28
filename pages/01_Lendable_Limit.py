# pages/01_Lendable_Limit.py

import streamlit as st
import pandas as pd
import numpy as np
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment, Border, Side, NamedStyle, numbers
from io import BytesIO
from datetime import datetime
import os 
import sys

# Import library untuk PDF (Dibutuhkan jika Anda memiliki tombol download PDF)
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

# ============================
# ANTARMUKA LL (MAIN)
# ============================

def main():
    # Panggil fungsi background di baris pertama main()
    # PENTING: Pastikan nama file adalah 'background.jpg'
    set_background_from_local('background.jpg') 
    
    st.title("💸 Lendable Limit (LL) Calculation")

# ============================
# FUNGSI UNTUK BACKGROUND GAMBAR LOKAL
# ============================
def get_base64_of_bin_file(bin_file):
    """Mengonversi file biner (gambar) menjadi string Base64."""
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        st.error(f"❌ Gagal menemukan file gambar: {bin_file}. Pastikan file ada di folder yang sama.")
        return ""

def set_background_from_local(file_path): # Ganti png_file menjadi file_path untuk generalisasi
    """Menyuntikkan CSS dengan gambar latar belakang lokal yang sudah di-Base64."""
    bin_str = get_base64_of_bin_file(file_path)
    if bin_str:
        # Deteksi tipe MIME berdasarkan ekstensi file
        if file_path.lower().endswith(('.jpg', '.jpeg')):
            mime_type = 'image/jpeg'
        elif file_path.lower().endswith('.png'):
            mime_type = 'image/png'
        else:
            mime_type = 'image/jpeg' # Default ke JPEG jika tidak dikenali

        page_bg_img = f"""
        <style>
        .stApp {{
        background-image: url("data:{mime_type};base64,{bin_str}");
        background-size: cover; 
        background-repeat: no-repeat;
        background-attachment: fixed; 
        background-position: center;
        }}
        </style>
        """
        st.markdown(page_bg_img, unsafe_allow_html=True)

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

# === HEADER PDF SEDERHANA UNTUK MENGATASI KETERBATASAN RUANG ===
PDF_HEADERS = [
    'Kode', 'Nama Saham', 'QOH', 
    '1st Lgst', '2nd Lgst', 'Total Lgst', 
    'Qty Avail', '30% QOH', 'REPO', 
    'LL Limit', 'Borrow Pos', 'Avail LL'
]
# ===============================================================


# ============================
# FUNGSI STYLING KONDISIONAL UNTUK TAMPILAN WEB
# ============================
def highlight_negative_ll(row):
    """Menyoroti baris di mana 'Available Lendable Limit' < 0 dengan warna latar merah muda."""
    
    # Ambil nilai dari kolom 'Available Lendable Limit'
    value = row['Available Lendable Limit']
    
    # Membuat daftar style string kosong untuk semua kolom
    styles = [''] * len(row) 
    
    if value < 0:
        # Jika nilainya negatif, terapkan style warna latar merah muda terang
        styles = ['background-color: #FFCCCC'] * len(row) 
    
    return styles


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
        return None, None, None

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
            return None, None, None


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
            # df_result_static adalah data hasil untuk template LL LENGKAP
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
            return None, None, None

    # --- BAGIAN 4: COPY HASIL KE TEMPLATE LL PENUH ---
    with st.spinner('3/3 - Menyalin Lendable Limit Result ke Template...'):
        try:
            wb_template = load_workbook(template_file_data)
            ws_template = wb_template.active
            
            thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

            # Definisikan NamedStyle
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


            output_template_buffer_full = BytesIO()
            wb_template.save(output_template_buffer_full)
            output_template_buffer_full.seek(0)
            
            st.success("✅ Berhasil menyalin data ke template.")
            
            return output_xlsx_buffer, output_template_buffer_full, df_result_static

        except Exception as e:
            st.error(f"❌ Gagal menyalin dan memformat ke template. Error: {e}")
            return None, None, None

# ============================
# FUNGSI UNTUK MENGISI TEMPLATE EKSTERNAL (3 KOLOM)
# ============================
def fill_simple_ll_template(df_result, template_buffer):
    """Mengisi template 3-kolom yang sudah memiliki format yang benar, dimulai dari Row 7, dan mengupdate tanggal di B4."""
    
    # 1. Load template sederhana
    wb = load_workbook(template_buffer)
    ws = wb.active 
    
    # PERUBAHAN: Update tanggal di cell B4
    today_formatted = datetime.now().strftime('%d-%b-%y')
    ws["B4"] = today_formatted

    # Tambahkan style untuk tanggal jika B4 kosong
    try:
        date_style = ws.cell(row=4, column=2).style
    except:
        date_style = NamedStyle(name="LL_Ext_Date_Default")
        date_style.font = Font(name='Roboto Condensed', size=9, bold=True)
        date_style.alignment = Alignment(horizontal='left', vertical='center')
        if "LL_Ext_Date_Default" not in wb.named_styles: wb.add_named_style(date_style)
    
    ws.cell(row=4, column=2).style = date_style

    # Menetapkan baris awal data
    start_row = 7 
    
    # 2. Hapus data lama (jika ada) - Menghapus dari baris start_row ke bawah
    if ws.max_row >= start_row:
        ws.delete_rows(start_row, ws.max_row - start_row + 1)

    # 3. Definisikan Style yang sama dengan template penuh (agar konsisten)
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    # Style untuk Stock Code (Teks, Center)
    style_stock_code = NamedStyle(name="LL_Ext_Code")
    style_stock_code.font = Font(name='Roboto Condensed', size=9)
    style_stock_code.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    style_stock_code.border = thin_border
    if "LL_Ext_Code" not in wb.named_styles: wb.add_named_style(style_stock_code)
    
    # Style untuk Stock Name (Teks, Left)
    style_stock_name = NamedStyle(name="LL_Ext_Name")
    style_stock_name.font = Font(name='Roboto Condensed', size=9)
    style_stock_name.alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
    style_stock_name.border = thin_border
    if "LL_Ext_Name" not in wb.named_styles: wb.add_named_style(style_stock_name)
    
    # Style untuk Available Lendable Limit (Angka, Center, #,##0)
    style_available_ll = NamedStyle(name="LL_Ext_Limit")
    style_available_ll.font = Font(name='Roboto Condensed', size=9)
    style_available_ll.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    style_available_ll.border = thin_border
    style_available_ll.number_format = '#,##0' 
    if "LL_Ext_Limit" not in wb.named_styles: wb.add_named_style(style_available_ll)


    # 4. Tulis data baru (Mulai dari row 7)
    for r_idx, row in enumerate(df_result.itertuples(index=False), start=start_row):
        # Kolom A (1): Stock Code
        cell_A = ws.cell(row=r_idx, column=1, value=str(row[0]) if pd.notna(row[0]) else "")
        cell_A.style = style_stock_code

        # Kolom B (2): Stock Name
        cell_B = ws.cell(row=r_idx, column=2, value=str(row[1]) if pd.notna(row[1]) else "")
        cell_B.style = style_stock_name

        # Kolom C (3): Available Lendable Limit (Harus berupa float/int agar format #,##0 bekerja)
        value_C = int(row[2]) if pd.notna(row[2]) and row[2] == int(row[2]) else (float(row[2]) if pd.notna(row[2]) else 0)
        cell_C = ws.cell(row=r_idx, column=3, value=value_C)
        cell_C.style = style_available_ll
        
    # 5. Simpan ke buffer baru
    output_buffer = BytesIO()
    wb.save(output_buffer)
    output_buffer.seek(0)
    return output_buffer


# ============================
# FUNGSI TAMBAHAN UNTUK KONVERSI KE PDF (MENGGUNAKAN df_result_static)
# ============================
def convert_df_full_to_pdf(df_result_static):
    """Mengubah DataFrame LL Lengkap (df_result_static) menjadi buffer PDF."""
    
    pdf_buffer = BytesIO()
    
    # Siapkan data dari DataFrame (menggunakan header yang disederhanakan)
    data_list = [PDF_HEADERS] 
    
    for row in df_result_static.itertuples(index=False):
        # Format angka menggunakan f-string untuk ribuan
        formatted_row = [
            str(row[0]),  # 0: Stock Code
            str(row[1]),  # 1: Stock Name
            f'{row[2]:,.0f}', # 2: Quantity On Hand
            f'{row[3]:,.0f}', # 3: First Largest
            f'{row[4]:,.0f}', # 4: Second Largest
            f'{row[5]:,.0f}', # 5: Total two Largest
            f'{row[6]:,.0f}', # 6: Quantity Available
            f'{row[7]:,.0f}', # 7: Thirty Percent On Hand
            f'{row[8]:,.0f}', # 8: REPO
            f'{row[9]:,.0f}', # 9: Lendable Limit
            f'{row[10]:,.0f}',# 10: Borrow Position
            f'{row[11]:,.0f}' # 11: Available Lendable Limit
        ]
        data_list.append(formatted_row)

    # Menggunakan pagesize landscape (horizontal) karena kolomnya banyak (12 kolom)
    doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(letter),
                            leftMargin=0.25*inch, rightMargin=0.25*inch,
                            topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    
    elements = []
    
    # Tambahkan judul dan tanggal
    elements.append(Paragraph(f"Lendable Limit Saham Jaminan PEI (LENGKAP)", styles['Title']))
    today_formatted = datetime.now().strftime('%d %B %Y')
    elements.append(Paragraph(f"Tanggal: {today_formatted}", styles['Normal']))
    elements.append(Paragraph("<br/>", styles['Normal'])) # Spasi

    # Atur lebar kolom secara optimal untuk 12 kolom di kertas landscape
    col_widths = [0.6*inch, 1.6*inch] + [0.8*inch] * 9 + [1.1*inch] 
    table = Table(data_list, colWidths=col_widths)
    
    # Style Tabel
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F2F2F2')), 
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'), 
        ('ALIGN', (0, 1), (0, -1), 'CENTER'), 
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),   
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 7), 
    ])
    table.setStyle(table_style)
    
    elements.append(table)
    
    doc.build(elements)
    
    pdf_buffer.seek(0)
    return pdf_buffer


# ============================
# ANTARMUKA LL (MAIN)
# ============================

def main():
    st.title("💸 Lendable Limit (LL) Calculation")
    st.markdown("Unggah **tiga** file sumber data LL dan **dua** template.")

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
    col_temp1, col_temp2 = st.columns(2)
    with col_temp1:
        template_file_full = st.file_uploader('4. File Template Output LL Lengkap', type=['xlsx'], key='template_ll_full')
    with col_temp2:
        template_file_simple = st.file_uploader('5. File Template Output Lendable Limit Eksternal', type=['xlsx'], key='template_ll_simple')

    
    all_files_uploaded = all(f is not None for f in uploaded_files.values())
    
    st.markdown("---")
    st.header("Hasil LL")
    
    # Cek semua 5 file
    if all_files_uploaded and template_file_full is not None and template_file_simple is not None:
        if st.button("Jalankan Perhitungan LL", type="primary"):
            
            template_file_data_full = BytesIO(template_file_full.getvalue())
            template_file_data_simple = BytesIO(template_file_simple.getvalue()) 

            output_xlsx_buffer, output_template_buffer_full, df_result_static = process_lendable_limit(uploaded_files, template_file_data_full)
            
            if output_xlsx_buffer and output_template_buffer_full and df_result_static is not None:
                date_str = datetime.now().strftime('%Y%m%d')
                
                # =========================================================
                # ✅ TAMPILAN DATA DI WEB DENGAN SOROTAN MERAH (BARU)
                # =========================================================
                st.subheader("⚠️ Lendable Limit Result (Negatif disorot Merah)")
                
                # Menggunakan Pandas Styler untuk menerapkan fungsi highlight
                styled_df = df_result_static.style.apply(highlight_negative_ll, axis=1)
                
                # Tampilkan DataFrame yang sudah di-style di Streamlit
                st.dataframe(styled_df, use_container_width=True)
                
                st.markdown("---")
                
                # =========================================================
                # --- LOGIKA UNTUK OUTPUT EKSTERNAL SEDERHANA ---
                simple_ll_df = df_result_static[['Stock Code', 'Stock Name', 'Available Lendable Limit']].copy()
                output_template_buffer_simple = fill_simple_ll_template(simple_ll_df, template_file_data_simple)
                
                # --- LOGIKA UNTUK PDF (DARI DATA LL LENGKAP) ---
                output_pdf_buffer = convert_df_full_to_pdf(df_result_static)
                # ----------------------------------------------

                st.subheader("Tombol Unduh (Memicu 'Save As' di Browser Anda)")
                
                # Menggunakan layout yang lebih baik: (Konsolidasi) (LL Lengkap + PDF) (LL Eksternal)
                col_down1, col_down2, col_down_pdf, col_down3 = st.columns([1, 1, 1, 1])

                # Tombol Download 1: Konsolidasi (Save As)
                col_down1.download_button(
                    label="⬇️ Unduh Konsolidasi (.xlsx)",
                    data=output_xlsx_buffer,
                    file_name=f'{date_str}- LL_Konsolidasi.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                
                # Tombol Download 2: LL Lengkap (Save As)
                col_down2.download_button(
                    label="⬇️ Unduh LL Lengkap (.xlsx)",
                    data=output_template_buffer_full,
                    file_name=f'Lendable Limit {date_str}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                
                # Tombol Download 4: PDF (DARI TEMPLATE LL LENGKAP)
                col_down_pdf.download_button(
                    label="⬇️ Unduh LL Lengkap (.pdf)",
                    data=output_pdf_buffer,
                    file_name=f'Lendable Limit {date_str}.pdf',
                    mime='application/pdf'
                )

                # Tombol Download 3: LL Eksternal (Save As)
                col_down3.download_button(
                    label="⬇️ Unduh LL Eksternal (.xlsx)",
                    data=output_template_buffer_simple,
                    file_name=f'Lendable Limit Eksternal {date_str}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                
            else:
                st.error("Gagal menghasilkan file. Cek pesan error di atas.")
    else:
        st.info("Mohon unggah **semua 5 file** yang diperlukan: 3 file data, 1 template LL Lengkap, dan 1 template Lendable Limit Eksternal.")

if __name__ == '__main__':
    main()


