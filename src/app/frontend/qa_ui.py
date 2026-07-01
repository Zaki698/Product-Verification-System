import os
from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st

REPORTING_API = os.getenv("REPORTING_API", "http://localhost:8002")

st.set_page_config(page_title="QA Manager – Reports", page_icon="📊", layout="wide")
st.title("📊 Quality Assurance Manager")
st.subheader("Verification Activity Report")

c1, c2, c3 = st.columns([1, 1, 1])
start_date = c1.date_input("Start date", value=date.today() - timedelta(days=7))
end_date   = c2.date_input("End date",   value=date.today())
generate   = c3.button("📈 Generate Report", type="primary", use_container_width=True)

if generate:
    if start_date > end_date:
        st.error("Start date must be before end date.")
    else:
        try:
            resp = requests.get(
                f"{REPORTING_API}/report",
                params={"start_date": start_date.isoformat(),
                        "end_date":   end_date.isoformat()},
                timeout=60,
            )
            resp.raise_for_status()
            report = resp.json()
        except Exception as e:
            st.error(f"Could not reach Reporting Service: {e}")
            report = None

        if report:
            # ── Narrative ──────────────────────────────────────────────────
            st.info(
                f"**Summary for {start_date} → {end_date}**\n\n"
                # f"{report.get('narrative', '')}"
            )

            # ── Top-line metrics ───────────────────────────────────────────
            st.markdown("### Overall Counts")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Checks",   report["total_checks"])
            m2.metric("✅ Correct",     report["correct"])
            m3.metric("❌ Incorrect",   report["incorrect"])
            m4.metric("❓ Not Found",   report["not_found"])

            # ── Per-field breakdown (new in v2) ────────────────────────────
            st.markdown("### Field-level Breakdown")
            f1, f2 = st.columns(2)
            f1.metric(
                "🏭 Mfg Date Mismatches",
                report.get("mfg_date_incorrect", "—"),
                help="Checks where the Manufacturing Date was marked INCORRECT",
            )
            f2.metric(
                "📅 Expiry Date Mismatches",
                report.get("expiry_date_incorrect", "—"),
                help="Checks where the Expiry Date was marked INCORRECT",
            )

            # ── AI Insights ─────────────────────────────────────────
            st.markdown("### AI Insights")
            st.markdown(report["narrative"])

            # ── Detailed log table ─────────────────────────────────────────
            st.divider()
            st.markdown("### Detailed Log")
            if report["logs"]:
                df = pd.DataFrame(report["logs"])

                # Friendly column ordering
                ordered_cols = [
                    "id", "checked_at", "wid", "ean",
                    "manufacturing_date", "expiry_date",
                    "operator_id", "validation_mode",
                    "result", "mfg_date_result", "expiry_date_result",
                    "ocr_mfg_date", "ocr_expiry_date", "image_path",
                ]
                df = df[[c for c in ordered_cols if c in df.columns]]

                st.dataframe(df, use_container_width=True, hide_index=True)

                csv_bytes = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Download CSV",
                    csv_bytes,
                    file_name=f"verification_report_{start_date}_{end_date}.csv",
                    mime="text/csv",
                )
            else:
                st.info("No verification activity found in this date range.")
