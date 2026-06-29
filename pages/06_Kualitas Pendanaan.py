import streamlit as st
import pandas as pd
import io
from datetime import date, timedelta
from calendar import monthrange

st.set_page_config(page_title="Rekap SID - Pendanaan & Jaminan", layout="wide")
st.title("Rekap SID, Nama Partisipan, Nilai Pendanaan, Nilai Jaminan, Maturity, Status")
st.caption("Upload file A01 dan F06 (format .txt pipe-delimited) untuk menggabungkan datanya.")
st.caption(
    "ℹ️ Setiap baris hasil = 1 kontrak unik (per SID). Nilai Jaminan otomatis di-SUM hanya untuk agunan "
    "dalam SID yang sama (misal basket saham margin) — kontrak berbeda dengan Nama Partisipan sama "
    "(misal beberapa kontrak REPO) tetap tampil sebagai baris terpisah, tidak tergabung."
)

# ----------------------------------------------------------
# SIDEBAR
# ----------------------------------------------------------
st.sidebar.header("⚙️ Mapping Kolom (ubah jika perlu)")

st.sidebar.markdown("**File A01**")
col_a01_sid     = st.sidebar.number_input("A01 - posisi kolom SID",            min_value=0, value=2)
col_a01_nama    = st.sidebar.number_input("A01 - posisi kolom Nama Partisipan", min_value=0, value=11)
col_a01_jaminan = st.sidebar.number_input("A01 - posisi kolom Nilai Jaminan",   min_value=0, value=16)

st.sidebar.markdown("**File F06**")
col_f06_sid      = st.sidebar.number_input("F06 - posisi kolom SID",                    min_value=0, value=1)
col_f06_pendanaan= st.sidebar.number_input("F06 - posisi kolom Nilai Pendanaan",         min_value=0, value=9)
col_f06_maturity = st.sidebar.number_input("F06 - posisi kolom Maturity",                min_value=0, value=6)
col_f06_kualitas = st.sidebar.number_input("F06 - posisi kolom Kode Kualitas",           min_value=0, value=11)
col_f06_jenis    = st.sidebar.number_input("F06 - posisi kolom Kode Jenis Fasilitas Lain",min_value=0, value=3)

st.sidebar.info("Posisi dihitung mulai dari 0. Kolom A=0, B=1, C=2, ... L=11, Q=16, dst.")

st.sidebar.markdown("---")
st.sidebar.header("📅 Periode Pelaporan")
report_year  = st.sidebar.number_input("Tahun pelaporan", min_value=2000, max_value=2099, value=2022)
report_month = st.sidebar.number_input("Bulan pelaporan (1-12)", min_value=1, max_value=12, value=3)

# Tanggal akhir bulan pelaporan
last_day     = monthrange(report_year, report_month)[1]
report_date  = date(report_year, report_month, last_day)

# ----------------------------------------------------------
# UPLOAD
# ----------------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    file_a01 = st.file_uploader("Upload file A01 (.txt)", type=["txt"], key="a01")
with col2:
    file_f06 = st.file_uploader("Upload file F06 (.txt)", type=["txt"], key="f06")

# ----------------------------------------------------------
# HELPER FUNCTIONS
# ----------------------------------------------------------
def read_pipe_file(uploaded_file):
    content = uploaded_file.read().decode("utf-8", errors="ignore")
    rows = []
    for line in content.splitlines():
        line = line.rstrip("\r\n")
        if not line or line.startswith("H|"):
            continue
        rows.append(line.split("|"))
    return rows

def safe_get(row, idx):
    return row[idx] if idx < len(row) else ""

def parse_number(value):
    if not value:
        return 0.0
    try:
        return float(value.replace(",", "").strip())
    except ValueError:
        return 0.0

def parse_date(value):
    value = value.strip()
    try:
        return pd.to_datetime(value, format="%Y%m%d").date()
    except Exception:
        return None

QUALITY_MAP = {
    "1": "1-Lancar",
    "2": "2-Dalam Perhatian Khusus",
    "3": "3-Kurang Lancar",
    "4": "4-Diragukan",
    "5": "5-Macet",
}

def parse_quality(value):
    value = value.strip()
    return QUALITY_MAP.get(value, value) if value else None

JENIS_FASILITAS_MAP = {
    "001": "001-Kredit Kelolaan",
    "002": "002-Tagihan Akseptasi",
    "003": "003-Kewajiban Kepada Pemerintah",
    "004": "004-Tagihan Transaksi Derivatif",
    "005": "005-REPO (Reverse Repo)",
    "006": "006-Tagihan Pendanaan Non Pembiayaan",
    "007": "007-Transaksi Margin",
    "008": "008-Bai Al Musawamah (Salam)",
    "009": "009-Tagihan Subrogasi",
    "900": "900-Lainnya",
}

def parse_jenis(value):
    value = value.strip()
    return JENIS_FASILITAS_MAP.get(value, value) if value else None

