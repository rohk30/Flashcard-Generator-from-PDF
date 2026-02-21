import streamlit as st
import pdfplumber
import requests
import os
import tempfile
import time
import genanki
import random
import tempfile

st.set_page_config(page_title="PDF → Anki GRE Flashcards", layout="centered")

st.title("📚 GRE PDF → Anki Flashcards (Stable Import)")
st.write("Upload your GRE vocabulary PDF and generate Anki flashcards automatically.")

anki_host = st.text_input("Anki Host", value="http://localhost")
anki_port = st.text_input("Anki Port", value="8765")

delete_existing_deck = st.checkbox("🧹 Delete existing deck before import (avoid duplicates)", value=True)
throttle_ms = st.slider("⏱ Delay between cards (ms)", min_value=0, max_value=200, value=50, step=10)

uploaded_file = st.file_uploader("Upload GRE Vocabulary PDF", type=["pdf"])


# -------------------- AnkiConnect Helpers --------------------

def anki_request(action, params, retries=5, delay=1):
    url = f"{anki_host}:{anki_port}"
    payload = {
        "action": action,
        "version": 6,
        "params": params
    }

    for attempt in range(retries):
        try:
            res = requests.post(url, json=payload, timeout=5).json()
            if res.get("error"):
                raise Exception(res["error"])
            return res["result"]
        except Exception as e:
            print(f"[WARN] AnkiConnect error (attempt {attempt+1}/{retries}): {e}")
            time.sleep(delay)

    raise Exception("❌ AnkiConnect unreachable after multiple retries.")


def get_models():
    return anki_request("modelNames", {})


def create_deck(deck_name):
    return anki_request("createDeck", {"deck": deck_name})


def delete_deck(deck_name):
    return anki_request("deleteDecks", {"decks": [deck_name], "cardsToo": True})


def add_note(deck_name, word, meaning, example):
    note = {
        "deckName": deck_name,
        "modelName": "Basic",
        "fields": {
            "Front": word,
            "Back": f"<b>Meaning:</b> {meaning}<br><br><b>Example:</b> {example}"
        },
        "tags": ["GRE", deck_name]
    }

    try:
        result = anki_request("addNote", {"note": note})
        return True, result
    except Exception as e:
        return False, str(e)


def get_deck_card_count(deck_name):
    cards = anki_request("findCards", {"query": f'deck:"{deck_name}"'})
    return len(cards)


# -------------------- PDF Parser --------------------

def parse_pdf_gre_format(pdf_path):
    entries = []

    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"

    lines = [line.strip().replace("", "").strip() for line in text.split("\n") if line.strip()]

    current_word = None
    current_meaning = None

    for line in lines:
        if "." in line and "(" in line and ")" in line and line.split(".")[0].isdigit():
            try:
                current_word = line.split(". ", 1)[1].split("(")[0].strip()
            except:
                current_word = None

        elif line.lower().startswith("meaning:"):
            current_meaning = line.replace("Meaning:", "").strip()

        elif line.lower().startswith("example:"):
            example = line.replace("Example:", "").strip()
            if current_word and current_meaning:
                entries.append((current_word, current_meaning, example))
                current_word, current_meaning = None, None

    return entries

def generate_apkg(deck_name, entries):
    model_id = random.randrange(1 << 30, 1 << 31)
    deck_id = random.randrange(1 << 30, 1 << 31)

    model = genanki.Model(
        model_id,
        'GRE Basic Model',
        fields=[
            {'name': 'Word'},
            {'name': 'Meaning'},
            {'name': 'Example'},
        ],
        templates=[
            {
                'name': 'Card 1',
                'qfmt': '<h2>{{Word}}</h2>',
                'afmt': '<b>Meaning:</b> {{Meaning}}<br><br><b>Example:</b> {{Example}}',
            },
        ],
    )

    deck = genanki.Deck(deck_id, deck_name)

    for word, meaning, example in entries:
        note = genanki.Note(
            model=model,
            fields=[word, meaning, example]
        )
        deck.add_note(note)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".apkg") as tmp:
        genanki.Package(deck).write_to_file(tmp.name)
        return tmp.name
    
# -------------------- Main Flow --------------------



if uploaded_file:
    deck_name = os.path.splitext(uploaded_file.name)[0]
    st.success(f"Deck Name: {deck_name}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        pdf_path = tmp.name

    if st.button("🚀 Create Anki Deck"):
        try:
            entries = parse_pdf_gre_format(pdf_path)

            if len(entries) == 0:
                st.error("❌ No words were parsed from the PDF.")
                st.stop()

            st.success(f"Parsed {len(entries)} words successfully!")
            st.write("🔍 First 10 parsed entries:")
            st.write(entries[:10])

            print(f"[DEBUG] Parsed {len(entries)} entries from PDF")

            models = get_models()
            if "Basic" not in models:
                st.error("❌ Anki model 'Basic' not found.")
                st.stop()

            if delete_existing_deck:
                try:
                    delete_deck(deck_name)
                    print(f"[DEBUG] Deleted existing deck: {deck_name}")
                except:
                    print(f"[DEBUG] No deck to delete: {deck_name}")

            create_deck(deck_name)
            print(f"[DEBUG] Created deck: {deck_name}")

            progress = st.progress(0)
            success_count = 0
            failure_count = 0
            failures = []

            for i, (word, meaning, example) in enumerate(entries):
                ok, result = add_note(deck_name, word, meaning, example)

                if ok:
                    success_count += 1
                    print(f"[OK] {word}")
                else:
                    failure_count += 1
                    failures.append((word, result))
                    print(f"[FAIL] {word} -> {result}")

                progress.progress((i + 1) / len(entries))
                time.sleep(throttle_ms / 1000.0)

            st.success(f"✅ Added {success_count} cards successfully.")              

            if failure_count:
                st.warning(f"⚠️ Failed to add {failure_count} cards.")
                st.write("❌ Sample failures:")
                st.write(failures[:10])
            else:                
                st.info("All cards added successfully!")

            deck_size = get_deck_card_count(deck_name)
            st.info(f"📊 Total cards in Anki deck '{deck_name}': {deck_size}")
            print(f"[DEBUG] Final deck size: {deck_size}")

            st.info("Open Anki and click Sync to push to AnkiWeb.")

        except Exception as e:
            print("[FATAL ERROR]", e)
            st.error(f"❌ Fatal Error: {str(e)}")