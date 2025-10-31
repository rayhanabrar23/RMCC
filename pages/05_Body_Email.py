import streamlit as st
import pandas as pd
from datetime import date
import os
import numpy as np
import re
from io import StringIO

# --- KONFIGURASI STREAMLIT & TEMPLATE ---

st.set_page_config(
    page_title="Generator Body Email Harian",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Template placeholder (USER HARUS MENGISI INI DENGAN KONTEN ASLI MEREKA)
# Ini akan diganti dengan input dari st.text_area
DEFAULT_EMAIL_TEMPLATE = """
Kepada Yth. Bapak/Ibu,

Dengan hormat,

Berikut adalah ringkasan harian Daily Summary PEI per tanggal **{{tanggal_laporan}}**.

Kami mencatat ada **{{jumlah_xc_margin_call}}** peserta yang terkena Excess Collateral/Margin Call.

**1. Posisi Marjin Harian:**
{{tabel_posisi_marjin}}

**2. Posisi REPO Normal:**
{{tabel_posisi_repo}}

**3. Posisi REPO Restrukturisasi (ASS, MSU, BBM):**
{{tabel_repo_restrukturisasi}}

**4. Posisi Reverse REPO Bonds:**
{{tabel_repo_bond}}

**5. Posisi PME / SLB:**
{{tabel_posisi_pme}}

Demikian laporan ini disampaikan. Atas perhatiannya kami ucapkan terima kasih.

Hormat kami,
[Nama Departemen Anda]
"""

# --- FUNGSI STYLING HTML (CSS Inline) ---

def get_html_style():
    """Mengembalikan tag <style> untuk CSS dasar yang kompatibel dengan email."""
    # Menggunakan font fallback yang umum
    css_style = """
    <style>
        body, table {
            font-family: Arial, sans-serif; 
            font-collapse: collapse;
            width: 100%; 
        }
        th, td {
            border: 1px solid #000;
            padding: 2px 4px; 
            text-align: center;
            vertical-align: middle;
        }
        th {
            font-weight: bold;
            background-color: #f2f2f2;
            text-align: center;
            white-space: normal;
            line-height: 1.2;
        }
        .total-row td {
            font-weight: bold;
            background-color: #d9d9d9;
        }
        p, b { 
            font-size: 11pt;
            font-family: Arial, sans-serif; 
        }
    </style>
    """
    return css_style


def clean_headers(df):
    """
    Membersihkan dan merapikan nama kolom (header),
    serta menghilangkan kolom index yang tidak sengaja terbaca.
    """
    # Mapping header yang sangat detail
    header_mapping = {
        'Participant Code': 'Participant<br>Code',
        'Participant Name': 'Participant<br>Name',
        'TotalCashShortfall': 'Total Cash<br>Shortfall',
        'TotalNetCashShortfall': 'Total Net<br>Cash<br>Shortfall',
        'Total NetCashShortfall': 'Total Net<br>Cash<br>Shortfall',
        'TotalNet CashShortfall': 'Total Net<br>Cash<br>Shortfall',
        'Total Net CashShortfall': 'Total Net<br>Cash<br>Shortfall',
        'Total Net Cash Shortfall': 'Total Net<br>Cash<br>Shortfall',
        'ClientCollateralValue': 'Client<br>Collateral<br>Value',
        'ParticipantCollateralValue': 'Participant<br>Collateral<br>Value',
        'AccruedInterest': 'Accrued<br>Interest',
        'AccruedPenalty': 'Accrued<br>Penalty',
        'OutstandingAmount': 'Outstanding<br>Amount',
        'StockCode': 'Stock<br>Code',
        'KPEKContractNo': 'KPEK<br>Contract<br>No',
        'ShockCode': 'Shock<br>Code',
        'CollateralRatio': 'Collateral<br>Ratio',
        'ExemptionRatio': 'Exemption<br>Ratio',
        'RepoPrice': 'Repo<br>Price',
        'RepoValue': 'Repo<br>Value',
        'CurrentMarketPrice': 'Current<br>Market<br>Price',
        'RequiredCollateralValue': 'Required<br>Collateral<br>Value',
        'CurrentCollateralValue': 'Current<br>Collateral<br>Value',
        'MarginRatio': 'Margin<br>Ratio',
        'CounterpartName': 'Counterpart<br>Name',
        'Excess /Lack fromRequiredCollateral': 'Excess / Lack<br>from Required<br>Collateral',
        'CurrentMarginRatio': 'Current<br>Margin<br>Ratio',
        'Excess_LackfromRequiredCollateral': 'Excess / Lack<br>from Required<br>Collateral',
        'Excess/LackfromRequiredCollateral': 'Excess / Lack<br>from Required<br>Collateral',
        'Current Margin Ratio': 'Current<br>Margin<br>Ratio',
        'Estimated Period (days)': 'Est. Period (Days)',
        'Daily Position': 'Daily Pos.',
        'Borrow Price': 'Borrow Price',
        'Borrow Amount': 'Borrow Amount',
        'Borrow Value': 'Borrow Value',
        'Client Code': 'Client<br>Code',
        'Client Name': 'Client<br>Name',
        'DailyPos.': 'Daily Pos.',
        'Estimated Period (Days)': 'Est. Period (Days)',
    }

    new_columns = {}
    cols_to_drop = []

    for col in df.columns:
        original_col = str(col)
        original_col_stripped = original_col.strip()

        # 1. Identifikasi kolom yang akan di-drop
        if original_col_stripped.lower() in ('nan', '') or re.match(r'Unnamed: \d+', original_col_stripped):
            cols_to_drop.append(col)

    df = df.drop(columns=cols_to_drop, errors='ignore')

    # 2. Lakukan rename header
    for col in df.columns:
        original_col = str(col).strip()
        if original_col in header_mapping:
            new_columns[original_col] = header_mapping[original_col]

    df = df.rename(columns=new_columns)
    return df


def apply_custom_styling(styler):
    """Menerapkan styling khusus pada DataFrame Styler, termasuk font-size dan FONT-FAMILY INLINE."""

    # Mengganti font-family 'Roboto Condensed' dengan 'Arial' (lebih umum di email)
    default_font = "Arial, sans-serif"

    # 1. Terapkan Font Size dan FONT FAMILY secara INLINE untuk HEADER
    styler = styler.set_table_styles([
        {'selector': 'th', 'props': [
            ('font-size', '9pt'),
            ('font-family', default_font), 
            ('border', '1px solid #000'), # Tambahkan border pada TH
            ('background-color', '#f2f2f2'),
            ('text-align', 'center'),
            ('vertical-align', 'middle'),
        ]}
    ], overwrite=False)

    # 2. Terapkan Font Size dan FONT FAMILY secara INLINE untuk BODY (TD)
    styler = styler.set_properties(**{
        'font-size': '8pt',
        'font-family': default_font,
        'border': '1px solid #000', # Tambahkan border pada TD
        'text-align': 'center',
        'vertical-align': 'middle',
    }, subset=pd.IndexSlice[styler.index, styler.columns])


    def highlight_total_row(row):
        first_col_value = row.iloc[0]
        # Menggunakan pencarian yang fleksibel di kolom pertama
        if isinstance(first_col_value, str) and (
                'TOTAL' in first_col_value.upper() or 'JUMLAH' in first_col_value.upper()):
            # Terapkan font-size 8pt (sesuai body) ke baris total
            return [f'font-weight: bold; background-color: #d9d9d9; font-size: 8pt; font-family: {default_font};'] * len(row)
        return [''] * len(row)

    styler = styler.apply(highlight_total_row, axis=1)

    # Tambahkan atribut tabel global
    styler = styler.set_table_attributes(
        'style="border-collapse: collapse; border: 1px solid #000; table-layout: auto; width: 100%;"')

    return styler


# --- FUNGSI RE-IMPLEMENTASI MERGE KOLOM TOTAL DENGAN REGEX ---

def merge_total_row_cells(html_table_string):
    """
    Memodifikasi string HTML tabel untuk menggabungkan sel-sel kosong sebelum sel 'TOTAL'
    dalam baris yang memiliki kata kunci 'TOTAL' atau 'JUMLAH'.
    """
    default_font = "Arial, sans-serif"

    def replace_total_row(match):
        tr_open = match.group(1)
        td_content = match.group(2)
        tr_close = match.group(3)

        cells = re.findall(r'<td[^>]*>.*?</td>', td_content, re.DOTALL)
        cell_contents = [re.sub(r'<td[^>]*>(.*?)</td>', r'\1', cell, flags=re.DOTALL).strip() for cell in cells]

        total_index = -1
        for i, content in enumerate(cell_contents):
            # Cari sel yang mengandung TOTAL atau JUMLAH
            if re.search(r'TOTAL|JUMLAH', content, re.IGNORECASE) and i > 0: # Cek i > 0 agar tidak merge kolom pertama
                total_index = i
                break

        if total_index > 0:
            # Hitung jumlah kolom yang akan di-merge (sel pertama + sel kosong sebelumnya)
            cols_to_merge = total_index + 1 

            # Ambil seluruh tag <td> (termasuk style) dari sel yang berisi TOTAL/JUMLAH
            total_cell = cells[total_index]
            total_cell_attrs_match = re.search(r'(<td[^>]*>)', total_cell)
            merged_cell_content = cell_contents[total_index]

            # Atribut CSS wajib untuk memastikan merge berhasil dan konsisten
            fixed_style = f"text-align: center; font-weight: bold; background-color: #d9d9d9; font-size: 8pt; font-family: '{default_font}'; border: 1px solid #000;"

            if total_cell_attrs_match:
                # Ambil atribut aslinya dan tambahkan/timpa style yang pasti
                original_tag = total_cell_attrs_match.group(0).replace('>', '').strip()
                # Ganti/Tambahkan style attribute
                if 'style=' in original_tag.lower():
                    new_td_tag = re.sub(r'style="[^"]*"', f'style="{fixed_style}"', original_tag, flags=re.IGNORECASE)
                else:
                    new_td_tag = f'{original_tag} style="{fixed_style}"'
                
                # Tambahkan colspan
                new_td_tag = new_td_tag + f' colspan="{cols_to_merge}">'
            else:
                # Fallback
                new_td_tag = f'<td colspan="{cols_to_merge}" style="{fixed_style}">'

            # Sel gabungan baru:
            new_merged_cell = f'{new_td_tag}{merged_cell_content}</td>'

            # Sisa sel yang berisi angka (dimulai dari total_index + 1)
            remaining_cells = cells[total_index + 1:]

            # Bangun ulang baris <tr>
            new_row_content = new_merged_cell + ''.join(remaining_cells)

            return f"{tr_open}{new_row_content}{tr_close}"

        return match.group(0)

    # Pola RegEx untuk mencocokkan seluruh baris <tr> yang memiliki salah satu selnya berisi "TOTAL" atau "JUMLAH"
    pattern = r'(<tr[^>]*>)(.*?)(</tr>)'
    modified_html = re.sub(pattern, replace_total_row, html_table_string, flags=re.DOTALL)
    return modified_html


# --- A. FUNGSI GENERATOR TABEL UTAMA ---

def generate_html_table(file_object, header_row, skip_header_rows, skip_footer_rows, sep_char):
    """Membaca file CSV/TXT (dari Streamlit File Object) dan mengkonversinya menjadi tabel HTML."""
    file_name = file_object.name
    try:
        # Baca konten file
        file_object.seek(0)
        content = StringIO(file_object.getvalue().decode('latin-1'))
        
        # NOTE: Untuk mengatasi masalah header (skiprows) dan footer (skipfooter) yang kompleks
        # di Streamlit, kita akan memuat data mentah terlebih dahulu jika ada skipfooter.
        
        # Membaca semua baris
        df_full = pd.read_csv(
            content, sep=sep_char, header=None, encoding='latin-1', engine='python'
        )

        # 1. Hapus footer
        if skip_footer_rows > 0:
            df_full = df_full.iloc[:-skip_footer_rows]
            
        # 2. Tentukan baris header dan data
        header_index = header_row + skip_header_rows # header_row=0 (indeks header di dalam data yang tersisa)
        
        if len(df_full) <= header_index:
             raise ValueError(f"Struktur CSV tidak valid. Jumlah baris ({len(df_full)}) kurang dari target header (baris {header_index+1}).")
            
        # Ambil baris header (berdasarkan indeks 0)
        df_full.columns = df_full.iloc[header_index]
        
        # Ambil data (dari baris setelah header hingga akhir)
        df = df_full.iloc[header_index + 1:].reset_index(drop=True)
        
        # Cleanup
        df = df.dropna(axis=1, how='all').replace({np.nan: ''})

        df = clean_headers(df)
        styler = df.style.pipe(apply_custom_styling)

        html_table = styler.to_html(index=False, classes='', border=0) + "<br><br>"
        html_table = merge_total_row_cells(html_table)

        st.success(f"✅ Tabel dari file **{file_name}** berhasil dibuat.")
        return html_table

    except Exception as e:
        st.error(f"❌ ERROR saat membuat tabel dari file **{file_name}**. Cek struktur CSV: {e}")
        return f"<p style=\"font-size: 11pt; font-family: Arial, sans-serif;\">❌ ERROR saat membuat tabel. Cek struktur CSV: {e}</p><br><br>"


def generate_html_table_by_row_range(file_object, start_row, end_row, sep_char):
    """Membaca data dari rentang baris tertentu (1-based, inklusif) dan mengkonversinya menjadi HTML."""
    file_name = file_object.name
    try:
        file_object.seek(0)
        content = StringIO(file_object.getvalue().decode('latin-1'))
        
        # Membaca data mentah
        df_full = pd.read_csv(
            content, sep=sep_char, header=None, encoding='latin-1', engine='python'
        )
        
        # Streamlit file object is 0-indexed, rows are 1-based inclusive.
        # Baris yang diinginkan: dari start_row - 1 sampai end_row (inklusi)
        # Jika start_row = 20 dan end_row = 30, berarti indeks 19 sampai 29
        
        df_segment = df_full.iloc[start_row - 1 : end_row].copy()

        # Baris pertama (0) adalah header
        df_segment.columns = df_segment.iloc[0]
        # Ambil semua baris kecuali baris header yang sudah diangkat
        df = df_segment[1:].reset_index(drop=True).dropna(axis=1, how='all').replace({np.nan: ''})

        df = clean_headers(df)
        styler = df.style.pipe(apply_custom_styling)

        html_table = styler.to_html(index=False, classes='', border=0) + "<br><br>"
        html_table = merge_total_row_cells(html_table)

        st.success(
            f"✅ Tabel restrukturisasi dari file **{file_name}** berhasil dibuat (Baris {start_row}-{end_row}).")
        return html_table

    except Exception as e:
        st.error(f"❌ ERROR saat membuat tabel restrukturisasi dari file **{file_name}**: {e}")
        return f"<p style=\"font-size: 11pt; font-family: Arial, sans-serif;\">❌ ERROR saat membuat tabel restrukturisasi. Cek rentang baris/struktur CSV: {e}</p><br><br>"


def generate_table_slb(file_object):
    """Fungsi khusus untuk Tabel 5 (Posisi PME/SLB)."""
    file_name = file_object.name
    try:
        # Fungsi konversi angka ke format Indonesia
        def format_thousand_indonesian(x):
            if pd.notna(x) and x != '':
                try:
                    # Menangani string yang mungkin sudah diformat dengan titik sebagai pemisah ribuan
                    num_str = str(x).replace('.', '').replace(',', '.') if isinstance(x, str) else str(x)
                    num = float(num_str)
                    
                    # Jika bilangan bulat, format tanpa desimal
                    if num == int(num):
                        formatted = f'{int(num):,}'.replace(',', '_temp_').replace('.', ',').replace('_temp_', '.')
                    # Jika bilangan desimal, format dengan 2 desimal
                    else:
                        formatted = f'{num:,.2f}'.replace(',', '_temp_').replace('.', ',').replace('_temp_', '.')
                    return formatted
                except (ValueError, TypeError):
                    return x 
            return x

        file_object.seek(0)
        content = StringIO(file_object.getvalue().decode('latin-1'))
        
        # Membaca data dengan konfigurasi khusus
        df_slb_full = pd.read_csv(
            content, sep=';', header=0, skiprows=7, encoding='latin-1', engine='python'
        )
        
        # Reset thousands dan decimal (karena di atas sudah dibaca sebagai string)
        df_slb_full = df_slb_full.dropna(axis=1, how='all').replace({np.nan: ''})
        
        df_slb_data = df_slb_full.copy()
        
        # Ambil data sampai baris TOTAL
        try:
            total_row_index = df_slb_full[
                df_slb_full.iloc[:, 0].astype(str).str.contains('TOTAL|JUMLAH', case=False, na=False)
            ].index[0]
            df_slb_data = df_slb_full.iloc[:total_row_index + 1].copy()
        except IndexError:
            df_slb_data = df_slb_full.copy()

        # Format kolom angka ke format Indonesia
        cols_to_format_indonesian = [col for col in df_slb_data.columns if
                                     ('Amount' in str(col) or 'Value' in str(col) or 'Price' in str(col) or 'Borrow' in str(col)) and 'Code' not in str(col)]
        
        for col_name in cols_to_format_indonesian:
            df_slb_data.loc[:, col_name] = df_slb_data[col_name].apply(format_thousand_indonesian)
            
        # Format Estimated Period
        last_col_name = df_slb_data.columns[-1]
        if last_col_name and 'Estimated Period' in str(last_col_name):
            df_slb_data.loc[:, last_col_name] = df_slb_data[last_col_name].apply(
                lambda x: f"{int(float(x))}" if str(x).strip() != '' and pd.to_numeric(x, errors='coerce') is not None and float(x) == int(float(x)) else x
            )

        df_slb_data = clean_headers(df_slb_data)
        styler = df_slb_data.style.pipe(apply_custom_styling)
        tabel_posisi_pme_html = styler.to_html(index=False, classes='', border=0) + "<br><br>"
        tabel_posisi_pme_html = merge_total_row_cells(tabel_posisi_pme_html)
        
        st.success(f"✅ Tabel PME/SLB dari file **{file_name}** berhasil dibuat.")
        return tabel_posisi_pme_html

    except Exception as e:
        st.error(f"❌ ERROR saat membuat tabel PME/SLB dari file **{file_name}**: {e}")
        return f"<p style=\"font-size: 11pt; font-family: Arial, sans-serif;\">❌ ERROR saat membuat tabel PME. Cek struktur CSV: {e}</p><br><br>"


# --- B. FUNGSI EKSEKUSI DATA DAN TEMPLATE ---
def generate_email_body(email_template, uploaded_files):
    """
    Mengambil file yang diunggah dan templat,
    kemudian menghasilkan konten HTML lengkap.
    """
    
    # 1. PENGELOMPOKAN FILE
    # Pastikan urutan file sesuai dengan yang diharapkan
    
    try:
        FILE_1 = uploaded_files['PEI Daily Position']
        FILE_2 = uploaded_files['Repo Daily Position Normal']
        FILE_3 = uploaded_files['Repo Daily Position ASS, MSU, BBM']
        FILE_4 = uploaded_files['Reverse Repo Bonds Daily Position']
        FILE_5 = uploaded_files['SLB Position']
    except KeyError as e:
        st.error(f"File **{e.args[0]}** belum diunggah. Mohon lengkapi semua file.")
        return None

    # 2. GENERATE TABEL

    # Tabel 1: Posisi Marjin
    tabel_posisi_marjin_html = generate_html_table(
        FILE_1, header_row=0, skip_header_rows=5, skip_footer_rows=3, sep_char=';'
    )
    tabel_posisi_marjin_html = "<br>" + tabel_posisi_marjin_html
    
    # Tabel 2: Posisi REPO Normal
    tabel_posisi_repo_html = generate_html_table(
        FILE_2, header_row=0, skip_header_rows=16, skip_footer_rows=6, sep_char=';'
    )
    
    # Tabel 3: REPO Restrukturisasi
    tabel_repo_restrukturisasi_html = generate_html_table_by_row_range(
        FILE_3, start_row=20, end_row=30, sep_char=';'
    )
    
    # Tabel 4: Reverse Repo Bond
    tabel_repo_bond_html = generate_html_table_by_row_range(
        FILE_4, start_row=11, end_row=15, sep_char=';'
    )
    
    # Tabel 5: Posisi PME/SLB
    tabel_posisi_pme_html = generate_table_slb(FILE_5)


    # 3. DATA UNTUK PLACEHOLDER
    # *Note: jumlah_xc_margin_call diset manual, atau bisa dihitung dari Tabel 1
    # Karena data awal tidak jelas, kita hardcode angkanya seperti di kode lama.
    data_harian = {
        'tanggal_laporan': date.today().strftime("%d %B %Y"),
        'jumlah_xc_margin_call': 2, # Angka dummy dari kode lama
        'tabel_posisi_marjin': tabel_posisi_marjin_html,
        'tabel_posisi_repo': tabel_posisi_repo_html,
        'tabel_repo_restrukturisasi': tabel_repo_restrukturisasi_html,
        'tabel_repo_bond': tabel_repo_bond_html,
        'tabel_posisi_pme': tabel_posisi_pme_html
    }

    # 4. ISI TEMPLATE
    final_template = email_template
    for key, value in data_harian.items():
        # Mengganti placeholder {{key}} dengan nilai
        final_template = final_template.replace('{{' + key + '}}', str(value))

    # 5. Gabungkan CSS styling dan body template
    final_html = f"<!DOCTYPE html><html><head>{get_html_style()}</head><body>{final_template}</body></html>"

    return final_html


# --- C. EKSEKUSI STREAMLIT UTAMA ---

def main():
    st.title("✉️ Generator Body Email Laporan Harian")
    st.markdown("""
    Alat ini menggantikan skrip Python lokal Anda dengan Streamlit.
    Silakan **unggah kelima file CSV/TXT** Anda dan **masukkan konten templat email**
    untuk membuat *body* HTML email yang siap disalin.
    """)
    st.markdown("---")
    
    uploaded_files_map = {}
    
    with st.sidebar:
        st.header("1. Konten Template Email")
        email_template_input = st.text_area(
            "Salin dan Tempel Konten Template Email Anda di sini (termasuk placeholder {{...}}):",
            value=DEFAULT_EMAIL_TEMPLATE,
            height=300,
            key="email_template_area"
        )
        st.markdown("---")
        
        st.header("2. Unggah File CSV/TXT")
        
        required_files = [
            'PEI Daily Position',
            'Repo Daily Position Normal',
            'Repo Daily Position ASS, MSU, BBM',
            'Reverse Repo Bonds Daily Position',
            'SLB Position'
        ]
        
        for name in required_files:
            file_obj = st.file_uploader(f"Unggah File: **{name}** (Gunakan separator: `;`)", 
                                        type=['csv', 'txt'], key=name)
            if file_obj is not None:
                uploaded_files_map[name] = file_obj
                
        st.markdown("---")
        
        if st.button("🚀 Buat Body Email HTML", use_container_width=True, type="primary"):
            if len(uploaded_files_map) == len(required_files) and email_template_input:
                st.session_state['run_generation'] = True
            else:
                st.error("Mohon lengkapi **semua file** dan **template email** sebelum menjalankan.")
        
        # Reset state untuk percobaan baru
        if st.button("🔄 Reset", use_container_width=True):
            for name in required_files:
                if name in st.session_state:
                    del st.session_state[name]
            st.session_state['run_generation'] = False
            st.rerun()

    
    # Tampilan utama
    if st.session_state.get('run_generation', False):
        st.header("Hasil Body Email HTML")
        st.info("Salin teks di bawah (termasuk tag HTML) dan tempel di body email Anda.")
        
        with st.spinner("Sedang memproses dan menggabungkan data..."):
            final_html_body = generate_email_body(email_template_input, uploaded_files_map)
        
        if final_html_body:
            st.code(final_html_body, language='html')
            st.markdown("---")
            
            st.subheader("Preview Tampilan Email")
            # Menampilkan HTML mentah yang dapat dilihat sebagai preview
            st.components.v1.html(final_html_body, height=800, scrolling=True)


if __name__ == "__main__":
    # Inisialisasi state untuk memicu pembuatan email setelah button diklik
    if 'run_generation' not in st.session_state:
        st.session_state['run_generation'] = False
        
    main()