# ----------------------------------------------------------
# KOLEKTIBILITAS: hitung dari hari tunggakan (POJK 40/2019)
# ----------------------------------------------------------
def hitung_kolektibilitas(maturity_date, nilai_pendanaan, report_dt):
    """
    Kualitas berdasarkan hari tunggakan sejak maturity date.
    Kalau belum jatuh tempo atau sudah lunas (nilai=0) → Lancar.
    """
    if nilai_pendanaan <= 0:
        return "Lancar"                          # sudah lunas
    if maturity_date is None:
        return "Lancar"
    if maturity_date >= report_dt:
        return "Lancar"                          # belum jatuh tempo

    hari_tunggak = (report_dt - maturity_date).days
    if hari_tunggak <= 30:
        return "Lancar"
    elif hari_tunggak <= 90:
        return "Dalam Perhatian Khusus"
    elif hari_tunggak <= 120:
        return "Kurang Lancar"
    elif hari_tunggak <= 180:
        return "Diragukan"
    else:
        return "Macet"

# Kolom yang tampil di tabel kolektibilitas (sesuai permintaan)
KOLS_TAMPIL = ["Lancar", "Kurang Lancar", "Macet"]

BULAN_ID = [
    "Januari","Februari","Maret","April","Mei","Juni",
    "Juli","Agustus","September","Oktober","November","Desember"
]

