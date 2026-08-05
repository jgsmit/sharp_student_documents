"""Utilities for cleaning document preview text.

PyPDF2 (and pypdf) PDF text extraction often produces artifacts:
stray whitespace, page numbers fused onto words, letter-spaced text,
and words split into fragments.  ``normalize_preview_text`` cleans the
extracted text before it is stored/displayed.
"""
import re

_STOPWORDS = frozenset(
    """
    a an the and or but nor if of in on at to for from with by as
    is are was were be been being am it its this that these those
    there here which who whom whose when where while than then them
    they their theirs you your yours he him his she her hers we us
    our ours i me my mine do does did have has had not no so such
    can could will would shall should may might must about into upon
    under over after before between through during without against
    out up down off again further once also very too just now how
    what why both each few more most other some only own same et
    """.split()
)

# Lowercase tokens that are actually word fragments (suffixes) even
# though they occur frequently in the corpus, e.g. "Reson *ance*".
_SUFFIX_FRAGMENTS = frozenset(
    {"ance", "tions", "tion", "ing", "nction", "able"}
)

# Fallback known words used when no corpus-derived set is supplied.
_DEFAULT_KNOWN_WORDS = frozenset(
    """
    exam exams test tests question questions answer answers correct
    verified answers update updated latest new final practice review
    comprehensive nursing medical study guide studies bank certification
    with detailed actual real complete questions answers and the for
    course code university grade graded pass guarantee guaranteed pass
    fundamental fundamentals pharmacology psychiatric mental health
    edition version new complete objective assessment exit predictor
    hesi ati rn pn nclex cleet posc1010 wgu chamberlain pharmacology
    exam answers verified correct answers nursing medical study guide
    certification actual complete questions bank final exam study guide
    practice questions verified answers detailed answers correct answers
    """.split()
)


def _collapse_whitespace(text):
    return re.sub(r"\s+", " ", text.replace("\u00a0", " ")).strip()


def _split_digit_letter(text):
    return re.sub(r"(?<=[0-9])(?=[A-Za-z])", " ", text)


def _strip_fused_leading_number(text):
    if re.match(r"^\d+[A-Za-z]", text):
        return re.sub(r"^\d{1,3}\s+", "", text)
    return text


def _strip_leading_pagenum(text):
    # Drop a leftover page number ("70 Christopher ...") when a
    # Capitalized word of 8+ letters follows.
    return re.sub(r"^\d{1,3}\s+(?=[A-Z][a-z]{7,})", "", text)


def _fix_space_before_punctuation(text):
    text = re.sub(r"\s+([.,;:!?)%])", r"\1", text)
    return re.sub(r"(?<=[A-Za-z]) - (?=[A-Za-z])", "-", text)


def _should_merge(prev, cur, known_words):
    if not prev or not cur:
        return False
    if not prev.isalpha() or not cur.isalpha():
        return False
    if cur.lower() in _STOPWORDS or prev.lower() in _STOPWORDS:
        return False
    if cur.lower() in known_words and cur.lower() not in _SUFFIX_FRAGMENTS:
        return False
    if len(prev) + len(cur) > 16:
        return False
    if prev.isupper() and cur.isupper():
        return len(prev) <= 9 and len(cur) <= 9
    if prev[0].isupper() and cur.islower():
        return len(prev) <= 8 and len(cur) <= 9
    return False


def _merge_fragments(text, known_words):
    out = []
    for token in text.split(" "):
        if out and _should_merge(out[-1], token, known_words):
            out[-1] = out[-1] + token
        else:
            out.append(token)
    return " ".join(out)


def normalize_preview_text(text, known_words=None):
    """Return a cleaned version of ``text``.

    ``known_words`` is a set of lowercase tokens that should never be
    merged into a preceding word fragment.  When omitted, a static
    fallback set is used (adequate for newly uploaded documents).
    """
    if not text:
        return text or ""

    known_words = known_words or _DEFAULT_KNOWN_WORDS

    cleaned = _collapse_whitespace(text)
    # Detect a page number fused onto the first word *before* the
    # digit/letter split makes it look like two separate tokens.
    starts_fused = bool(re.match(r"^\d+[A-Za-z]", cleaned))
    cleaned = _split_digit_letter(cleaned)
    if starts_fused:
        cleaned = _strip_fused_leading_number(cleaned)
    cleaned = _fix_space_before_punctuation(cleaned)
    cleaned = _merge_fragments(cleaned, known_words)
    cleaned = _strip_leading_pagenum(cleaned)
    return cleaned
