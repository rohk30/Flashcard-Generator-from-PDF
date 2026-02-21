import genanki
import random
import tempfile

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
        note = genanki.Note(model=model, fields=[word, meaning, example])
        deck.add_note(note)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".apkg") as tmp:
        genanki.Package(deck).write_to_file(tmp.name)
        return tmp.name