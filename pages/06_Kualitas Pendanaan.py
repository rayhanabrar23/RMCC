import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Rekap SID - Pendanaan & Jaminan", layout="wide")
st.title("Rekap SID, Nama Partisipan, Nilai Pendanaan, Nilai Jaminan, Maturity, Status")
st.caption("Upload file A01 dan F06 (format .txt pipe-delimited) untuk menggabungkan datanya.")
st.caption("ℹ️ Setiap baris hasil = 1 kontrak unik (per SID). Nilai Jaminan otomatis di-SUM hanya untuk agunan dalam SID yang sama (misal basket saham margin) — kontrak berbeda dengan Nama Partisipan sama (misal beberapa kontrak REPO) tetap tampil sebagai baris terpisah, tidak tergabung.")

# ----------------------------------------------------------
# SIDEBAR: Mapping posisi kolom (0-based, setelah split('|'))
# Default sudah disesuaikan berdasarkan contoh data riil.
# ----------------------------------------------------------
st.sidebar.header("⚙️ Mapping Kolom (ubah jika perlu)")

st.sidebar.markdown("**File A01**")
col_a01_sid = st.sidebar.number_input("A01 - posisi kolom SID", min_value=0, value=2, help="0 = kolom A, 1 = kolom B, 2 = kolom C, dst.")
col_a01_nama = st.sidebar.number_input("A01 - posisi kolom Nama Partisipan", min_value=0, value=11, help="11 = kolom L")
col_a01_jaminan = st.sidebar.number_input("A01 - posisi kolom Nilai Jaminan", min_value=0, value=16, help="16 = kolom Q")

st.sidebar.markdown("**File F06**")
col_f06_sid = st.sidebar.number_input("F06 - posisi kolom SID", min_value=0, value=1, help="1 = kolom B")
col_f06_pendanaan = st.sidebar.number_input("F06 - posisi kolom Nilai Pendanaan", min_value=0, value=9, help="9 = kolom J (cek ulang jika beda file)")
col_f06_maturity = st.sidebar.number_input("F06 - posisi kolom Maturity", min_value=0, value=6, help="6 = kolom G (cek ulang jika beda file)")
col_f06_kualitas = st.sidebar.number_input("F06 - posisi kolom Kode Kualitas", min_value=0, value=11, help="11 = kolom L (Status Lancar/Macet)")
col_f06_jenis = st.sidebar.number_input("F06 - posisi kolom Kode Jenis Fasilitas Lain", min_value=0, value=3, help="3 = kolom D (005=Repo, 007=Margin, dst)")

st.sidebar.info("Posisi dihitung mulai dari 0. Kolom A = 0, B = 1, C = 2, ... L = 11, Q = 16, dst.")

# ----------------------------------------------------------
# UPLOAD FILES
# ----------------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    file_a01 = st.file_uploader("Upload file A01 (.txt)", type=["txt"], key="a01")
with col2:
    file_f06 = st.file_uploader("Upload file F06 (.txt)", type=["txt"], key="f06")


def read_pipe_file(uploaded_file):
    """Baca file pipe-delimited, skip baris header (diawali 'H|')."""
    content = uploaded_file.read().decode("utf-8", errors="ignore")
    rows = []
    for line in content.splitlines():
        line = line.rstrip("\n").rstrip("\r")
        if not line or line.startswith("H|"):
            continue
        rows.append(line.split("|"))
    return rows


def safe_get(row, idx):
    if idx < len(row):
        return row[idx]
    return ""


def parse_number(value):
    if value is None or value == "":
        return 0.0
    value = value.replace(",", "").strip()
    try:
        return float(value)
    except ValueError:
        return 0.0


def parse_date(value):
    value = value.strip()
    try:
        return pd.to_datetime(value, format="%Y%m%d").date()
    except Exception:
        return value if value else None


QUALITY_MAP = {
    "1": "1-Lancar",
    "2": "2-Dalam Perhatian Khusus",
    "3": "3-Kurang Lancar",
    "4": "4-Diragukan",
    "5": "5-Macet",
}


def parse_quality(value):
    value = value.strip()
    if not value:
        return None
    return QUALITY_MAP.get(value, value)


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
    if not value:
        return None
    return JENIS_FASILITAS_MAP.get(value, value)


if file_a01 and file_f06:
    try:
        a01_rows = read_pipe_file(file_a01)
        f06_rows = read_pipe_file(file_f06)

        # ---- Proses A01: SID, Nama Partisipan, Nilai Jaminan (sum per SID) ----
        a01_records = []
        for r in a01_rows:
            sid = safe_get(r, col_a01_sid).strip()
            nama = safe_get(r, col_a01_nama).strip()
            jaminan = parse_number(safe_get(r, col_a01_jaminan))
            if sid:
                a01_records.append((sid, nama, jaminan))

        df_a01 = pd.DataFrame(a01_records, columns=["SID", "Nama Partisipan", "Nilai Jaminan"])
        df_a01_grouped = df_a01.groupby("SID", as_index=False).agg({
            "Nama Partisipan": "first",
            "Nilai Jaminan": "sum",
        })

        # ---- Proses F06: SID, Nilai Pendanaan, Maturity, Status Kualitas, Jenis Transaksi ----
        f06_records = []
        for r in f06_rows:
            sid = safe_get(r, col_f06_sid).strip()
            pendanaan = parse_number(safe_get(r, col_f06_pendanaan))
            maturity = parse_date(safe_get(r, col_f06_maturity))
            status = parse_quality(safe_get(r, col_f06_kualitas))
            jenis = parse_jenis(safe_get(r, col_f06_jenis))
            if sid:
                f06_records.append((sid, pendanaan, maturity, status, jenis))

        df_f06 = pd.DataFrame(f06_records, columns=["SID", "Nilai Pendanaan", "Maturity", "Status", "Jenis Transaksi"])

        # ---- Gabungkan ----
        result = pd.merge(df_f06, df_a01_grouped, on="SID", how="left")
        result = result[["SID", "Nama Partisipan", "Jenis Transaksi", "Nilai Pendanaan", "Nilai Jaminan", "Maturity", "Status"]]
        result = result.sort_values(["Nama Partisipan", "SID"], na_position="last").reset_index(drop=True)

        n_missing = result["Nama Partisipan"].isna().sum()
        if n_missing > 0:
            st.warning(f"⚠️ {n_missing} SID dari F06 tidak ditemukan pasangannya di A01.")

        st.success(f"✅ Berhasil! {len(result)} baris dihasilkan.")
        st.dataframe(
            result.style.format({
                "Nilai Pendanaan": "{:,.0f}",
                "Nilai Jaminan": "{:,.0f}",
            }),
            use_container_width=True,
        )

        # ---- Download hasil sebagai Excel ----
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            result.to_excel(writer, index=False, sheet_name="Rekap")
        buffer.seek(0)

        st.download_button(
            label="⬇️ Download hasil (Excel)",
            data=buffer,
            file_name="rekap_sid.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as e:
        st.error(f"Terjadi error saat memproses file: {e}")
        st.exception(e)
else:
    st.info("⬆️ Silakan upload kedua file A01 dan F06 untuk memulai.")
