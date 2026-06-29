import streamlit as st
import pandas as pd
import io
from datetime import date
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
col_f06_sid       = st.sidebar.number_input("F06 - posisi kolom SID",                     min_value=0, value=1)
col_f06_pendanaan = st.sidebar.number_input("F06 - posisi kolom Nilai Pendanaan",          min_value=0, value=9)
col_f06_maturity  = st.sidebar.number_input("F06 - posisi kolom Maturity",                 min_value=0, value=6)
col_f06_kualitas  = st.sidebar.number_input("F06 - posisi kolom Kode Kualitas",            min_value=0, value=11)
col_f06_jenis     = st.sidebar.number_input("F06 - posisi kolom Kode Jenis Fasilitas Lain",min_value=0, value=3)

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
    try:
        yr       = int(header_cols[3])
        mo       = int(header_cols[4])
        last_day = monthrange(yr, mo)[1]
        return yr, mo, date(yr, mo, last_day)
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

# Kode "Operasi Data" (kolom paling akhir tiap baris detail SLIK):
# - C = Create  -> baris/kontrak baru pertama kali muncul di bulan laporan ini
# - U = Update  -> kontrak sudah dilaporkan di bulan sebelumnya, dilaporkan ulang
#                  (bisa ada perubahan status/kualitas/nilai/maturity, atau tetap sama)
# - D = Delete  -> baris dihapus dari pelaporan (biasanya koreksi atas kesalahan input)
OPERASI_DATA_MAP = {
    "C": "🆕 Baru (Create)",
    "U": "🔄 Update",
    "D": "🗑️ Dihapus (Delete)",
}

def parse_operasi(value):
    value = value.strip().upper()
    return OPERASI_DATA_MAP.get(value, value) if value else None

# ----------------------------------------------------------
# KONSTANTA STYLING DASHBOARD
# ----------------------------------------------------------
BULAN_ID = [
    "Januari","Februari","Maret","April","Mei","Juni",
    "Juli","Agustus","September","Oktober","November","Desember"
]

# Urutan status sesuai QUALITY_MAP
STATUS_ORDER = ["1-Lancar", "2-Dalam Perhatian Khusus", "3-Kurang Lancar", "4-Diragukan", "5-Macet"]

STATUS_STYLE = {
    "1-Lancar":                   {"bg": "#D6F0E6", "fg": "#0F6E56", "icon": "✅"},
    "2-Dalam Perhatian Khusus":   {"bg": "#FEF3CD", "fg": "#856404", "icon": "⚠️"},
    "3-Kurang Lancar":            {"bg": "#FDEBD0", "fg": "#7D3A14", "icon": "🔶"},
    "4-Diragukan":                {"bg": "#FAD7D7", "fg": "#7A1B1A", "icon": "🔴"},
    "5-Macet":                    {"bg": "#F0C0C0", "fg": "#5C0F0F", "icon": "🚫"},
}

BAR_HEX = {
    "1-Lancar":                   "#1baf7a",
    "2-Dalam Perhatian Khusus":   "#eda100",
    "3-Kurang Lancar":            "#eb6834",
    "4-Diragukan":                "#e34948",
    "5-Macet":                    "#a32d2d",
}

STYLE_XL = {
    "1-Lancar":                   "#D6F0E6",
    "2-Dalam Perhatian Khusus":   "#FEF3CD",
    "3-Kurang Lancar":            "#FDEBD0",
    "4-Diragukan":                "#FAD7D7",
    "5-Macet":                    "#F0C0C0",
}

