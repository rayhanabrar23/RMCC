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
st.sidebar.info("Periode otomatis dibaca dari header file F06 (baris H|). Tidak perlu diisi manual.")

# ----------------------------------------------------------
# UPLOAD
# ----------------------------------------------------------
col1, col2, col3 = st.columns(3)
with col1:
    file_a01 = st.file_uploader("Upload file A01 (.txt)", type=["txt"], key="a01")
with col2:
    file_f06 = st.file_uploader("Upload file F06 (.txt)", type=["txt"], key="f06")
with col3:
    file_d02 = st.file_uploader("Upload file D02 (.txt) — opsional, untuk fallback nama nasabah", type=["txt"], key="d02")

# ----------------------------------------------------------
# HELPER FUNCTIONS
# ----------------------------------------------------------
def read_pipe_file(uploaded_file):
    """Baca file pipe-delimited, skip baris header (diawali 'H|'). Return (rows, header_cols)."""
    content = uploaded_file.read().decode("utf-8", errors="ignore")
    rows = []
    header_cols = []
    for line in content.splitlines():
        line = line.rstrip("\r\n")
        if not line:
            continue
        if line.startswith("H|"):
            header_cols = line.split("|")
            continue
        rows.append(line.split("|"))
    return rows, header_cols

def detect_periode(header_cols):
    """
    Baca tahun & bulan dari header F06.
    Format: H|0402|016357|YYYY|MM|F06|n|n
    index:   0   1      2    3   4   5
    """
    try:
        yr  = int(header_cols[3])
        mo  = int(header_cols[4])
        last_day   = monthrange(yr, mo)[1]
        report_dt  = date(yr, mo, last_day)
        return yr, mo, report_dt
    except Exception:
        return None, None, None

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

# Urutan & styling kartu kolektibilitas
KOL_ORDER = ["Lancar", "Dalam Perhatian Khusus", "Kurang Lancar", "Diragukan", "Macet"]
KOL_STYLE = {
    "Lancar":                   {"bg": "#D6F0E6", "fg": "#0F6E56", "icon": "✅"},
    "Dalam Perhatian Khusus":   {"bg": "#FEF3CD", "fg": "#856404", "icon": "⚠️"},
    "Kurang Lancar":            {"bg": "#FDEBD0", "fg": "#7D3A14", "icon": "🔶"},
    "Diragukan":                {"bg": "#FAD7D7", "fg": "#7A1B1A", "icon": "🔴"},
    "Macet":                    {"bg": "#F0C0C0", "fg": "#5C0F0F", "icon": "🚫"},
}

