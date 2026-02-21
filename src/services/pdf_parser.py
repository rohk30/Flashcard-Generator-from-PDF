import pdfplumber

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