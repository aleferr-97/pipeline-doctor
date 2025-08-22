import re
from pathlib import Path
from typing import Dict, List, Iterable

# Local knowledge folder”
DOCS_DIR = Path("docs/knowledge")

# Stopwords
_STOP = {
    "the","a","an","of","and","or","to","in","on","for","with","by","is","are",
    "be","as","at","from","this","that","it","its","if","then","else","when","while",
}

def _tokenize(s: str) -> List[str]:
    """
    Tokenization:
    - lowercasing
    - alphanumeric char remove, keeping useful symbols (._+:#=-)
    - split
    - stopword filter
    """
    s = s.lower()
    s = re.sub(r"[^a-z0-9_+.#=:-]+", " ", s)  # consenti ., _, +, :, #, =, - per chiavi tipo spark.sql.x
    return [w for w in s.split() if w and w not in _STOP]

def _split_chunks(text: str, max_chunk_chars: int = 800) -> List[str]:
    """
    Split a document in paragraphs, and then it builds
    chunks, merging adjacent paragraphs.
    It's useful to not build huge blobs
    """
    raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    buf: List[str] = []
    size = 0

    for p in raw_paragraphs:
        plen = len(p)
        if size + plen > max_chunk_chars and buf:
            chunks.append(" ".join(buf))
            buf, size = [p], plen
        else:
            buf.append(p)
            size += plen

    if buf:
        chunks.append(" ".join(buf))
    return chunks

def _score(query_terms: List[str], text: str) -> float:
    """
    Scoring system:
    - overlap = how much words of query are in the chunk
    - bonus (+0.5) if the query string is ordered in the tokenized chunk
    """
    tokens = _tokenize(text)
    if not tokens:
        return 0.0
    ts = set(tokens)
    overlap = sum(1 for t in query_terms if t in ts)

    phrase_bonus = 0.0
    qstr = " ".join(query_terms)
    if qstr and " ".join(tokens).find(qstr) >= 0:
        phrase_bonus = 0.5

    return overlap + phrase_bonus

def build_query_from_metrics_and_issues(metrics: Dict, issues: List[Dict]) -> str:
    """
    It builds a readable query, using useful terms from:
    - issues
    - metrics (is_skew_suspect, is_small_files_problem)
    - some stable keyword
    """
    terms: List[str] = []

    for r in issues:
        t = r.get("issue", "")
        if t:
            terms.extend(_tokenize(t))
        why = r.get("why", "")
        low_why = why.lower()
        if "skew" in low_why:
            terms += ["spark", "data", "skew", "aqe", "skewJoin"]
        if "small file" in low_why or "file size" in low_why:
            terms += ["delta", "optimize", "compaction", "partition", "file", "size"]

    if (metrics or {}).get("is_skew_suspect"):
        terms += ["spark", "skew", "aqe"]
    if (metrics or {}).get("is_small_files_problem"):
        terms += ["delta", "optimize", "compaction"]

    terms += [
        "spark.sql.adaptive.enabled",
        "spark.sql.adaptive.skewJoin.enabled",
        "Delta", "OPTIMIZE"
    ]

    seen = set()
    uniq: List[str] = []
    for t in terms:
        if t not in seen:
            uniq.append(t)
            seen.add(t)
    return " ".join(uniq[:20])

def _iter_knowledge_files(allowed_exts: Iterable[str]) -> Iterable[Path]:
    if not DOCS_DIR.exists():
        return []
    for p in sorted(DOCS_DIR.rglob("*")):
        if p.suffix.lower() in allowed_exts and p.is_file():
            yield p

def retrieve_snippets(query: str, k: int = 5, *, min_score: float = 0.0,
                      allowed_exts: Iterable[str] = (".md", ".txt"),
                      max_chunk_chars: int = 800) -> List[Dict]:
    """
    Takes top‑k most relevant chunks, based on the query.

    Args:
        query
        k: max snippets number
        min_score: minimum threshold to include a snippet
        allowed_exts
        max_chunk_chars

    Returns:
        [{"source": "path#chunk_idx", "text": "...", "score": float}, ...] ordered by increasing score
    """
    q_terms = _tokenize(query)
    results: List[Dict] = []

    for p in _iter_knowledge_files(allowed_exts):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        chunks = _split_chunks(text, max_chunk_chars=max_chunk_chars)
        for i, ch in enumerate(chunks):
            s = _score(q_terms, ch)
            if s >= min_score:
                results.append({
                    "source": f"{p.as_posix()}#{i}",
                    "text": ch.strip(),
                    "score": s
                })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:k]