# ----------------------------------------------------------
# MAIN LOGIC
# ----------------------------------------------------------
if file_a01 and file_f06:
    try:
        a01_rows, _          = read_pipe_file(file_a01)
        f06_rows, f06_header = read_pipe_file(file_f06)
        d02_rows, _          = read_pipe_file(file_d02) if file_d02 else ([], [])

        # Auto-detect periode dari header F06
        report_year, report_month, report_date = detect_periode(f06_header)
        if not report_date:
            st.error("❌ Gagal membaca periode dari header file F06. Pastikan format header: H|kode|inst|YYYY|MM|F06|n|n")
            st.stop()

        # ---- A01 ----
        a01_by_fas = {}
        for r in a01_rows:
            if safe_get(r, 0).strip() != 'D':
                continue
            no_fas  = safe_get(r, 2).strip()
            nama    = safe_get(r, 11).strip()
            jaminan = parse_number(safe_get(r, 15))
            if no_fas:
                if no_fas not in a01_by_fas:
                    a01_by_fas[no_fas] = [nama, 0.0]
                a01_by_fas[no_fas][1] += jaminan

        df_a01_fas = pd.DataFrame(
            [(k, v[0], v[1]) for k, v in a01_by_fas.items()],
            columns=["fas_key", "Nama Partisipan", "Nilai Jaminan"]
        ) if a01_by_fas else pd.DataFrame(columns=["fas_key", "Nama Partisipan", "Nilai Jaminan"])

        # ---- D02 (fallback nama nasabah via CIF) ----
        d02_by_cif = {}
        for r in d02_rows:
            if safe_get(r, 0).strip() != 'D':
                continue
            cif  = safe_get(r, 1).strip()
            nama = safe_get(r, 3).strip()
            if cif and nama:
                d02_by_cif[cif] = nama

        df_d02_cif = pd.DataFrame(
            [(k, v) for k, v in d02_by_cif.items()],
            columns=["cif_key", "Nama_D02"]
        ) if d02_by_cif else pd.DataFrame(columns=["cif_key", "Nama_D02"])

        # ---- F06 ----
        f06_records = []
        for r in f06_rows:
            no_fas    = safe_get(r, col_f06_sid).strip()
            cif       = safe_get(r, 2).strip()
            pendanaan = parse_number(safe_get(r, col_f06_pendanaan))
            maturity  = parse_date(safe_get(r, col_f06_maturity))
            status    = parse_quality(safe_get(r, col_f06_kualitas))
            jenis     = parse_jenis(safe_get(r, col_f06_jenis))
            if no_fas:
                f06_records.append((no_fas, cif, pendanaan, maturity, status, jenis))

        df_f06 = pd.DataFrame(f06_records,
                              columns=["SID", "CIF", "Nilai Pendanaan", "Maturity", "Status", "Jenis Transaksi"])

        # ---- Join 1: via No.Fasilitas ----
        result = pd.merge(df_f06, df_a01_fas, left_on="SID", right_on="fas_key", how="left")
        result = result.drop(columns=["fas_key"], errors="ignore")

        # ---- Join 2: via CIF (fallback D02) ----
        if not df_d02_cif.empty:
            result = pd.merge(result, df_d02_cif, left_on="CIF", right_on="cif_key", how="left")
            result["Nama Partisipan"] = result["Nama Partisipan"].fillna(result["Nama_D02"])
            result = result.drop(columns=["Nama_D02", "cif_key"], errors="ignore")

        result = result.drop(columns=["CIF"], errors="ignore")
        result["Nilai Jaminan"] = result["Nilai Jaminan"].fillna(0)

        result = result[["SID", "Nama Partisipan", "Jenis Transaksi",
                          "Nilai Pendanaan", "Nilai Jaminan", "Maturity", "Status"]]
        result = result.sort_values(["Nama Partisipan", "SID"], na_position="last").reset_index(drop=True)

        # ---- Kolektibilitas (POJK 40/2019) ----
        result["Kolektibilitas"] = result.apply(
            lambda row: hitung_kolektibilitas(row["Maturity"], row["Nilai Pendanaan"], report_date),
            axis=1
        )

        n_missing = result["Nama Partisipan"].isna().sum()
        if n_missing > 0:
            extra = " Coba upload file D02 untuk fallback nama nasabah." if not file_d02 else " Cek kelengkapan data D02."
            st.warning(f"⚠️ {n_missing} fasilitas tidak ditemukan nama nasabahnya di A01/D02.{extra}")

        st.success(f"✅ Berhasil! {len(result)} baris dihasilkan. Periode: {report_date.strftime('%d %B %Y')}")

        # ----------------------------------------------------------
        # DASHBOARD RINGKASAN KOLEKTIBILITAS
        # ----------------------------------------------------------
        st.subheader("🏦 Ringkasan Kolektibilitas")
        st.caption(
            f"Berdasarkan POJK 40/POJK.03/2019 · Periode: **{BULAN_ID[report_month-1]} {report_year}** · "
            f"Total kontrak: **{len(result):,}** · Total nasabah unik: **{result['Nama Partisipan'].nunique():,}**"
        )

        kol_counts_raw = result["Kolektibilitas"].value_counts()
        total_kontrak  = len(result)

        # Baris kartu metrik (5 kategori)
        card_cols = st.columns(5)
        for i, kol in enumerate(KOL_ORDER):
            count = int(kol_counts_raw.get(kol, 0))
            pct   = (count / total_kontrak * 100) if total_kontrak > 0 else 0
            s     = KOL_STYLE[kol]
            card_cols[i].markdown(
                f"""<div style="background:{s['bg']};border-radius:10px;padding:16px 14px;min-height:110px;">
                    <p style="margin:0 0 4px;font-size:11px;color:{s['fg']};font-weight:600;line-height:1.3;">{s['icon']} {kol}</p>
                    <p style="margin:0 0 2px;font-size:30px;font-weight:700;color:{s['fg']};line-height:1.1;">{count:,}</p>
                    <p style="margin:0;font-size:11px;color:{s['fg']};opacity:0.85;">{pct:.1f}% dari {total_kontrak:,} kontrak</p>
                </div>""",
                unsafe_allow_html=True
            )

        # Progress bar visual proporsi
        st.markdown("<div style='margin-top:14px;margin-bottom:2px;font-size:11px;color:#888;'>Proporsi kontrak</div>", unsafe_allow_html=True)
        bar_colors = {k: v["bg"].replace("D6","1b").replace("FEF","eda").replace("FDE","eb6").replace("FAD","e34").replace("F0C","a32") for k, v in KOL_STYLE.items()}
        BAR_HEX = {
            "Lancar":                   "#1baf7a",
            "Dalam Perhatian Khusus":   "#eda100",
            "Kurang Lancar":            "#eb6834",
            "Diragukan":                "#e34948",
            "Macet":                    "#a32d2d",
        }
        bar_html = "<div style='display:flex;height:10px;border-radius:5px;overflow:hidden;gap:2px;'>"
        for kol in KOL_ORDER:
            count = int(kol_counts_raw.get(kol, 0))
            pct   = (count / total_kontrak * 100) if total_kontrak > 0 else 0
            if pct > 0:
                bar_html += f"<div style='width:{pct}%;background:{BAR_HEX[kol]};border-radius:3px;' title='{kol}: {count} ({pct:.1f}%)'></div>"
        bar_html += "</div>"

        legend_html = "<div style='display:flex;flex-wrap:wrap;gap:12px;margin-top:6px;font-size:11px;color:#666;'>"
        for kol in KOL_ORDER:
            count = int(kol_counts_raw.get(kol, 0))
            if count > 0:
                legend_html += (
                    f"<span style='display:flex;align-items:center;gap:4px;'>"
                    f"<span style='width:10px;height:10px;border-radius:2px;background:{BAR_HEX[kol]};display:inline-block;'></span>"
                    f"{kol} ({count})</span>"
                )
        legend_html += "</div>"

        st.markdown(bar_html + legend_html, unsafe_allow_html=True)
        st.markdown("---")

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
        # ============================================================
        st.subheader("📊 Data Pelaporan Tingkat Kolektibilitas")
        st.caption(
            f"Dihitung otomatis per POJK 40/POJK.03/2019 berdasarkan hari tunggakan sejak Maturity Date. "
            f"Periode aktif ditampilkan: **{BULAN_ID[report_month-1]} {report_year}**"
        )

        kol_counts = result["Kolektibilitas"].value_counts()

        years = sorted({report_year, report_year})
        table_rows = []
        for mo in range(1, 13):
            row_data = {"No": mo, "Bulan": BULAN_ID[mo-1]}
            for yr in years:
                for kol in KOLS_TAMPIL:
                    col_key = f"{yr}_{kol}"
                    if mo == report_month and yr == report_year:
                        cnt = result[result["Kolektibilitas"] == kol]["Nama Partisipan"].nunique()
                        row_data[col_key] = cnt if cnt > 0 else ""
                    else:
                        row_data[col_key] = ""
            table_rows.append(row_data)

        df_kol = pd.DataFrame(table_rows)
        df_kol = df_kol.set_index(["No","Bulan"])

        df_kol.columns = pd.MultiIndex.from_tuples(
            [(str(yr), kol) for yr in years for kol in KOLS_TAMPIL],
            names=["Tahun","Kualitas"]
        )

        st.dataframe(df_kol, use_container_width=True)

        # ---- Export Excel ----
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            wb  = writer.book

            # Sheet 1: Data rekap
            result.to_excel(writer, index=False, sheet_name="Rekap")
            ws_rekap = writer.sheets["Rekap"]
            fmt_num = wb.add_format({"num_format": "#,##0", "align": "right"})
            for col_idx, col_name in enumerate(result.columns):
                if col_name in ("Nilai Pendanaan","Nilai Jaminan"):
                    ws_rekap.set_column(col_idx, col_idx, 20, fmt_num)
                else:
                    ws_rekap.set_column(col_idx, col_idx, 22)

            # Sheet 2: Ringkasan kolektibilitas (dashboard)
            ws_dash = wb.add_worksheet("Ringkasan Kolektibilitas")
            fmt_title   = wb.add_format({"bold": True, "font_size": 12})
            fmt_hdr     = wb.add_format({"bold": True, "align": "center", "valign": "vcenter",
                                          "border": 1, "bg_color": "#D9E1F2", "text_wrap": True})
            fmt_center  = wb.add_format({"align": "center", "valign": "vcenter", "border": 1})
            fmt_num_ctr = wb.add_format({"align": "center", "valign": "vcenter", "border": 1, "num_format": "#,##0"})
            fmt_pct     = wb.add_format({"align": "center", "valign": "vcenter", "border": 1, "num_format": "0.0%"})

            STYLE_XL = {
                "Lancar":                   "#D6F0E6",
                "Dalam Perhatian Khusus":   "#FEF3CD",
                "Kurang Lancar":            "#FDEBD0",
                "Diragukan":               "#FAD7D7",
                "Macet":                    "#F0C0C0",
            }

            ws_dash.write(0, 0, f"Ringkasan Kolektibilitas — {BULAN_ID[report_month-1]} {report_year}", fmt_title)
            ws_dash.write(1, 0, f"Total kontrak: {total_kontrak:,}  |  Total nasabah unik: {result['Nama Partisipan'].nunique():,}")

            headers = ["Kategori Kolektibilitas", "Jumlah Kontrak", "% Kontrak", "Nasabah Unik"]
            for ci, h in enumerate(headers):
                ws_dash.write(3, ci, h, fmt_hdr)

            ws_dash.set_column(0, 0, 28)
            ws_dash.set_column(1, 3, 16)

            for ri, kol in enumerate(KOL_ORDER):
                count_k  = int(kol_counts_raw.get(kol, 0))
                pct_k    = count_k / total_kontrak if total_kontrak > 0 else 0
                nasabah_k = result[result["Kolektibilitas"] == kol]["Nama Partisipan"].nunique()
                bg = STYLE_XL.get(kol, "#FFFFFF")
                fmt_kol_lbl = wb.add_format({"bold": True, "border": 1, "bg_color": bg})
                fmt_kol_num = wb.add_format({"align": "center", "border": 1, "bg_color": bg, "num_format": "#,##0"})
                fmt_kol_pct = wb.add_format({"align": "center", "border": 1, "bg_color": bg, "num_format": "0.0%"})
                ws_dash.write(4 + ri, 0, kol,       fmt_kol_lbl)
                ws_dash.write(4 + ri, 1, count_k,   fmt_kol_num)
                ws_dash.write(4 + ri, 2, pct_k,     fmt_kol_pct)
                ws_dash.write(4 + ri, 3, nasabah_k, fmt_kol_num)

            # Sheet 3: Tabel kolektibilitas bulanan
            ws_kol = wb.add_worksheet("Kolektibilitas")

            fmt_title2  = wb.add_format({"bold":True, "font_size":11})
            fmt_hdr_yr  = wb.add_format({"bold":True, "align":"center", "valign":"vcenter",
                                          "border":1, "bg_color":"#D9E1F2"})
            fmt_hdr_kol = wb.add_format({"bold":True, "align":"center", "valign":"vcenter",
                                          "border":1, "bg_color":"#D9E1F2", "text_wrap":True})
            fmt_hdr_no  = wb.add_format({"bold":True, "align":"center", "valign":"vcenter",
                                          "border":1, "bg_color":"#D9E1F2"})
            fmt_cell    = wb.add_format({"align":"center", "valign":"vcenter", "border":1})
            fmt_bulan   = wb.add_format({"align":"center", "valign":"vcenter", "border":1})
            fmt_active  = wb.add_format({"align":"center", "valign":"vcenter", "border":1,
                                          "bg_color":"#E2EFDA", "bold":True, "num_format":"#,##0"})

            ws_kol.write(0, 0, "Data Pelaporan Tingkat Kolektibilitas", fmt_title2)
            ws_kol.merge_range(1, 0, 2, 0, "No",    fmt_hdr_no)
            ws_kol.merge_range(1, 1, 2, 1, "Bulan", fmt_hdr_no)

            start_col = 2
            for i, yr in enumerate(years):
                end_col = start_col + len(KOLS_TAMPIL) - 1
                ws_kol.merge_range(1, start_col, 1, end_col, str(yr), fmt_hdr_yr)
                for j, kol in enumerate(KOLS_TAMPIL):
                    ws_kol.write(2, start_col + j, kol, fmt_hdr_kol)
                start_col = end_col + 1

            ws_kol.set_column(0, 0, 5)
            ws_kol.set_column(1, 1, 12)
            ws_kol.set_column(2, 2 + len(years)*len(KOLS_TAMPIL) - 1, 16)
            ws_kol.set_row(1, 18)
            ws_kol.set_row(2, 30)

            for mo_idx, mo in enumerate(range(1, 13)):
                row_excel = 3 + mo_idx
                ws_kol.write(row_excel, 0, mo,               fmt_cell)
                ws_kol.write(row_excel, 1, BULAN_ID[mo-1],   fmt_bulan)
                col_x = 2
                for yr in years:
                    for kol in KOLS_TAMPIL:
                        if mo == report_month and yr == report_year:
                            cnt = result[result["Kolektibilitas"] == kol]["Nama Partisipan"].nunique()
                            ws_kol.write(row_excel, col_x, cnt if cnt else "", fmt_active)
                        else:
                            ws_kol.write(row_excel, col_x, "", fmt_cell)
                        col_x += 1

        buffer.seek(0)
        st.download_button(
            label="⬇️ Download hasil (Excel) — Rekap + Ringkasan + Kolektibilitas",
            data=buffer,
            file_name="rekap_slik_kolektibilitas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as e:
        st.error(f"Terjadi error saat memproses file: {e}")
        st.exception(e)
else:
    st.info("⬆️ Silakan upload kedua file A01 dan F06 untuk memulai.")
