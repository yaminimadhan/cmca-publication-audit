import spacy
from pathlib import Path
from rapidfuzz import fuzz, process

# Load spaCy model
nlp = spacy.load("en_core_web_trf")


def staff_list(filepath="staffs.txt"):
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip().rstrip(",") for line in f if line.strip()]


def staff_mention(sentences, staff_list, threshold=90):
    staff_name = []

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        doc = nlp(sentence)
        matched_people = []

        for ent in doc.ents:
            if ent.label_ == "PERSON" and len(ent.text.strip()) >= 3:
                match, score, _ = process.extractOne(
                    ent.text.lower(),
                    [s.lower() for s in staff_list],
                    scorer=fuzz.partial_ratio
                )
                if score >= threshold:
                    matched_people.append({
                        "detected_name": ent.text,
                        "matched_staff": match,
                        "match_score": score
                    })

        if matched_people:
            staff_name.append({
                "sentence": sentence,
                "matches": matched_people
            })

    return staff_name


def instrument_list(filepath="instruments.txt"):
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip().lower() for line in f if line.strip()]


def instrument_mention(sentences, instrument_list):
    instrument_matches = []

    for sentence in sentences:
        sentence_clean = sentence.strip()
        if not sentence_clean:
            continue

        matched_instruments = [
            inst for inst in instrument_list if inst in sentence_clean.lower()
        ]

        if matched_instruments:
            instrument_matches.append({
                "sentence": sentence_clean,
                "matched_instruments": matched_instruments
            })

    return instrument_matches