import re
import unicodedata


# Serbian Cyrillic, plus Russian/Ukrainian letters that Whisper sometimes mixes in
_CYRILLIC_LOWER = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'ђ': 'đ', 'е': 'e', 'ж': 'ž',
    'з': 'z', 'и': 'i', 'ј': 'j', 'к': 'k', 'л': 'l', 'љ': 'lj', 'м': 'm', 'н': 'n',
    'њ': 'nj', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'ћ': 'ć', 'у': 'u',
    'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'č', 'џ': 'dž', 'ш': 'š',
    'щ': 'šč', 'ы': 'i', 'э': 'e', 'ю': 'ju', 'я': 'ja', 'ё': 'jo', 'й': 'j',
    'ъ': '', 'ь': '', 'і': 'i', 'ї': 'ji', 'є': 'je', 'ґ': 'g',
}
CYRILLIC_TO_LATIN = {**_CYRILLIC_LOWER, **{k.upper(): v.capitalize() for k, v in _CYRILLIC_LOWER.items()}}

DIACRITICS = {'č': 'c', 'ć': 'c', 'š': 's', 'ž': 'z', 'đ': 'dj'}

TAG_RE = re.compile(r"\[[^\]]*\]")
NON_WORD_RE = re.compile(r"[^\w\s]|_")


def cyrillic_to_latin(text):
    return "".join(CYRILLIC_TO_LATIN.get(char, char) for char in text)


def strip_diacritics(text):
    return "".join(DIACRITICS.get(char, char) for char in text)


def normalize(text, keep_diacritics=True):
    """Prepare a transcript for scoring, so only real speech differences count as errors.

    Applied identically to references and model output: NFC, Cyrillic to Latin, lowercase,
    drop [tags] like [smeh], drop apostrophes, turn other punctuation and symbols (emoji) into
    spaces, collapse whitespace. Dialect spellings and numbers are left as written.
    """
    text = unicodedata.normalize("NFC", text)
    text = cyrillic_to_latin(text).lower()
    text = TAG_RE.sub(" ", text)
    text = text.replace("'", "").replace("’", "")
    text = NON_WORD_RE.sub(" ", text)
    if not keep_diacritics:
        text = strip_diacritics(text)
    return " ".join(text.split())


def max_repeated_ngram(text, n=4):
    """How many times the most frequent n-word phrase occurs, a sign of Whisper looping."""
    words = normalize(text).split()
    counts = {}
    for i in range(len(words) - n + 1):
        gram = " ".join(words[i:i + n])
        counts[gram] = counts.get(gram, 0) + 1
    return max(counts.values(), default=0)
