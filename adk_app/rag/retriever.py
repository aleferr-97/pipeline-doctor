import re
from pathlib import Path
from typing import Dict, List

DOCS_DIR = Path("docs/knowledge")

_STOP = {
    "the","a","an","of","and","or","to","in","on","for","with","by","is","are",
    "be","as","at","from","this","that","it","its","if","then","else","when","while",
}

def _tokenize(s: str) -> List[str]:
    s = s.lower()
    s = re.sub(r"[^a-z0-9_+.#=-]+", " ", s)
    return [w for w in s.split() if w and w not in _STOP]

def _split_chunks(text: str) -> List[str]:
    # split by double newline; keep medium chunks
    raw = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    buf = []
    size = 0
    for p in raw:
        plen = len(p)
        if size + plen > 800 and buf:
            chunks.append(" ".join(buf))
            buf, size = [p], plen
        else:
            buf.append(p)
            size += plen
    if buf:
        chunks.append(" ".join(buf))
    return chunks

def _score(query_terms: List[str], text: str) -> float:
    # simple overlap + mild phrase bonus
    tokens = _tokenize(text)
    if not tokens:
        return 0.0
    ts = set(tokens)
    overlap = sum(1 for t in query_terms if t in ts)
    phrase_bonus = 0.0
    qstr = " ".join(query_terms)
    if len(qstr) > 0 and " ".join(tokens).find(qstr) >= 0:
        phrase_bonus = 1.0
    return overlap + 0.5 * phrase_bonus

def build_query_from_metrics_and_issues(metrics: Dict, issues: List[Dict]) -> str:
    terms: List[str] = []
    # from issues
    for r in issues:
        t = r.get("issue","")
        if t:
            terms.extend(_tokenize(t))
        why = r.get("why","")
        if "skew" in why.lower():
            terms += ["spark","data","skew","aqe","skewJoin"]
        if "small file" in why.lower() or "file size" in why.lower():
            terms += ["delta","optimize","compaction","partition","file","size"]
    # from metrics
    if (metrics or {}).get("is_skew_suspect"):
        terms += ["spark","skew","aqe"]
    if (metrics or {}).get("is_small_files_problem"):
        terms += ["delta","optimize","compaction"]
    # a few stable keywords
    terms += ["spark.sql.adaptive.enabled","spark.sql.adaptive.skewJoin.enabled","Delta OPTIMIZE"]
    # dedup while preserving order
    seen = set()
    uniq = []
    for t in terms:
        if t not in seen:
            uniq.append(t)
            seen.add(t)
    return " ".join(uniq[:20])

def retrieve_snippets(query: str, k: int = 5) -> List[Dict]:
    """
    Scan docs/knowledge/*.md|*.txt, split into chunks, rank by simple token overlap.
    Returns: [{"source": "path#chunk_idx", "text": "...", "score": float}, ...] sorted desc.
    """
    if not DOCS_DIR.exists():
        return []
    q_terms = _tokenize(query)
    results: List[Dict] = []
    for p in sorted(DOCS_DIR.rglob("*")):
        if p.suffix.lower() not in {".md",".txt"}:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        chunks = _split_chunks(text)
        for i, ch in enumerate(chunks):
            s = _score(q_terms, ch)
            if s > 0:
                results.append({"source": f"{p.as_posix()}#{i}", "text": ch.strip(), "score": s})
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:k]
