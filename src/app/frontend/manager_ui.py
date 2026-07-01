import os
import requests
import streamlit as st

INGESTION_API = os.getenv("INGESTION_API", "http://localhost:8000")

st.set_page_config(page_title="Warehouse Manager - Bulk Upload", page_icon="📦", layout="centered")

st.title("📦 Warehouse Manager")
st.subheader("Bulk Product Data Upload")

st.markdown(
    "Upload a CSV with columns **WID, EAN, Manufacturing_Date, Expiry_Date** "
    "to populate the system with new inventory."
)

uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])

if uploaded_file is not None:
    st.write(f"Selected file: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")
    if st.button("🚀 Upload & Process", use_container_width=True, type="primary"):
        with st.spinner("Uploading and bulk-loading into the database... this may take a while for large files."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
                resp = requests.post(f"{INGESTION_API}/upload", files=files, timeout=600)
                resp.raise_for_status()
                result = resp.json()
            except Exception as e:
                st.error(f"Upload failed: {e}")
                result = None

        if result:
            if result["status"] == "completed":
                st.success(result["message"])
            else:
                st.error(result["message"])

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total rows", result["total_rows"])
            c2.metric("Inserted", result["inserted_rows"])
            c3.metric("Duplicates", result["duplicate_rows"])
            c4.metric("Failed", result["failed_rows"])

st.divider()
st.subheader("📜 Recent Upload Batches")
try:
    batches = requests.get(f"{INGESTION_API}/batches", timeout=10).json()
    if batches:
        st.dataframe(batches, use_container_width=True, hide_index=True)
    else:
        st.info("No batches uploaded yet.")
except Exception as e:
    st.warning(f"Could not reach Ingestion Service at {INGESTION_API}: {e}")