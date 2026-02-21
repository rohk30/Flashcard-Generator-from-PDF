import streamlit as st
import os
import tempfile
import time

from services.pdf_parser import parse_pdf_gre_format
from services.anki_connect import (
    get_models,
    create_deck,
    delete_deck,
    add_note,
    get_deck_card_count
)
from services.apkg_export import generate_apkg
from utils.config import DEFAULT_ANKI_HOST, DEFAULT_ANKI_PORT

st.set_page_config(page_title="PDF → Anki GRE Flashcards", layout="centered")

st.title("📚 PDF → Anki GRE Flashcards")
st.write("Upload your GRE vocabulary PDF and generate Anki flashcards automatically.")

mode = st.radio("Mode", ["📦 Export Anki Deck (.apkg) [Cloud-friendly]", "🚀 Sync to Local Anki (Advanced)"])

anki_host = st.text_input("Anki Host", value=DEFAULT_ANKI_HOST)
anki_port = st.text_input("Anki Port", value=DEFAULT_ANKI_PORT)

delete_existing_deck = st.checkbox("🧹 Delete existing deck before import (avoid duplicates)", value=True)
throttle_ms = st.slider("⏱ Delay between cards (ms)", min_value=0, max_value=200, value=50, step=10)

uploaded_file = st.file_uploader("Upload GRE Vocabulary PDF", type=["pdf"])

if uploaded_file:
    deck_name = os.path.splitext(uploaded_file.name)[0]
    st.success(f"Deck Name: {deck_name}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        pdf_path = tmp.name

    entries = parse_pdf_gre_format(pdf_path)

    if not entries:
        st.error("❌ No words were parsed from the PDF.")
        st.stop()

    st.success(f"Parsed {len(entries)} words successfully!")
    st.write("🔍 Preview (first 10 entries):")
    st.write(entries[:10])

    # -------- Export Mode --------
    if mode.startswith("📦"):
        if st.button("📦 Generate Anki Deck (.apkg)"):
            apkg_path = generate_apkg(deck_name, entries)

            with open(apkg_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download Anki Deck",
                    data=f,
                    file_name=f"{deck_name}.apkg",
                    mime="application/octet-stream"
                )

            st.success("✅ Anki package generated! Import it into Anki and sync.")

    # -------- Local Sync Mode --------
    else:
        if st.button("🚀 Sync to Local Anki"):
            try:
                models = get_models(anki_host, anki_port)
                if "Basic" not in models:
                    st.error("❌ Anki model 'Basic' not found.")
                    st.stop()

                if delete_existing_deck:
                    delete_deck(anki_host, anki_port, deck_name)

                create_deck(anki_host, anki_port, deck_name)

                progress = st.progress(0)
                success_count = 0
                failure_count = 0
                failures = []

                for i, (word, meaning, example) in enumerate(entries):
                    ok, result = add_note(anki_host, anki_port, deck_name, word, meaning, example)
                    if ok:
                        success_count += 1
                    else:
                        failure_count += 1
                        failures.append((word, result))

                    progress.progress((i + 1) / len(entries))
                    time.sleep(throttle_ms / 1000.0)

                st.success(f"✅ Added {success_count} cards successfully.")

                if failure_count:
                    st.warning(f"⚠️ Failed to add {failure_count} cards.")
                    st.write("❌ Sample failures:")
                    st.write(failures[:10])
                else:
                    st.info("All cards added successfully!")

                deck_size = get_deck_card_count(anki_host, anki_port, deck_name)
                st.info(f"📊 Total cards in Anki deck '{deck_name}': {deck_size}")
                st.info("Open Anki and click Sync to push to AnkiWeb.")

            except Exception as e:
                st.error(f"❌ Fatal Error: {str(e)}")