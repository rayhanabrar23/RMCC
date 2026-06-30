import streamlit as st
import pandas as pd
import io
import os
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

def get_template_bytes(uploaded_template_file):
    """Template diambil dari file yang diupload user (bukan file di server),
    supaya tidak ada masalah path sama sekali di Streamlit multipage app."""
    return io.BytesIO(uploaded_template_file.read())

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
col_f06_kualitas  = st.sidebar.number_input("F06 - posisi kolom Kode Kualitas",             min_value=0, value=11)

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

QUALITY_MAP = {
    "1": "LANCAR",
    "2": "DALAM PERHATIAN KHUSUS",
    "3": "KURANG LANCAR",
    "4": "DIRAGUKAN",
    "5": "MACET",
}

def parse_quality(value):
    value = (value or "").strip()
    return QUALITY_MAP.get(value, value) if value else None

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

st.subheader("📐 Upload Template Excel")
st.caption(
    "Upload file template Excel asli (format, font, kolom hidden, dll). File ini yang akan "
    "diisi otomatis dan dijadikan hasil akhir — formatnya tidak akan diubah sama sekali."
)
template_file = st.file_uploader("Upload Template (.xlsx)", type=["xlsx"], key="template")

st.markdown("---")

col1, col2, col3 = st.columns(3)
with col1:
    files_a01 = st.file_uploader("Upload semua file A01 (.txt)", type=["txt"], key="a01", accept_multiple_files=True)
with col2:
    files_f06 = st.file_uploader("Upload semua file F06 (.txt)", type=["txt"], key="f06", accept_multiple_files=True)
with col3:
    files_d02 = st.file_uploader("Upload file D02 (.txt) — opsional, fallback nama", type=["txt"], key="d02", accept_multiple_files=True)

st.markdown("---")
st.subheader("🛠️ Data Koreksi (opsional)")
st.caption(
    "Kalau ada file koreksi (cuma berisi SID/baris tertentu yang nilainya perlu diperbaiki), "
    "upload di sini. Format file sama seperti A01/F06 biasa, tapi isinya cuma sebagian data "
    "(yang dikoreksi saja). Data koreksi akan **menimpa** baris dengan SID yang sama di data "
    "utama, baris lain yang tidak ada di file koreksi tidak akan berubah. Boleh upload "
    "**lebih dari satu set koreksi** — kalau SID yang sama dikoreksi berkali-kali, koreksi yang "
    "diupload paling akhir yang dipakai."
)
ck1, ck2 = st.columns(2)
with ck1:
    files_a01_koreksi = st.file_uploader("Upload file A01 Koreksi (.txt)", type=["txt"], key="a01_koreksi", accept_multiple_files=True)
with ck2:
    files_f06_koreksi = st.file_uploader("Upload file F06 Koreksi (.txt)", type=["txt"], key="f06_koreksi", accept_multiple_files=True)

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
if not template_file:
    st.info("⬆️ Silakan upload file Template Excel dulu di atas.")
