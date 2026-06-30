import streamlit as st
import pandas as pd
import io
import copy
from datetime import date
from calendar import monthrange
import openpyxl
from openpyxl.utils import get_column_letter

st.set_page_config(page_title="Rekap SID - Isi Template Excel", layout="wide")
st.title("Rekap SID, Nama Partisipan, Nilai Pendanaan, Nilai Jaminan, Maturity, Status")
st.caption(
    "Versi ini langsung mengisi ke **template Excel asli** kamu (format, font, kolom hidden "
    "F/H/K, border, lebar kolom — semua persis sama). Hasilnya tinggal di-export ke PDF."
)
st.caption(
    "ℹ️ Setiap baris hasil = 1 kontrak unik (per SID). Nilai Jaminan otomatis di-SUM hanya untuk "
    "agunan dalam SID yang sama (misal basket saham margin) — kontrak berbeda dengan Nama "
    "Partisipan sama (misal beberapa kontrak REPO) tetap tampil sebagai baris terpisah."
)

TEMPLATE_PATH = "template.xlsx"  # taruh file template di folder yang sama dengan app ini

# ----------------------------------------------------------
# SIDEBAR - mapping kolom
# ----------------------------------------------------------
st.sidebar.header("⚙️ Mapping Kolom (ubah jika perlu)")
st.sidebar.markdown("**File A01**")
col_a01_no_fas  = st.sidebar.number_input("A01 - posisi kolom No Fasilitas (SID)", min_value=0, value=2)
col_a01_nama    = st.sidebar.number_input("A01 - posisi kolom Nama Partisipan",    min_value=0, value=11)
col_a01_jaminan = st.sidebar.number_input("A01 - posisi kolom Nilai Jaminan",      min_value=0, value=15)

st.sidebar.markdown("**File F06**")
col_f06_sid       = st.sidebar.number_input("F06 - posisi kolom SID",                      min_value=0, value=1)
col_f06_cif       = st.sidebar.number_input("F06 - posisi kolom CIF",                      min_value=0, value=2)
col_f06_pendanaan = st.sidebar.number_input("F06 - posisi kolom Nilai Pendanaan",           min_value=0, value=9)
col_f06_maturity  = st.sidebar.number_input("F06 - posisi kolom Maturity",                  min_value=0, value=6)
col_f06_jenis     = st.sidebar.number_input("F06 - posisi kolom Kode Jenis Fasilitas Lain", min_value=0, value=3)

st.sidebar.markdown("**D02 (opsional, fallback nama)**")
col_d02_cif  = st.sidebar.number_input("D02 - posisi kolom CIF",  min_value=0, value=1)
col_d02_nama = st.sidebar.number_input("D02 - posisi kolom Nama", min_value=0, value=3)

st.sidebar.info("Posisi dihitung mulai dari 0. Kolom A=0, B=1, C=2, ... L=11, dst.")

# ----------------------------------------------------------
# Mapping jenis fasilitas -> label kolom B di template
# ----------------------------------------------------------
JENIS_TO_LABEL = {
    "005": "Pendanaan Transaksi REPO",
    "007": "Pendanaan Transaksi Marjin",
}
JENIS_RAW_LABEL = {
    "001": "Pendanaan Kredit Kelolaan",
    "002": "Pendanaan Tagihan Akseptasi",
    "003": "Pendanaan Kewajiban Kepada Pemerintah",
    "004": "Pendanaan Tagihan Transaksi Derivatif",
    "005": "Pendanaan Transaksi REPO",
    "006": "Pendanaan Tagihan Non Pembiayaan",
    "007": "Pendanaan Transaksi Marjin",
    "008": "Pendanaan Bai Al Musawamah (Salam)",
    "009": "Pendanaan Tagihan Subrogasi",
    "900": "Pendanaan Lainnya",
}

def label_jenis(code):
    code = (code or "").strip()
    return JENIS_TO_LABEL.get(code, JENIS_RAW_LABEL.get(code, f"Pendanaan Lainnya ({code})"))

