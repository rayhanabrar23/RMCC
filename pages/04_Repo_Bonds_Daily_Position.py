import streamlit as st
import pandas as pd
import re
from openpyxl import load_workbook
from io import BytesIO
from datetime import datetime
from zoneinfo import ZoneInfo

# Cek login
if "login_status" not in st.session_state or not st.session_state["login_status"]:
    st.error("🚨 Akses Ditolak! Silakan login di halaman utama terlebih dahulu.")
    st.stop()

# ─────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp { background-color: #0f1117; color: #e8eaf0; }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1d2e 0%, #141624 100%);
        border-right: 1px solid #2a2d3e;
    }

    .card {
        background: #1a1d2e;
        border: 1px solid #2a2d3e;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 16px;
    }
    .card-title {
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        color: #5c7cfa;
        text-transform: uppercase;
        margin-bottom: 6px;
    }

    .main-header {
        background: linear-gradient(135deg, #1a1d2e 0%, #1e2340 100%);
        border: 1px solid #2a2d3e;
        border-radius: 14px;
        padding: 24px 28px;
        margin-bottom: 24px;
    }
    .main-header h1 { font-size: 1.6rem; font-weight: 700; color: #e8eaf0; margin: 0; }
    .main-header p  { color: #6b7080; margin: 6px 0 0 0; font-size: 0.88rem; }

    .stButton > button {
        background: linear-gradient(135deg, #3b5bdb, #5c7cfa);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 10px 24px;
        transition: opacity 0.2s;
    }
    .stButton > button:hover { opacity: 0.88; }

    [data-testid="stFileUploader"] {
        background: #1a1d2e;
        border: 1px dashed #3b5bdb;
        border-radius: 10px;
        padding: 8px;
    }

    hr { border-color: #2a2d3e; }

    .stTextInput > div > div, .stSelectbox > div > div {
        background: #1a1d2e !important;
        border-color: #2a2d3e !important;
        color: #e8eaf0 !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================
# KONSTANTA & KONFIGURASI
# ============================
# Nama kolom dicari lewat teks header (bukan nomor baris/kolom tetap),
# jadi aman kalau posisi tabel di template bergeser.
TEMPLATE_KEY_HEADER = 'INSTRUMENTCODE'      # header "Instrument Code" / "Instrument\nCode"
TEMPLATE_VALUE_HEADER = 'FAIRPRICEPHEI'     # header "Fair Price PHEI"
TEMPLATE_NO_HEADER = 'NO'                   # header "No"
PHEI_KEY_COL = 'SERIES'
PHEI_VALUE_COL = 'TODAY FAIR PRICE'
DATE_CELL = (2, 1)                          # A2
PRICE_SCALE_THRESHOLD = 1000                # harga bond normal ~50-150 (% par)
PRICE_SCALE_DIVISOR = 1_000_000_000_000     # sama seperti formula VLOOKUP lama di template
TZ = ZoneInfo("Asia/Jakarta")


# ============================
# FUNGSI PEMBERSIH
# ============================
def norm_header(value):
    """'Instrument\\nCode' -> 'INSTRUMENTCODE'"""
    return re.sub(r'[^A-Z0-9]', '', str(value).upper()) if value is not None else ''


def clean_key(value):
    return re.sub(r'[^A-Z0-9]', '', str(value).strip().upper()) if value is not None else ''


# ============================
# DETEKSI STRUKTUR TEMPLATE
# ============================
def find_position_table(ws):
    """
    Cari tabel 'Current Position': baris header yang memuat 'Fair Price PHEI'.
    Return: (header_row, col_no, col_key, col_value, data_rows)
    data_rows = baris di bawah header selama kolom 'No' berisi angka
    (berhenti otomatis di baris 'Total' / kosong).
    """
    header_row = None
    for r in range(1, ws.max_row + 1):
        if any(norm_header(ws.cell(r, c).value) == TEMPLATE_VALUE_HEADER
               for c in range(1, ws.max_column + 1)):
            header_row = r
            break

    if header_row is None:
        raise ValueError("Header 'Fair Price PHEI' tidak ditemukan di template.")

    cols = {}
    for c in range(1, ws.max_column + 1):
        h = norm_header(ws.cell(header_row, c).value)
        if h in (TEMPLATE_NO_HEADER, TEMPLATE_KEY_HEADER, TEMPLATE_VALUE_HEADER):
            cols[h] = c

    missing = [h for h in (TEMPLATE_NO_HEADER, TEMPLATE_KEY_HEADER, TEMPLATE_VALUE_HEADER)
               if h not in cols]
    if missing:
        raise ValueError(f"Kolom {missing} tidak ditemukan pada baris header {header_row}.")

    data_rows = []
    r = header_row + 1
    while r <= ws.max_row:
        no_val = ws.cell(r, cols[TEMPLATE_NO_HEADER]).value
        if isinstance(no_val, (int, float)):
            data_rows.append(r)
            r += 1
        else:
            break  # 'Total' atau baris kosong

    if not data_rows:
        raise ValueError(f"Tidak ada baris data di bawah header (baris {header_row}).")

    return (header_row, cols[TEMPLATE_NO_HEADER], cols[TEMPLATE_KEY_HEADER],
            cols[TEMPLATE_VALUE_HEADER], data_rows)


# ============================
# BACA FILE PHEI
# ============================
DOTTED_NUMBER = re.compile(r'^\d{1,3}(\.\d{3}){3,}$')   # mis. 102.625.000.000.000


def parse_phei_price(value):
    """
    Format CSV PHEI: titik = pemisah ribuan, nilai dikali 1e12
    ('102.625.000.000.000' -> 102.625). Angka biasa (mis. dari xlsx) dibiarkan.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return float('nan')
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if DOTTED_NUMBER.match(text):
        return int(text.replace('.', '')) / PRICE_SCALE_DIVISOR
    try:
        return float(text.replace(',', '.'))
    except ValueError:
        return float('nan')


def load_phei_lookup(uploaded_file):
    if uploaded_file.name.lower().endswith('.csv'):
        # CSV PHEI memakai ';' sebagai pemisah; dtype=str agar angka tidak rusak
        df = pd.read_csv(uploaded_file, encoding='latin1', sep=None,
                         engine='python', dtype=str)
    else:
        df = pd.read_excel(uploaded_file)

    col_map = {str(c).strip().upper(): c for c in df.columns}
    if PHEI_KEY_COL not in col_map or PHEI_VALUE_COL not in col_map:
        raise ValueError(
            f"Kolom '{PHEI_KEY_COL}' / '{PHEI_VALUE_COL}' tidak ada di file PHEI. "
            f"Kolom yang terbaca: {list(df.columns)}"
        )

    lookup = pd.DataFrame({
        'key': df[col_map[PHEI_KEY_COL]].map(clean_key),
        'price': df[col_map[PHEI_VALUE_COL]].map(parse_phei_price),
    })
    lookup = lookup[lookup['key'] != ''].drop_duplicates(subset='key')
    return dict(zip(lookup['key'], lookup['price']))


# ============================
# FUNGSI PENGOLAHAN DATA UTAMA
# ============================
def process_repo_workbook(repo_bytes, phei_dict):
    wb = load_workbook(BytesIO(repo_bytes))
    ws = wb.active

    header_row, col_no, col_key, col_val, data_rows = find_position_table(ws)

    # Update tanggal (A2)
    today_date = datetime.now(TZ).strftime('%d %b %Y')
    ws.cell(*DATE_CELL, value=f"Daily As of Date : {today_date} - {today_date}")

    result, unmatched, out_of_range, rescaled = [], [], [], 0

    for r in data_rows:
        no_val = ws.cell(r, col_no).value
        raw_code = ws.cell(r, col_key).value
        price = phei_dict.get(clean_key(raw_code))

        if price is None or pd.isna(price):
            price = None
            unmatched.append(str(raw_code))
        else:
            if price > PRICE_SCALE_THRESHOLD:
                price = price / PRICE_SCALE_DIVISOR
                rescaled += 1
            if not (50 <= price <= 150):
                out_of_range.append(f"{raw_code} ({price})")

        ws.cell(r, col_val, value=price)   # menimpa formula VLOOKUP lama dengan nilai
        result.append({'No': int(no_val), 'Instrument Code': raw_code, 'Fair Price PHEI': price})

    out = BytesIO()
    wb.save(out)

    return {
        'df': pd.DataFrame(result),
        'bytes': out.getvalue(),
        'header_row': header_row,
        'unmatched': unmatched,
        'out_of_range': out_of_range,
        'rescaled': rescaled,
    }


# ============================
# MAIN UI
# ============================
def main():
    # Header
    st.markdown("""
    <div class="main-header">
      <h1>🔄 Otomatisasi Repo Bonds Daily Position</h1>
      <p>Mengisi kolom <strong>Fair Price PHEI (J)</strong> dan update tanggal <strong>(A2)</strong> secara otomatis</p>
    </div>
    """, unsafe_allow_html=True)

    # Card: Upload File
    st.markdown('<div class="card"><div class="card-title">Upload File</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        repo_file_upload = st.file_uploader('1. Template Repo', type=['xlsx'])
    with col2:
        phei_lookup_file = st.file_uploader('2. File PHEI Hari Ini', type=['xlsx', 'csv'])
    st.markdown('</div>', unsafe_allow_html=True)

    if repo_file_upload and phei_lookup_file:
        if st.button("▶ Jalankan Proses Update"):
            try:
                phei_dict = load_phei_lookup(phei_lookup_file)
                res = process_repo_workbook(repo_file_upload.getvalue(), phei_dict)
                df_result = res['df']

                st.success(
                    f"✅ Berhasil memproses {len(df_result)} baris data "
                    f"(tabel Current Position, header di baris {res['header_row']})."
                )

                if res['rescaled']:
                    st.info(f"{res['rescaled']} harga dinormalisasi (÷ 1e12) mengikuti formula template lama. Cek preview di bawah.")
                if res['unmatched']:
                    st.warning("Instrument Code tidak ditemukan di file PHEI (kolom J dikosongkan): "
                               + ", ".join(sorted(set(res['unmatched']))))
                if res['out_of_range']:
                    st.warning("Harga di luar kisaran 50–150, mohon dicek: "
                               + ", ".join(res['out_of_range']))

                # Card: Preview
                st.markdown('<div class="card"><div class="card-title">Preview Hasil (Kolom J)</div>', unsafe_allow_html=True)
                st.dataframe(df_result, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

                # Card: Download
                st.markdown('<div class="card"><div class="card-title">Unduh Hasil</div>', unsafe_allow_html=True)
                st.download_button(
                    label="⬇ Unduh File Update",
                    data=res['bytes'],
                    file_name=f"Reverse Repo Bonds Daily Position {datetime.now(TZ).strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
                st.markdown('</div>', unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Terjadi kesalahan: {e}")

    else:
        st.markdown("""
        <div class="card">
          <div class="card-title">Panduan</div>
          <p style="color:#8a8fa8;font-size:0.85rem;margin:0">
            Upload kedua file di atas, lalu klik
            <strong style="color:#5c7cfa">▶ Jalankan Proses Update</strong> untuk memproses.
          </p>
        </div>
        """, unsafe_allow_html=True)

main()