# ----------------------------------------------------------
# MAIN LOGIC
# ----------------------------------------------------------
if file_a01 and file_f06:
    try:
        a01_rows, _          = read_pipe_file(file_a01)
        f06_rows, f06_header = read_pipe_file(file_f06)
        d02_rows, _          = read_pipe_file(file_d02) if file_d02 else ([], [])

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

        # ---- D02 fallback ----
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
            operasi   = parse_operasi(safe_get(r, len(r) - 1))
            if no_fas:
                f06_records.append((no_fas, cif, pendanaan, maturity, status, jenis, operasi))

        df_f06 = pd.DataFrame(f06_records,
                              columns=["SID", "CIF", "Nilai Pendanaan", "Maturity", "Status", "Jenis Transaksi", "Keterangan Operasi Data"])

        # ---- Join ----
        result = pd.merge(df_f06, df_a01_fas, left_on="SID", right_on="fas_key", how="left")
        result = result.drop(columns=["fas_key"], errors="ignore")

        if not df_d02_cif.empty:
            result = pd.merge(result, df_d02_cif, left_on="CIF", right_on="cif_key", how="left")
            result["Nama Partisipan"] = result["Nama Partisipan"].fillna(result["Nama_D02"])
            result = result.drop(columns=["Nama_D02", "cif_key"], errors="ignore")

        result = result.drop(columns=["CIF"], errors="ignore")
        result["Nilai Jaminan"] = result["Nilai Jaminan"].fillna(0)

        result = result[["SID", "Nama Partisipan", "Jenis Transaksi",
                          "Nilai Pendanaan", "Nilai Jaminan", "Maturity", "Status", "Keterangan Operasi Data"]]
        result = result.sort_values(["Nama Partisipan", "SID"], na_position="last").reset_index(drop=True)

        n_missing = result["Nama Partisipan"].isna().sum()
        if n_missing > 0:
            extra = " Coba upload file D02 untuk fallback nama nasabah." if not file_d02 else " Cek kelengkapan data D02."
            st.warning(f"⚠️ {n_missing} fasilitas tidak ditemukan nama nasabahnya di A01/D02.{extra}")

        st.success(f"✅ Berhasil! {len(result)} baris dihasilkan. Periode: {report_date.strftime('%d %B %Y')}")

        # ----------------------------------------------------------
        # DASHBOARD RINGKASAN STATUS (dari kolom Status F06)
        # ----------------------------------------------------------
        st.subheader("🏦 Ringkasan Status Kualitas Kredit")
        st.caption(
            f"Berdasarkan Kode Kualitas pada file F06 · Periode: **{BULAN_ID[report_month-1]} {report_year}** · "
            f"Total kontrak: **{len(result):,}** · Total nasabah unik: **{result['Nama Partisipan'].nunique():,}**"
        )

        status_counts = result["Status"].value_counts()
        total_kontrak = len(result)

        # Kartu metrik per status
        card_cols = st.columns(5)
        for i, st_key in enumerate(STATUS_ORDER):
            count = int(status_counts.get(st_key, 0))
            pct   = (count / total_kontrak * 100) if total_kontrak > 0 else 0
            s     = STATUS_STYLE[st_key]
            label = st_key.split("-", 1)[1]  # strip angka prefix untuk label kartu
            card_cols[i].markdown(
                f"""<div style="background:{s['bg']};border-radius:10px;padding:16px 14px;min-height:110px;">
                    <p style="margin:0 0 4px;font-size:11px;color:{s['fg']};font-weight:600;line-height:1.3;">{s['icon']} {label}</p>
                    <p style="margin:0 0 2px;font-size:30px;font-weight:700;color:{s['fg']};line-height:1.1;">{count:,}</p>
                    <p style="margin:0;font-size:11px;color:{s['fg']};opacity:0.85;">{pct:.1f}% dari {total_kontrak:,} kontrak</p>
                </div>""",
                unsafe_allow_html=True
            )

        # Progress bar proporsi
        st.markdown("<div style='margin-top:14px;margin-bottom:2px;font-size:11px;color:#888;'>Proporsi kontrak</div>",
                    unsafe_allow_html=True)

        bar_html = "<div style='display:flex;height:10px;border-radius:5px;overflow:hidden;gap:2px;'>"
        for st_key in STATUS_ORDER:
            count = int(status_counts.get(st_key, 0))
            pct   = (count / total_kontrak * 100) if total_kontrak > 0 else 0
            if pct > 0:
                label = st_key.split("-", 1)[1]
                bar_html += (
                    f"<div style='width:{pct}%;background:{BAR_HEX[st_key]};border-radius:3px;'"
                    f" title='{label}: {count} ({pct:.1f}%)'></div>"
                )
        bar_html += "</div>"

        legend_html = "<div style='display:flex;flex-wrap:wrap;gap:12px;margin-top:6px;font-size:11px;color:#666;'>"
        for st_key in STATUS_ORDER:
            count = int(status_counts.get(st_key, 0))
            if count > 0:
                label = st_key.split("-", 1)[1]
                legend_html += (
                    f"<span style='display:flex;align-items:center;gap:4px;'>"
                    f"<span style='width:10px;height:10px;border-radius:2px;"
                    f"background:{BAR_HEX[st_key]};display:inline-block;'></span>"
                    f"{label} ({count})</span>"
                )
        legend_html += "</div>"

        st.markdown(bar_html + legend_html, unsafe_allow_html=True)

        # ----------------------------------------------------------
        # RINGKASAN OPERASI DATA (trade adjustment: Create / Update / Delete)
        # ----------------------------------------------------------
        st.markdown("---")
        st.subheader("🔁 Ringkasan Operasi Data (Trade Adjustment)")
        st.caption(
            "Menunjukkan kontrak mana yang baru muncul (Create), sudah ada sebelumnya dan dilaporkan "
            "ulang (Update), atau dihapus dari pelaporan (Delete) pada bulan ini."
        )
        operasi_counts = result["Keterangan Operasi Data"].value_counts()
        op_cols = st.columns(len(OPERASI_DATA_MAP))
        for i, (code, label) in enumerate(OPERASI_DATA_MAP.items()):
            count = int(operasi_counts.get(label, 0))
            op_cols[i].metric(label, f"{count:,}")

        with st.expander("📌 Lihat kontrak yang Baru (Create) atau Dihapus (Delete) bulan ini"):
            mask = result["Keterangan Operasi Data"].isin([OPERASI_DATA_MAP["C"], OPERASI_DATA_MAP["D"]])
            st.dataframe(
                result[mask].style.format({
                    "Nilai Pendanaan": "{:,.0f}",
                    "Nilai Jaminan":   "{:,.0f}",
                }),
                use_container_width=True,
            )

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

        # ---- Export Excel ----
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            wb = writer.book

            # Sheet 1: Data rekap
            result.to_excel(writer, index=False, sheet_name="Rekap")
            ws_rekap = writer.sheets["Rekap"]
            fmt_num = wb.add_format({"num_format": "#,##0", "align": "right"})
            for col_idx, col_name in enumerate(result.columns):
                if col_name in ("Nilai Pendanaan", "Nilai Jaminan"):
                    ws_rekap.set_column(col_idx, col_idx, 20, fmt_num)
                elif col_name == "Keterangan Operasi Data":
                    ws_rekap.set_column(col_idx, col_idx, 20)
                else:
                    ws_rekap.set_column(col_idx, col_idx, 22)

            # Sheet 2: Ringkasan status kualitas
            ws_dash = wb.add_worksheet("Ringkasan Status")
            fmt_title = wb.add_format({"bold": True, "font_size": 12})
            fmt_hdr   = wb.add_format({"bold": True, "align": "center", "valign": "vcenter",
                                        "border": 1, "bg_color": "#D9E1F2", "text_wrap": True})

            ws_dash.write(0, 0, f"Ringkasan Status Kualitas Kredit — {BULAN_ID[report_month-1]} {report_year}", fmt_title)
            ws_dash.write(1, 0, f"Total kontrak: {total_kontrak:,}  |  Total nasabah unik: {result['Nama Partisipan'].nunique():,}")

            headers = ["Status Kualitas", "Jumlah Kontrak", "% Kontrak", "Nasabah Unik"]
            for ci, h in enumerate(headers):
                ws_dash.write(3, ci, h, fmt_hdr)

            ws_dash.set_column(0, 0, 30)
            ws_dash.set_column(1, 3, 16)

            for ri, st_key in enumerate(STATUS_ORDER):
                count_k   = int(status_counts.get(st_key, 0))
                pct_k     = count_k / total_kontrak if total_kontrak > 0 else 0
                nasabah_k = result[result["Status"] == st_key]["Nama Partisipan"].nunique()
                bg        = STYLE_XL.get(st_key, "#FFFFFF")
                fmt_lbl   = wb.add_format({"bold": True, "border": 1, "bg_color": bg})
                fmt_num_k = wb.add_format({"align": "center", "border": 1, "bg_color": bg, "num_format": "#,##0"})
                fmt_pct_k = wb.add_format({"align": "center", "border": 1, "bg_color": bg, "num_format": "0.0%"})
                ws_dash.write(4 + ri, 0, st_key,    fmt_lbl)
                ws_dash.write(4 + ri, 1, count_k,   fmt_num_k)
                ws_dash.write(4 + ri, 2, pct_k,     fmt_pct_k)
                ws_dash.write(4 + ri, 3, nasabah_k, fmt_num_k)

            # Sheet 3: Ringkasan operasi data (create/update/delete)
            ws_op = wb.add_worksheet("Ringkasan Operasi Data")
            ws_op.write(0, 0, f"Ringkasan Operasi Data (Trade Adjustment) — {BULAN_ID[report_month-1]} {report_year}", fmt_title)
            op_headers = ["Operasi Data", "Jumlah Kontrak", "% Kontrak"]
            for ci, h in enumerate(op_headers):
                ws_op.write(2, ci, h, fmt_hdr)
            ws_op.set_column(0, 0, 26)
            ws_op.set_column(1, 2, 16)
            for ri, (code, label) in enumerate(OPERASI_DATA_MAP.items()):
                count_o = int(operasi_counts.get(label, 0))
                pct_o   = count_o / total_kontrak if total_kontrak > 0 else 0
                fmt_num_o = wb.add_format({"align": "center", "border": 1, "num_format": "#,##0"})
                fmt_pct_o = wb.add_format({"align": "center", "border": 1, "num_format": "0.0%"})
                fmt_lbl_o = wb.add_format({"bold": True, "border": 1})
                ws_op.write(3 + ri, 0, label,   fmt_lbl_o)
                ws_op.write(3 + ri, 1, count_o, fmt_num_o)
                ws_op.write(3 + ri, 2, pct_o,   fmt_pct_o)

        buffer.seek(0)
        st.download_button(
            label="⬇️ Download hasil (Excel) — Rekap + Ringkasan Status + Ringkasan Operasi Data",
            data=buffer,
            file_name="rekap_slik.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as e:
        st.error(f"Terjadi error saat memproses file: {e}")
        st.exception(e)
else:
    st.info("⬆️ Silakan upload kedua file A01 dan F06 untuk memulai.")