elif files_a01 and files_f06:
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

        def parse_a01_f06_pair(fa01, ff06, label):
            """Parse satu pasang A01+F06 -> DataFrame (kolom SID tetap dipertahankan,
            dipakai sebagai key untuk koreksi). Dipakai baik untuk batch utama
            maupun batch koreksi."""
            a01_rows, _ = read_pipe_file(fa01)
            f06_rows, f06_header = read_pipe_file(ff06)
            yr, mo, rdate = detect_periode(f06_header)

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

            f06_records = []
            for r in f06_rows:
                no_fas    = safe_get(r, col_f06_sid).strip()
                cif       = safe_get(r, col_f06_cif).strip()
                pendanaan = parse_number(safe_get(r, col_f06_pendanaan))
                maturity  = parse_date(safe_get(r, col_f06_maturity))
                jenis     = safe_get(r, col_f06_jenis).strip()
                kualitas  = safe_get(r, col_f06_kualitas).strip()
                if no_fas:
                    f06_records.append((no_fas, cif, pendanaan, maturity, jenis, kualitas))

            df_f06 = pd.DataFrame(
                f06_records,
                columns=["SID", "CIF", "Nilai Pendanaan", "Maturity", "Kode Jenis", "Kode Kualitas"]
            )
            if df_f06.empty:
                return pd.DataFrame(), yr, mo

            df_f06["Tipe Pendanaan"] = df_f06["Kode Jenis"].apply(label_jenis)
            df_f06["Status"] = df_f06["Kode Kualitas"].apply(parse_quality)

            result = pd.merge(df_f06, df_a01_fas, left_on="SID", right_on="fas_key", how="left")
            result = result.drop(columns=["fas_key"], errors="ignore")

            if d02_by_cif:
                result["Nama_D02"] = result["CIF"].map(d02_by_cif)
                result["Nama Partisipan"] = result["Nama Partisipan"].fillna(result["Nama_D02"])
                result = result.drop(columns=["Nama_D02"], errors="ignore")

            result["Nilai Jaminan"] = result["Nilai Jaminan"].fillna(0)
            result["Batch"] = label
            return result, yr, mo

        all_results = []
        detected_periods = []

        for i, (fa01, ff06) in enumerate(zip(files_a01, files_f06), start=1):
            label = f"{fa01.name} + {ff06.name}"
            result, yr, mo = parse_a01_f06_pair(fa01, ff06, label)
            if result.empty:
                st.warning(f"⚠️ Batch #{i}: file F06 ({ff06.name}) tidak menghasilkan baris data.")
                continue
            if yr and mo:
                detected_periods.append((yr, mo))
            all_results.append(result)

        if not all_results:
            st.error("❌ Tidak ada data valid dari batch manapun.")
            st.stop()

        # ---- Susun data utama jadi dict per SID (supaya koreksi bisa menimpa per-SID) ----
        data_by_sid = {}
        sid_order = []  # urutan kemunculan SID pertama kali, untuk sorting stabil nanti
        for result in all_results:
            for _, row in result.iterrows():
                sid = row["SID"]
                if sid not in data_by_sid:
                    sid_order.append(sid)
                data_by_sid[sid] = row.to_dict()

        # ---- KOREKSI (opsional, bisa berkali-kali, urut sesuai upload) ----
        koreksi_count = 0
        koreksi_sids = set()
        if files_a01_koreksi and files_f06_koreksi:
            if len(files_a01_koreksi) != len(files_f06_koreksi):
                st.error(
                    f"❌ Jumlah file A01 Koreksi ({len(files_a01_koreksi)}) dan F06 Koreksi "
                    f"({len(files_f06_koreksi)}) tidak sama. Setiap batch koreksi harus punya pasangan."
                )
                st.stop()

            for j, (fa01k, ff06k) in enumerate(zip(files_a01_koreksi, files_f06_koreksi), start=1):
                label = f"[KOREKSI #{j}] {fa01k.name} + {ff06k.name}"
                result_k, _, _ = parse_a01_f06_pair(fa01k, ff06k, label)
                if result_k.empty:
                    st.warning(f"⚠️ Koreksi #{j}: file F06 ({ff06k.name}) tidak menghasilkan baris data.")
                    continue
                for _, row in result_k.iterrows():
                    sid = row["SID"]
                    if sid not in data_by_sid:
                        sid_order.append(sid)
                    data_by_sid[sid] = row.to_dict()
                    koreksi_sids.add(sid)
                    koreksi_count += 1

        final = pd.DataFrame([data_by_sid[sid] for sid in sid_order])

        if koreksi_count > 0:
            st.success(
                f"🛠️ {len(koreksi_sids)} SID berhasil dikoreksi (dari {koreksi_count} baris koreksi yang diupload, "
                f"koreksi berikutnya menimpa koreksi sebelumnya jika SID sama)."
            )

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

        n_status_missing = final["Status"].isna().sum()
        if n_status_missing > 0:
            st.warning(
                f"⚠️ {n_status_missing} baris tidak punya Status/Kualitas Pendanaan yang valid. "
                f"Cek posisi kolom 'F06 - posisi kolom Kode Kualitas' di sidebar, mungkin salah."
            )

        final = final[["SID", "Tipe Pendanaan", "Nama Partisipan", "Nilai Pendanaan", "Nilai Jaminan", "Maturity", "Status", "Batch"]]
        final = final.sort_values(["Tipe Pendanaan", "Nama Partisipan"], na_position="last").reset_index(drop=True)

        st.success(
            f"✅ Berhasil! {len(final)} baris unik (per SID) dari {len(all_results)} batch utama digabung. "
            f"Periode: {report_date.strftime('%d %B %Y')}"
        )

        # ----------------------------------------------------------
        # DASHBOARD RINGKASAN STATUS
        # ----------------------------------------------------------
        st.subheader("🏦 Ringkasan Status Kualitas Kredit")
        STATUS_ORDER = ["LANCAR", "DALAM PERHATIAN KHUSUS", "KURANG LANCAR", "DIRAGUKAN", "MACET"]
        status_counts = final["Status"].value_counts()
        total_kontrak = len(final)

        dash_cols = st.columns(5)
        for i, st_key in enumerate(STATUS_ORDER):
            count = int(status_counts.get(st_key, 0))
            pct = (count / total_kontrak * 100) if total_kontrak > 0 else 0
            dash_cols[i].metric(st_key, f"{count:,}", f"{pct:.1f}%")

        st.caption(
            f"Total kontrak: **{total_kontrak:,}** dari **{len(all_results)} batch** file. "
            f"Periode: **{report_date.strftime('%d %B %Y')}**"
        )
        st.markdown("---")

        st.subheader("📋 Preview Data Gabungan (sebelum dimasukkan ke template)")
        st.dataframe(
            final.style.format({"Nilai Pendanaan": "{:,.0f}", "Nilai Jaminan": "{:,.0f}"}),
            use_container_width=True,
        )

        # ----------------------------------------------------------
        # ISI KE TEMPLATE EXCEL ASLI
        # ----------------------------------------------------------
        wb = openpyxl.load_workbook(get_template_bytes(template_file))
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

            tipe_pendanaan = row["Tipe Pendanaan"]
            nilai_pendanaan = row["Nilai Pendanaan"]
            nilai_jaminan = row["Nilai Jaminan"]
            maturity_val = row["Maturity"]

            ws.cell(row=r, column=2).value = tipe_pendanaan          # B
            ws.cell(row=r, column=3).value = row["Nama Partisipan"]  # C
            ws.cell(row=r, column=4).value = nilai_pendanaan         # D
            ws.cell(row=r, column=5).value = nilai_jaminan           # E
            ws.cell(row=r, column=6).value = 0                        # F - manual (Net Cash Shortfall), default 0

            if pd.notna(maturity_val):
                maturity_ts = pd.Timestamp(maturity_val)
                g_cell = ws.cell(row=r, column=7)
                g_cell.value = maturity_ts
                g_cell.number_format = "dd/mm/yyyy"  # short date sesuai permintaan
            else:
                maturity_ts = None
                ws.cell(row=r, column=7).value = 0

            # H (Jumlah Hari) -> dihitung langsung sebagai value (K kosong -> 0)
            jumlah_hari = 0  # karena K (Tanggal Macet) tidak diisi otomatis
            ws.cell(row=r, column=8).value = jumlah_hari

            # I (Status / Kualitas Pendanaan) -> diambil langsung dari Kode Kualitas F06
            # (LANCAR / DALAM PERHATIAN KHUSUS / KURANG LANCAR / DIRAGUKAN / MACET)
            status = row["Status"] if pd.notna(row["Status"]) else ""
            i_cell = ws.cell(row=r, column=9)
            i_cell.value = status
            if status == "MACET":
                old_font = i_cell.font
                i_cell.font = openpyxl.styles.Font(
                    name=old_font.name, size=old_font.size, bold=old_font.bold,
                    italic=old_font.italic, color="FFFF0000",
                )

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
            file_name=f"{report_year}-{report_month:02d}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as e:
        st.error(f"Terjadi error saat memproses file: {e}")
        st.exception(e)
else:
    st.info("⬆️ Silakan upload minimal satu pasang file A01 dan F06 untuk memulai (boleh upload banyak pasangan sekaligus).")
