import streamlit as st

from excel_parser import parse_komite_excel
from ppt_generator import build_presentation

st.set_page_config(page_title="Generator PPT Komite HC & CL", page_icon="📊", layout="centered")

st.title("📊 Generator PPT Komite Haircut & Concentration Limit")
st.write(
    "Upload file Excel hasil pembahasan Komite (format 'HC dan CL - KOMITE'), "
    "lalu unduh ringkasannya dalam bentuk slide PPTX."
)

uploaded = st.file_uploader("File Excel Komite (.xlsx)", type=["xlsx"])

if uploaded is not None:
    try:
        with st.spinner("Membaca file Excel..."):
            summary = parse_komite_excel(uploaded)
    except Exception as e:
        st.error(f"Gagal membaca file: {e}")
        st.stop()

    st.success(f"Berhasil dibaca — Periode {summary.periode_label}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Saham", summary.total_saham)
    col2.metric("Haircut Berubah", summary.haircut_naik + summary.haircut_turun,
                f"{summary.haircut_naik} naik / {summary.haircut_turun} turun")
    col3.metric("Terkena UMA", summary.uma_count)
    col4.metric("Saham Baru", summary.saham_baru_count)

    if st.button("Generate Slide PPTX", type="primary"):
        with st.spinner("Membuat presentasi..."):
            pptx_buf = build_presentation(summary)
        st.download_button(
            "⬇️ Download PPTX",
            data=pptx_buf,
            file_name=f"Komite_HC_CL_{summary.periode_label.replace(' ', '_')}.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )
else:
    st.info("Menunggu file diupload.")
