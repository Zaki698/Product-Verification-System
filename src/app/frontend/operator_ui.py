import os

import requests
import streamlit as st

VALIDATION_API = os.getenv("VALIDATION_API", "http://localhost:8001")

st.set_page_config(
    page_title="Operator – Product Check",
    page_icon="✅",
    layout="centered",
)

st.markdown(
    """
    <style>
    /* All buttons: big, rounded, readable */
    div.stButton > button {
        height: 3.6em;
        font-size: 1.3em;
        font-weight: bold;
        border-radius: 14px;
    }
    /* Submit button override (even bigger) */
    div.stButton > button[kind="primary"] {
        height: 4.2em;
        font-size: 1.5em;
    }
    .page-title  { font-size: 2.2em; font-weight: 800; }
    .section-hdr { font-size: 1.4em; font-weight: 700; margin-top: 0.8em; }
    .field-label { font-size: 1.2em; font-weight: 600; }
    .info-box    { background:#e8f4fd; padding:1em; border-radius:12px;
                   font-size:1.1em; line-height:1.8; }
    .correct-chip   { background:#d4f8d4; color:#1a7a1a; padding:.3em .8em;
                      border-radius:20px; font-weight:700; font-size:1.1em; }
    .incorrect-chip { background:#f8d4d4; color:#8b0000; padding:.3em .8em;
                      border-radius:20px; font-weight:700; font-size:1.1em; }
    .neutral-chip   { background:#e0e0e0; color:#444; padding:.3em .8em;
                      border-radius:20px; font-weight:600; font-size:1.0em; }
    .ai-box { background:#fff8e1; border:1px solid #ffe082;
              padding:1em; border-radius:12px; font-size:1.05em; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
DEFAULTS = {
    "operator_id": "operator_01",
    "lookup_result": None,
    "image_bytes": None,
    "image_path": None,
    "image_mime": "image/jpeg",
    "ocr_result": None,       # raw response from /extract-dates
    "ocr_mfg_input": "",      # editable text for AI-extracted MFG date
    "ocr_exp_input": "",      # editable text for AI-extracted expiry date
    "mfg_date_result": None,  # "CORRECT" | "INCORRECT" | None
    "expiry_date_result": None,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ---------------------------------------------------------------------------
# Helper: render a CORRECT / INCORRECT toggle row
# ---------------------------------------------------------------------------
def render_field_verdict(label: str, field_key: str, emoji: str):
    """Renders a labelled row with two big buttons that toggle session state."""
    current = st.session_state[field_key]
    st.markdown(f'<p class="field-label">{emoji} {label}</p>', unsafe_allow_html=True)

    col_c, col_i = st.columns(2)
    with col_c:
        btn_type = "primary" if current == "CORRECT" else "secondary"
        if st.button("✅  CORRECT", key=f"{field_key}_correct",
                     use_container_width=True, type=btn_type):
            st.session_state[field_key] = "CORRECT"
            st.rerun()
    with col_i:
        btn_type = "primary" if current == "INCORRECT" else "secondary"
        if st.button("❌  INCORRECT", key=f"{field_key}_incorrect",
                     use_container_width=True, type=btn_type):
            st.session_state[field_key] = "INCORRECT"
            st.rerun()

    # Small chip showing current selection
    if current == "CORRECT":
        st.markdown('<span class="correct-chip">✅ CORRECT selected</span>',
                    unsafe_allow_html=True)
    elif current == "INCORRECT":
        st.markdown('<span class="incorrect-chip">❌ INCORRECT selected</span>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<span class="neutral-chip">— not selected yet</span>',
                    unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helper: submit validation to backend
# ---------------------------------------------------------------------------
def submit_validation(validation_mode: str, ocr_mfg: str = None, ocr_exp: str = None):
    payload = {
        "wid": st.session_state.lookup_result["wid"],
        "operator_id": st.session_state.operator_id or "operator",
        "validation_mode": validation_mode,
        "mfg_date_result": st.session_state.mfg_date_result,
        "expiry_date_result": st.session_state.expiry_date_result,
        "ocr_mfg_date": ocr_mfg,
        "ocr_expiry_date": ocr_exp,
        "image_path": st.session_state.image_path,
    }
    try:
        resp = requests.post(f"{VALIDATION_API}/validate", json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        overall = data.get("overall_result", "UNKNOWN")
        st.success(
            f"✅ Saved! Overall result: **{overall}** "
            f"(MFG: {st.session_state.mfg_date_result} | "
            f"Expiry: {st.session_state.expiry_date_result})"
        )
        st.balloons()
        # Reset for next item
        for k, v in DEFAULTS.items():
            st.session_state[k] = v
        st.session_state.operator_id = payload["operator_id"]   # keep operator id
    except Exception as e:
        st.error(f"Could not save validation: {e}")


# ===========================================================================
# PAGE LAYOUT
# ===========================================================================
st.markdown('<p class="page-title">✅ Product Check</p>', unsafe_allow_html=True)

# ── Operator ID ────────────────────────────────────────────────────────────
st.session_state.operator_id = st.text_input(
    "👤 Operator name / ID",
    value=st.session_state.operator_id,
)

st.divider()

# ── Step 1: WID lookup ─────────────────────────────────────────────────────
st.markdown('<p class="section-hdr">1️⃣  Scan or type the product code (WID)</p>',
            unsafe_allow_html=True)
wid_input = st.text_input(
    "WID",
    label_visibility="collapsed",
    placeholder="Scan barcode or type WID here",
)

if st.button("🔍  LOOK UP PRODUCT", use_container_width=True):
    if not wid_input.strip():
        st.warning("Please scan or type a WID first.")
    else:
        try:
            resp = requests.get(
                f"{VALIDATION_API}/lookup/{wid_input.strip()}", timeout=10
            )
            resp.raise_for_status()
            st.session_state.lookup_result = resp.json()
            # Reset downstream state on new lookup
            for k in ("image_bytes", "image_path", "image_mime", "ocr_result",
                       "ocr_mfg_input", "ocr_exp_input",
                       "mfg_date_result", "expiry_date_result"):
                st.session_state[k] = DEFAULTS[k]
        except Exception as e:
            st.error(f"Could not reach Validation Service: {e}")
            st.session_state.lookup_result = None

result = st.session_state.lookup_result

if not result:
    st.stop()

st.divider()

# ── Step 2: Show system record ─────────────────────────────────────────────
if not result["found"]:
    st.error(f"❌  WID **{result['wid']}** was not found in the system.")
    st.stop()

st.markdown('<p class="section-hdr">2️⃣  System record for this product</p>',
            unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
c1.metric("EAN (Barcode)",       result["ean"])
c2.metric("Manufacturing Date",  result["manufacturing_date"])
c3.metric("Expiry Date",         result["expiry_date"])

st.divider()

# ── Step 3: Choose validation mode ─────────────────────────────────────────
st.markdown('<p class="section-hdr">3️⃣  How do you want to validate?</p>',
            unsafe_allow_html=True)

mode = st.radio(
    "Validation method",
    options=["📋  Manual – I will compare the label myself",
             "📸  Photo – Upload image for AI date extraction"],
    label_visibility="collapsed",
)

is_manual = mode.startswith("📋")

st.divider()

# ===========================================================================
# MANUAL VALIDATION FLOW
# ===========================================================================
if is_manual:
    st.markdown('<p class="section-hdr">4️⃣  Mark each date as Correct or Incorrect</p>',
                unsafe_allow_html=True)
    st.info("Compare the physical label to the system record above, then tap each result.")

    render_field_verdict("Manufacturing Date", "mfg_date_result", "🏭")
    st.markdown("<br>", unsafe_allow_html=True)
    render_field_verdict("Expiry Date", "expiry_date_result", "📅")

    st.markdown("<br>", unsafe_allow_html=True)

    both_set = (
        st.session_state.mfg_date_result is not None
        and st.session_state.expiry_date_result is not None
    )

    if both_set:
        if st.button("🚀  SUBMIT VALIDATION", use_container_width=True, type="primary"):
            submit_validation("MANUAL")
    else:
        st.warning("Please mark both dates before submitting.")

# ===========================================================================
# IMAGE / AI VALIDATION FLOW
# ===========================================================================
else:
    st.markdown('<p class="section-hdr">4️⃣  Upload a photo of the product label</p>',
                unsafe_allow_html=True)

    uploaded_photo = st.file_uploader(
        "Upload product label image",
        type=["jpg", "jpeg", "png", "webp"],
        label_visibility="collapsed",
    )

    if uploaded_photo is not None:
        # Store bytes and mime in session so they survive reruns
        st.session_state.image_bytes = uploaded_photo.getvalue()
        st.session_state.image_mime = uploaded_photo.type or "image/jpeg"
        st.image(st.session_state.image_bytes, caption="Uploaded image", use_column_width=True)

    if st.session_state.image_bytes is not None:
        # ── Save image + Extract dates ──────────────────────────────────────
        if st.button("🤖  EXTRACT DATES WITH AI", use_container_width=True):
            with st.spinner("AI is reading the product label..."):
                try:
                    # 1. Save image first (reuse path in /validate)
                    up_resp = requests.post(
                        f"{VALIDATION_API}/upload-image",
                        files={"file": (
                            "label.jpg",
                            st.session_state.image_bytes,
                            st.session_state.image_mime,
                        )},
                        timeout=30,
                    )
                    up_resp.raise_for_status()
                    st.session_state.image_path = up_resp.json()["image_path"]

                    # 2. Extract dates
                    ocr_resp = requests.post(
                        f"{VALIDATION_API}/extract-dates",
                        files={"file": (
                            "label.jpg",
                            st.session_state.image_bytes,
                            st.session_state.image_mime,
                        )},
                        timeout=60,
                    )
                    ocr_resp.raise_for_status()
                    ocr = ocr_resp.json()
                    st.session_state.ocr_result = ocr
                    st.session_state.ocr_mfg_input = ocr.get("mfg_date") or ""
                    st.session_state.ocr_exp_input = ocr.get("expiry_date") or ""

                    # Auto-set verdicts based on match
                    sys_mfg = result["manufacturing_date"]
                    sys_exp = result["expiry_date"]
                    st.session_state.mfg_date_result = (
                        "CORRECT"
                        if st.session_state.ocr_mfg_input == sys_mfg
                        else "INCORRECT"
                    )
                    st.session_state.expiry_date_result = (
                        "CORRECT"
                        if st.session_state.ocr_exp_input == sys_exp
                        else "INCORRECT"
                    )
                except Exception as e:
                    st.error(f"AI extraction failed: {e}")

    # ── Show AI results if we have them ──────────────────────────────────
    if st.session_state.ocr_result is not None:
        ocr = st.session_state.ocr_result

        if not ocr.get("success"):
            st.error(f"AI could not extract dates: {ocr.get('error', 'Unknown error')}")
        else:
            conf = ocr.get("confidence") or 0
            st.markdown(
                f'<div class="ai-box">🤖 <b>AI Extraction Complete</b> &nbsp;'
                f'Confidence: <b>{conf*100:.0f}%</b></div>',
                unsafe_allow_html=True,
            )
            if conf < 0.7:
                st.warning(
                    "⚠️  Low confidence — the image may be blurry or the dates partially covered. "
                    "Please verify the extracted dates carefully and correct them if needed."
                )

            st.markdown("<br>", unsafe_allow_html=True)

            # Side-by-side comparison table
            st.markdown("**📊 Comparison: AI Extracted vs System Record**")
            col_f, col_ai, col_sys, col_m = st.columns([2, 2, 2, 1])
            col_f.markdown("**Field**")
            col_ai.markdown("**AI Read**")
            col_sys.markdown("**System Has**")
            col_m.markdown("**Match?**")

            mfg_match = st.session_state.ocr_mfg_input == result["manufacturing_date"]
            exp_match  = st.session_state.ocr_exp_input == result["expiry_date"]

            col_f.write("Manufacturing Date")
            col_ai.write(st.session_state.ocr_mfg_input or "—")
            col_sys.write(result["manufacturing_date"])
            col_m.write("✅" if mfg_match else "❌")

            col_f.write("Expiry Date")
            col_ai.write(st.session_state.ocr_exp_input or "—")
            col_sys.write(result["expiry_date"])
            col_m.write("✅" if exp_match else "❌")

            st.divider()

            # ── Editable AI dates (operator can fix AI mistakes) ──────────
            st.markdown("**✏️  Edit AI-extracted dates if incorrect (YYYY-MM-DD)**")
            e1, e2 = st.columns(2)
            new_mfg = e1.text_input(
                "Manufacturing Date (AI read)",
                value=st.session_state.ocr_mfg_input,
                key="edit_mfg",
            )
            new_exp = e2.text_input(
                "Expiry Date (AI read)",
                value=st.session_state.ocr_exp_input,
                key="edit_exp",
            )

            # Update session state and re-evaluate auto-verdict when inputs change
            if new_mfg != st.session_state.ocr_mfg_input:
                st.session_state.ocr_mfg_input = new_mfg
                st.session_state.mfg_date_result = (
                    "CORRECT" if new_mfg == result["manufacturing_date"] else "INCORRECT"
                )
            if new_exp != st.session_state.ocr_exp_input:
                st.session_state.ocr_exp_input = new_exp
                st.session_state.expiry_date_result = (
                    "CORRECT" if new_exp == result["expiry_date"] else "INCORRECT"
                )

            st.divider()

            # ── Per-field verdict (auto-set, but operator can override) ───
            st.markdown(
                "**5️⃣  Confirm or change the verdict for each date**  "
                "_(auto-filled from AI comparison — override if needed)_"
            )
            render_field_verdict("Manufacturing Date", "mfg_date_result", "🏭")
            st.markdown("<br>", unsafe_allow_html=True)
            render_field_verdict("Expiry Date", "expiry_date_result", "📅")

            st.markdown("<br>", unsafe_allow_html=True)

            both_set = (
                st.session_state.mfg_date_result is not None
                and st.session_state.expiry_date_result is not None
            )

            if both_set:
                if st.button("🚀  SUBMIT VALIDATION", use_container_width=True, type="primary"):
                    submit_validation(
                        "IMAGE",
                        ocr_mfg=st.session_state.ocr_mfg_input or None,
                        ocr_exp=st.session_state.ocr_exp_input or None,
                    )
            else:
                st.warning("Please confirm both date verdicts before submitting.")

# ---------------------------------------------------------------------------
st.divider()
st.caption(f"Validation Service: {VALIDATION_API}")
