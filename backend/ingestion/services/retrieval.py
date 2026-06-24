import re
from decimal import Decimal

from django.db import connection

from assistant.embeddings import (
    active_model_name,
    cosine_similarity,
    embed_text,
    resolve_provider,
)
from assistant.models import EvidenceDocument


STOPWORDS = {
    "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "had",
    "her", "was", "one", "our", "out", "day", "get", "has", "him", "his",
    "how", "its", "may", "new", "now", "old", "see", "way", "who", "did",
    "this", "that", "with", "from", "have", "been", "will", "would", "about",
}


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]{3,}", text.lower())
    return [w for w in words if w not in STOPWORDS]


def _current_embedding_model() -> str:
    provider = resolve_provider()
    return f"{provider}:{active_model_name(provider)}"


def _query_embedding(question: str) -> list[float]:
    vector, _, _ = embed_text(question)
    return vector


def _keyword_score(doc: EvidenceDocument, tokens: list[str]) -> Decimal:
    if not tokens:
        return Decimal("0")

    title_lower = doc.title.lower()
    content_lower = doc.content.lower()
    score = Decimal("0")

    for token in tokens:
        if token in title_lower:
            score += Decimal("3")
        if token in content_lower:
            score += Decimal("1")

    if doc.published_at:
        score += Decimal("0.5")
    if doc.category == "trade_procedure":
        score += Decimal("1")

    return score


def _vector_score(doc: EvidenceDocument, query_embedding: list[float]) -> Decimal:
    if not doc.embedding or not query_embedding:
        return Decimal("0")
    if doc.embedding_model and doc.embedding_model != _current_embedding_model():
        return Decimal("0")
    return Decimal(str(round(cosine_similarity(query_embedding, doc.embedding), 4)))


def _pgvector_search(
    question: str,
    country_code: str,
    limit: int,
) -> list[tuple[int, float]]:
    """Use pgvector cosine distance when extension and column are available."""
    if connection.vendor != "postgresql":
        return []

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'assistant_evidencedocument'
              AND column_name = 'embedding_vector'
            """
        )
        if not cursor.fetchone():
            return []

    query_embedding = _query_embedding(question)
    vector_literal = "[" + ",".join(str(v) for v in query_embedding) + "]"
    model_key = _current_embedding_model()

    if country_code:
        sql = """
            SELECT id, 1 - (embedding_vector <=> %s::vector) AS score
            FROM assistant_evidencedocument
            WHERE embedding_vector IS NOT NULL
              AND (embedding_model = %s OR embedding_model = '')
              AND country_code IN (%s, '')
            ORDER BY embedding_vector <=> %s::vector
            LIMIT %s
        """
        params = [vector_literal, model_key, country_code, vector_literal, limit]
    else:
        sql = """
            SELECT id, 1 - (embedding_vector <=> %s::vector) AS score
            FROM assistant_evidencedocument
            WHERE embedding_vector IS NOT NULL
              AND (embedding_model = %s OR embedding_model = '')
            ORDER BY embedding_vector <=> %s::vector
            LIMIT %s
        """
        params = [vector_literal, model_key, vector_literal, limit]

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return [(row[0], row[1]) for row in cursor.fetchall() if row[1] > 0.1]
    except Exception:
        return []


def search_evidence(
    question: str,
    country_code: str = "",
    limit: int = 5,
    min_score: Decimal = Decimal("0.35"),
) -> tuple[list[tuple[EvidenceDocument, Decimal]], str]:
    """
    Hybrid retrieval: pgvector (postgres) or JSON cosine + keyword scoring.
    Returns (matches, method_used).
    """
    tokens = tokenize(question)
    query_embedding = _query_embedding(question)
    provider = resolve_provider()

    pgvector_hits = _pgvector_search(question, country_code, limit * 2)
    if pgvector_hits:
        id_scores = {doc_id: Decimal(str(round(score, 4))) for doc_id, score in pgvector_hits}
        docs = EvidenceDocument.objects.filter(id__in=id_scores.keys())
        matches = [(doc, id_scores[doc.id]) for doc in docs]
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:limit], f"pgvector+{provider}"

    qs = EvidenceDocument.objects.all().order_by("-published_at", "-indexed_at")
    if country_code:
        qs = qs.filter(country_code__in=[country_code, ""])

    model_key = _current_embedding_model()
    scored: list[tuple[EvidenceDocument, Decimal]] = []
    for doc in qs[:500]:
        kw = _keyword_score(doc, tokens)
        vec = _vector_score(doc, query_embedding)
        if doc.embedding_model and doc.embedding_model != model_key:
            vec = Decimal("0")
        combined = (kw * Decimal("0.4")) + (vec * Decimal("10"))
        if combined >= min_score:
            scored.append((doc, combined))

    scored.sort(key=lambda x: x[1], reverse=True)
    method = f"hybrid+{provider}" if any(d.embedding for d, _ in scored[:limit]) else "keyword"
    return scored[:limit], method


def best_excerpt(content: str, tokens: list[str], max_len: int = 500) -> str:
    if len(content) <= max_len:
        return content

    lower = content.lower()
    for token in tokens:
        idx = lower.find(token)
        if idx >= 0:
            start = max(0, idx - 100)
            return content[start : start + max_len].strip()

    return content[:max_len].strip()


def synthesize_answer(question: str, matches: list[tuple[EvidenceDocument, Decimal]]) -> str:
    if not matches:
        return ""

    tokens = tokenize(question)
    primary, _top_score = matches[0]
    date_str = primary.published_at.isoformat() if primary.published_at else "undated"

    parts = [
        f"Based on {primary.title} (dated {date_str}, source: {primary.source_url})",
    ]

    if len(matches) > 1:
        secondary = matches[1][0]
        sec_date = secondary.published_at.isoformat() if secondary.published_at else "undated"
        parts.append(f" and {secondary.title} (dated {sec_date})")

    excerpt = best_excerpt(primary.content, tokens)
    parts.append(f": {excerpt}")

    if len(matches) > 1:
        parts.append(f" [{len(matches)} supporting source(s) cited.]")

    return "".join(parts)