# ----------------------------------------------------------
# HELPER PARSING (sama seperti versi sebelumnya)
# ----------------------------------------------------------
def read_pipe_file(uploaded_file):
    content = uploaded_file.read().decode("utf-8", errors="ignore")
    rows, header_cols = [], []
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
        yr = int(header_cols[3]); mo = int(header_cols[4])
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
    value = (value or "").strip()
    try:
        return pd.to_datetime(value, format="%Y%m%d").date()
    except Exception:
        return None

# ----------------------------------------------------------
# UPLOAD MULTI-BATCH
# ----------------------------------------------------------
st.subheader("📁 Upload Batch Data")
st.caption(
    "Upload **lebih dari satu set file** sekaligus (misalnya 1 set untuk data Margin, 1 set lagi "
    "untuk data REPO Bonds). Urutan file A01 dan F06 akan dipasangkan berdasarkan urutan upload "
    "(file A01 ke-1 dipasangkan dengan file F06 ke-1, dst). Boleh upload >3 file sekaligus."
)

col1, col2, col3 = st.columns(3)
with col1:
    files_a01 = st.file_uploader("Upload semua file A01 (.txt)", type=["txt"], key="a01", accept_multiple_files=True)
with col2:
    files_f06 = st.file_uploader("Upload semua file F06 (.txt)", type=["txt"], key="f06", accept_multiple_files=True)
with col3:
    files_d02 = st.file_uploader("Upload file D02 (.txt) — opsional, fallback nama", type=["txt"], key="d02", accept_multiple_files=True)

st.markdown("---")
periode_override = st.checkbox("Override periode pelaporan manual (jika header F06 tidak terbaca / beda bulan antar file)")
if periode_override:
    c1, c2 = st.columns(2)
    with c1:
        yr_in = st.number_input("Tahun", min_value=2000, max_value=2100, value=date.today().year)
    with c2:
        mo_in = st.number_input("Bulan", min_value=1, max_value=12, value=date.today().month)

