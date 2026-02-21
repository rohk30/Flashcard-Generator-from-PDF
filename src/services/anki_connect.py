import requests
import time

def anki_request(host, port, action, params, retries=5, delay=1):
    url = f"{host}:{port}"
    payload = {"action": action, "version": 6, "params": params}

    for attempt in range(retries):
        try:
            res = requests.post(url, json=payload, timeout=5).json()
            if res.get("error"):
                raise Exception(res["error"])
            return res["result"]
        except Exception as e:
            print(f"[WARN] AnkiConnect error (attempt {attempt+1}/{retries}): {e}")
            time.sleep(delay)

    raise Exception("AnkiConnect unreachable after retries")

def get_models(host, port):
    return anki_request(host, port, "modelNames", {})

def create_deck(host, port, deck_name):
    return anki_request(host, port, "createDeck", {"deck": deck_name})

def delete_deck(host, port, deck_name):
    return anki_request(host, port, "deleteDecks", {"decks": [deck_name], "cardsToo": True})

def add_note(host, port, deck_name, word, meaning, example):
    note = {
        "deckName": deck_name,
        "modelName": "Basic",
        "fields": {"Front": word, "Back": f"<b>Meaning:</b> {meaning}<br><br><b>Example:</b> {example}"},
        "tags": ["GRE", deck_name]
    }

    try:
        return True, anki_request(host, port, "addNote", {"note": note})
    except Exception as e:
        return False, str(e)

def get_deck_card_count(host, port, deck_name):
    cards = anki_request(host, port, "findCards", {"query": f'deck:\"{deck_name}\"'})
    return len(cards)