# ----------------------------------------------------------
# MAIN LOGIC
# ----------------------------------------------------------
if file_a01 and file_f06:
    try:
        a01_rows = read_pipe_file(file_a01)
        f06_rows = read_pipe_file(file_f06)

        # ---- A01 ----
        a01_records = []
        for r in a01_rows:
            sid     = safe_get(r, col_a01_sid).strip()
            nama    = safe_get(r, col_a01_nama).strip()
            jaminan = parse_number(safe_get(r, col_a01_jaminan))
            if sid:
                a01_records.append((sid, nama, jaminan))

        df_a01 = pd.DataFrame(a01_records, columns=["SID","Nama Partisipan","Nilai Jaminan"])
        df_a01_grouped = df_a01.groupby("SID", as_index=False).agg(
            {"Nama Partisipan":"first", "Nilai Jaminan":"sum"}
        )

        # ---- F06 ----
        f06_records = []
        for r in f06_rows:
            sid       = safe_get(r, col_f06_sid).strip()
            pendanaan = parse_number(safe_get(r, col_f06_pendanaan))
            maturity  = parse_date(safe_get(r, col_f06_maturity))
            status    = parse_quality(safe_get(r, col_f06_kualitas))
            jenis     = parse_jenis(safe_get(r, col_f06_jenis))
            if sid:
                f06_records.append((sid, pendanaan, maturity, status, jenis))

        df_f06 = pd.DataFrame(f06_records,
                              columns=["SID","Nilai Pendanaan","Maturity","Status","Jenis Transaksi"])

        # ---- Join ----
        result = pd.merge(df_f06, df_a01_grouped, on="SID", how="left")
        result = result[["SID","Nama Partisipan","Jenis Transaksi",
                          "Nilai Pendanaan","Nilai Jaminan","Maturity","Status"]]
        result = result.sort_values(["Nama Partisipan","SID"], na_position="last").reset_index(drop=True)

        # ---- Kolektibilitas (POJK 40/2019) ----
        result["Kolektibilitas"] = result.apply(
            lambda row: hitung_kolektibilitas(row["Maturity"], row["Nilai Pendanaan"], report_date),
            axis=1
        )

        n_missing = result["Nama Partisipan"].isna().sum()
        if n_missing > 0:
            st.warning(f"⚠️ {n_missing} SID dari F06 tidak ditemukan pasangannya di A01.")

        st.success(f"✅ Berhasil! {len(result)} baris dihasilkan. Periode: {report_date.strftime('%d %B %Y')}")

        # ---- Tabel utama ----
        st.subheader("📋 Data Rekap")
        st.dataframe(
            result.style.format({
                "Nilai Pendanaan": "{:,.0f}",
                "Nilai Jaminan":   "{:,.0f}",
            }),
            use_container_width=True,
        )

        # ============================================================
        # TABEL KOLEKTIBILITAS (count nasabah per bulan × kualitas)
        # sesuai format Excel: baris=bulan, kolom=Lancar/KL/Macet
        # ============================================================
        st.subheader("📊 Data Pelaporan Tingkat Kolektibilitas")
        st.caption(
            f"Dihitung otomatis per POJK 40/POJK.03/2019 berdasarkan hari tunggakan sejak Maturity Date. "
            f"Periode aktif ditampilkan: **{BULAN_ID[report_month-1]} {report_year}**"
        )

        # Bangun baris untuk bulan aktif
        kol_counts = result["Kolektibilitas"].value_counts()

        # Tabel: 12 bulan × tahun (kosong kecuali bulan aktif)
        years = sorted({report_year, report_year})   # bisa extend ke multi-tahun
        table_rows = []
        for mo in range(1, 13):
            row_data = {"No": mo, "Bulan": BULAN_ID[mo-1]}
            for yr in years:
                for kol in KOLS_TAMPIL:
                    col_key = f"{yr}_{kol}"
                    if mo == report_month and yr == report_year:
                        # filter hanya nasabah unik (Nama Partisipan)
                        cnt = result[result["Kolektibilitas"] == kol]["Nama Partisipan"].nunique()
                        row_data[col_key] = cnt if cnt > 0 else ""
                    else:
                        row_data[col_key] = ""
            table_rows.append(row_data)

        df_kol = pd.DataFrame(table_rows)
        df_kol = df_kol.set_index(["No","Bulan"])

        # Rename kolom agar rapi
        df_kol.columns = pd.MultiIndex.from_tuples(
            [(str(yr), kol) for yr in years for kol in KOLS_TAMPIL],
            names=["Tahun","Kualitas"]
        )

        st.dataframe(df_kol, use_container_width=True)

        # ---- Export Excel dengan format sesuai gambar ----
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            wb  = writer.book

            # --- Sheet 1: Data rekap ---
            result.to_excel(writer, index=False, sheet_name="Rekap")
            ws_rekap = writer.sheets["Rekap"]
            fmt_num = wb.add_format({"num_format": "#,##0", "align": "right"})
            for col_idx, col_name in enumerate(result.columns):
                if col_name in ("Nilai Pendanaan","Nilai Jaminan"):
                    ws_rekap.set_column(col_idx, col_idx, 20, fmt_num)
                else:
                    ws_rekap.set_column(col_idx, col_idx, 22)

            # --- Sheet 2: Tabel kolektibilitas ---
            ws_kol = wb.add_worksheet("Kolektibilitas")

            # Format styles
            fmt_title   = wb.add_format({"bold":True, "font_size":11})
            fmt_hdr_yr  = wb.add_format({"bold":True, "align":"center", "valign":"vcenter",
                                          "border":1, "bg_color":"#D9E1F2"})
            fmt_hdr_kol = wb.add_format({"bold":True, "align":"center", "valign":"vcenter",
                                          "border":1, "bg_color":"#D9E1F2", "text_wrap":True})
            fmt_hdr_no  = wb.add_format({"bold":True, "align":"center", "valign":"vcenter",
                                          "border":1, "bg_color":"#D9E1F2"})
            fmt_cell    = wb.add_format({"align":"center", "valign":"vcenter", "border":1})
            fmt_bulan   = wb.add_format({"align":"center", "valign":"vcenter", "border":1})
            fmt_num_kol = wb.add_format({"align":"center", "valign":"vcenter", "border":1,
                                          "num_format":"#,##0"})
            fmt_active  = wb.add_format({"align":"center", "valign":"vcenter", "border":1,
                                          "bg_color":"#E2EFDA", "bold":True, "num_format":"#,##0"})

            ws_kol.write(0, 0, "Data Pelaporan Tingkat Kolektibilitas", fmt_title)

            # Header row 1: No | Bulan | [Tahun merged]
            # No=col0, Bulan=col1, then 3 cols per year
            ws_kol.merge_range(1, 0, 2, 0, "No",    fmt_hdr_no)
            ws_kol.merge_range(1, 1, 2, 1, "Bulan", fmt_hdr_no)

            start_col = 2
            for i, yr in enumerate(years):
                end_col = start_col + len(KOLS_TAMPIL) - 1
                ws_kol.merge_range(1, start_col, 1, end_col, str(yr), fmt_hdr_yr)
                for j, kol in enumerate(KOLS_TAMPIL):
                    ws_kol.write(2, start_col + j, kol, fmt_hdr_kol)
                start_col = end_col + 1

            # Set column widths
            ws_kol.set_column(0, 0, 5)   # No
            ws_kol.set_column(1, 1, 12)  # Bulan
            ws_kol.set_column(2, 2 + len(years)*len(KOLS_TAMPIL) - 1, 16)

            ws_kol.set_row(1, 18)
            ws_kol.set_row(2, 30)

            # Data rows (baris 3 dst, 0-indexed)
            for mo_idx, mo in enumerate(range(1, 13)):
                row_excel = 3 + mo_idx
                ws_kol.write(row_excel, 0, mo,               fmt_cell)
                ws_kol.write(row_excel, 1, BULAN_ID[mo-1],   fmt_bulan)
                col_x = 2
                for yr in years:
                    for kol in KOLS_TAMPIL:
                        if mo == report_month and yr == report_year:
                            cnt = result[result["Kolektibilitas"] == kol]["Nama Partisipan"].nunique()
                            val = cnt if cnt > 0 else 0
                            ws_kol.write(row_excel, col_x, val if val else "", fmt_active)
                        else:
                            ws_kol.write(row_excel, col_x, "", fmt_cell)
                        col_x += 1

        buffer.seek(0)
        st.download_button(
            label="⬇️ Download hasil (Excel) — Rekap + Kolektibilitas",
            data=buffer,
            file_name="rekap_slik_kolektibilitas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as e:
        st.error(f"Terjadi error saat memproses file: {e}")
        st.exception(e)
else:
    st.info("⬆️ Silakan upload kedua file A01 dan F06 untuk memulai.")