# ----------------------------------------------------------
# PROCESS
# ----------------------------------------------------------
if files_a01 and files_f06:
    if len(files_a01) != len(files_f06):
        st.error(f"❌ Jumlah file A01 ({len(files_a01)}) dan F06 ({len(files_f06)}) tidak sama. "
                 f"Setiap batch harus punya pasangan A01 + F06.")
        st.stop()

    try:
        # ---- D02 fallback (gabungan semua file D02) ----
        d02_by_cif = {}
        for f in (files_d02 or []):
            rows, _ = read_pipe_file(f)
            for r in rows:
                if safe_get(r, 0).strip() != 'D':
                    continue
                cif  = safe_get(r, col_d02_cif).strip()
                nama = safe_get(r, col_d02_nama).strip()
                if cif and nama:
                    d02_by_cif[cif] = nama

        all_results = []
        detected_periods = []

        for i, (fa01, ff06) in enumerate(zip(files_a01, files_f06), start=1):
            a01_rows, _ = read_pipe_file(fa01)
            f06_rows, f06_header = read_pipe_file(ff06)

            yr, mo, rdate = detect_periode(f06_header)
            if rdate:
                detected_periods.append((yr, mo))

            # A01 -> jaminan per no fasilitas (SUM dalam SID yang sama)
            a01_by_fas = {}
            for r in a01_rows:
                if safe_get(r, 0).strip() != 'D':
                    continue
                no_fas  = safe_get(r, col_a01_no_fas).strip()
                nama    = safe_get(r, col_a01_nama).strip()
                jaminan = parse_number(safe_get(r, col_a01_jaminan))
                if no_fas:
                    if no_fas not in a01_by_fas:
                        a01_by_fas[no_fas] = [nama, 0.0]
                    a01_by_fas[no_fas][1] += jaminan

            df_a01_fas = pd.DataFrame(
                [(k, v[0], v[1]) for k, v in a01_by_fas.items()],
                columns=["fas_key", "Nama Partisipan", "Nilai Jaminan"]
            ) if a01_by_fas else pd.DataFrame(columns=["fas_key", "Nama Partisipan", "Nilai Jaminan"])

            # F06
            f06_records = []
            for r in f06_rows:
                no_fas    = safe_get(r, col_f06_sid).strip()
                cif       = safe_get(r, col_f06_cif).strip()
                pendanaan = parse_number(safe_get(r, col_f06_pendanaan))
                maturity  = parse_date(safe_get(r, col_f06_maturity))
                jenis     = safe_get(r, col_f06_jenis).strip()
                if no_fas:
                    f06_records.append((no_fas, cif, pendanaan, maturity, jenis))

            df_f06 = pd.DataFrame(
                f06_records,
                columns=["SID", "CIF", "Nilai Pendanaan", "Maturity", "Kode Jenis"]
            )
            if df_f06.empty:
                st.warning(f"⚠️ Batch #{i}: file F06 ({ff06.name}) tidak menghasilkan baris data.")
                continue

            df_f06["Tipe Pendanaan"] = df_f06["Kode Jenis"].apply(label_jenis)

            result = pd.merge(df_f06, df_a01_fas, left_on="SID", right_on="fas_key", how="left")
            result = result.drop(columns=["fas_key"], errors="ignore")

            if d02_by_cif:
                result["Nama_D02"] = result["CIF"].map(d02_by_cif)
                result["Nama Partisipan"] = result["Nama Partisipan"].fillna(result["Nama_D02"])
                result = result.drop(columns=["Nama_D02"], errors="ignore")

            result["Nilai Jaminan"] = result["Nilai Jaminan"].fillna(0)
            result["Batch"] = f"{fa01.name} + {ff06.name}"
            all_results.append(result)

        if not all_results:
            st.error("❌ Tidak ada data valid dari batch manapun.")
            st.stop()

        final = pd.concat(all_results, ignore_index=True)

        # ---- Tentukan periode laporan ----
        if periode_override:
            report_year, report_month = int(yr_in), int(mo_in)
        elif detected_periods:
            report_year, report_month = detected_periods[0]
            if len(set(detected_periods)) > 1:
                st.warning(
                    "⚠️ Header F06 antar batch menunjukkan periode bulan/tahun yang berbeda-beda. "
                    "Memakai periode dari batch pertama. Centang 'Override periode pelaporan manual' "
                    "di atas jika ingin set manual."
                )
        else:
            st.error("❌ Gagal membaca periode dari header F06 di semua batch, dan override manual tidak dicentang.")
            st.stop()

        last_day = monthrange(report_year, report_month)[1]
        report_date = date(report_year, report_month, last_day)

        n_missing = final["Nama Partisipan"].isna().sum()
        if n_missing > 0:
            st.warning(f"⚠️ {n_missing} fasilitas tidak ditemukan nama nasabahnya di A01/D02.")

        final = final[["Tipe Pendanaan", "Nama Partisipan", "Nilai Pendanaan", "Nilai Jaminan", "Maturity", "Batch"]]
        final = final.sort_values(["Tipe Pendanaan", "Nama Partisipan"], na_position="last").reset_index(drop=True)

        st.success(
            f"✅ Berhasil! {len(final)} baris dari {len(all_results)} batch digabung. "
            f"Periode: {report_date.strftime('%d %B %Y')}"
        )

        st.subheader("📋 Preview Data Gabungan (sebelum dimasukkan ke template)")
        st.dataframe(
            final.style.format({"Nilai Pendanaan": "{:,.0f}", "Nilai Jaminan": "{:,.0f}"}),
            use_container_width=True,
        )

        # ----------------------------------------------------------
        # ISI KE TEMPLATE EXCEL ASLI
        # ----------------------------------------------------------
        wb = openpyxl.load_workbook(TEMPLATE_PATH)
        ws = wb.worksheets[0]

        TEMPLATE_FIRST_DATA_ROW = 5
        TEMPLATE_LAST_DATA_ROW  = 37  # jumlah baris siap pakai di template asli

        # Judul sheet & cell tanggal
        new_sheet_name = f"{report_month:02d}-{report_year}"
        try:
            ws.title = new_sheet_name
        except Exception:
            pass
        ws["B3"] = pd.Timestamp(report_date)

        n_rows = len(final)
        n_existing = TEMPLATE_LAST_DATA_ROW - TEMPLATE_FIRST_DATA_ROW + 1  # 33

        # Style "prototype" diambil dari baris pertama data template (row 5) -> dipakai utk baris baru jika perlu
        proto_row = TEMPLATE_FIRST_DATA_ROW

        def clone_row_style(src_row, dst_row, max_col=11):
            for c in range(1, max_col + 1):
                src_cell = ws.cell(row=src_row, column=c)
                dst_cell = ws.cell(row=dst_row, column=c)
                dst_cell.font = copy.copy(src_cell.font)
                dst_cell.border = copy.copy(src_cell.border)
                dst_cell.fill = copy.copy(src_cell.fill)
                dst_cell.alignment = copy.copy(src_cell.alignment)
                dst_cell.number_format = src_cell.number_format
                dst_cell.protection = copy.copy(src_cell.protection)
            ws.row_dimensions[dst_row].height = ws.row_dimensions[src_row].height

        # Jika data lebih banyak dari kapasitas template, sisipkan baris baru sebelum baris terakhir+1
        if n_rows > n_existing:
            extra = n_rows - n_existing
            insert_at = TEMPLATE_LAST_DATA_ROW + 1
            ws.insert_rows(insert_at, amount=extra)
            for offset in range(extra):
                clone_row_style(TEMPLATE_LAST_DATA_ROW, insert_at + offset)

        last_row_used = TEMPLATE_FIRST_DATA_ROW + n_rows - 1

        for i, (_, row) in enumerate(final.iterrows()):
            r = TEMPLATE_FIRST_DATA_ROW + i

            # No urut
            if r == TEMPLATE_FIRST_DATA_ROW:
                ws.cell(row=r, column=1).value = 1
            else:
                ws.cell(row=r, column=1).value = f"=A{r-1}+1"

            ws.cell(row=r, column=2).value = row["Tipe Pendanaan"]          # B
            ws.cell(row=r, column=3).value = row["Nama Partisipan"]        # C
            ws.cell(row=r, column=4).value = row["Nilai Pendanaan"]        # D
            ws.cell(row=r, column=5).value = row["Nilai Jaminan"]          # E
            ws.cell(row=r, column=6).value = 0                              # F - manual (Net Cash Shortfall), default 0
            if pd.notna(row["Maturity"]):
                ws.cell(row=r, column=7).value = pd.Timestamp(row["Maturity"])  # G
            else:
                ws.cell(row=r, column=7).value = 0
            ws.cell(row=r, column=8).value = f"=IF(ISBLANK(K{r}),0,$B$3-K{r})"  # H
            ws.cell(row=r, column=9).value = (
                f'=IF(B{r}="Pendanaan Transaksi Marjin",IF(F{r}<=0,"LANCAR", "CEK JUMLAH HARI"),'
                f'IF(G{r}>$B$3,"LANCAR","CEK JUMLAH HARI"))'
            )  # I
            # K (Tanggal Macet) sengaja dikosongkan -> diisi manual oleh user jika ada kontrak macet

        # Bersihkan baris sisa template yang tidak terpakai (kalau data < kapasitas template)
        if n_rows < n_existing:
            for r in range(TEMPLATE_FIRST_DATA_ROW + n_rows, TEMPLATE_LAST_DATA_ROW + 1):
                for c in range(1, 12):
                    cell = ws.cell(row=r, column=c)
                    if c == 1:
                        cell.value = None
                    elif c in (8, 9):
                        cell.value = None
                    else:
                        cell.value = None

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        st.markdown("---")
        st.download_button(
            label="⬇️ Download Hasil (format template asli, siap di-PDF-kan)",
            data=buffer,
            file_name=f"Penilaian_Kualitas_Pendanaan_Transaksi_Efek_{report_month:02d}-{report_year}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as e:
        st.error(f"Terjadi error saat memproses file: {e}")
        st.exception(e)
else:
    st.info("⬆️ Silakan upload minimal satu pasang file A01 dan F06 untuk memulai (boleh upload banyak pasangan sekaligus).")
