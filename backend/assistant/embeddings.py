"""
Embedding providers: fastembed (default), OpenAI (optional), hash fallback.

Configure via environment:
  EMBEDDING_PROVIDER=fastembed|openai|hash|auto
  EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
  OPENAI_API_KEY=sk-...
  EMBEDDING_DIM=384
"""

from __future__ import annotations

import logging
import math
import re
from functools import lru_cache

from django.conf import settings

logger = logging.getLogger(__name__)

EMBEDDING_DIM = getattr(settings, "EMBEDDING_DIM", 384)

_OPENAI_PLACEHOLDER_KEYS = frozenset(
    {"", "sk-...", "sk-your-key-here", "changeme", "your-openai-api-key"}
)


def openai_api_key() -> str:
    return getattr(settings, "OPENAI_API_KEY", "").strip()


def is_openai_key_configured() -> bool:
    key = openai_api_key()
    if not key or key in _OPENAI_PLACEHOLDER_KEYS:
        return False
    if key.endswith("..."):
        return False
    return key.startswith("sk-") and len(key) >= 20


def _fastembed_available() -> bool:
    try:
        import fastembed  # noqa: F401

        return True
    except ImportError:
        return False


def provider_config_error() -> str | None:
    """Return a user-facing error when embedding config cannot run as requested."""
    configured = getattr(settings, "EMBEDDING_PROVIDER", "auto").lower()
    if configured == "openai" and not is_openai_key_configured():
        return (
            "EMBEDDING_PROVIDER=openai but OPENAI_API_KEY is missing or still a placeholder. "
            "Set a real key in .env (https://platform.openai.com/api-keys), "
            "or use EMBEDDING_PROVIDER=fastembed for free local embeddings."
        )
    if configured == "fastembed" and not _fastembed_available():
        return (
            "EMBEDDING_PROVIDER=fastembed but fastembed is not installed. "
            "Run: pip install fastembed"
        )
    return None


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]{3,}", text.lower())


def _embed_hash(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    vec = [0.0] * dim
    if not text.strip():
        return vec

    for token in _tokenize(text):
        vec[hash(token) % dim] += 1.0

    for i in range(len(text) - 2):
        tri = text[i : i + 3].lower()
        if tri.isalnum():
            vec[hash(tri) % dim] += 0.3

    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


@lru_cache(maxsize=1)
def _get_fastembed_model():
    from fastembed import TextEmbedding

    model_name = getattr(settings, "EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    logger.info("Loading fastembed model: %s", model_name)
    return TextEmbedding(model_name=model_name)


def _embed_fastembed(text: str) -> list[float]:
    model = _get_fastembed_model()
    vector = list(model.embed([text[:8000]]))[0]
    return vector.tolist() if hasattr(vector, "tolist") else list(vector)


def _embed_openai(text: str) -> list[float]:
    import httpx

    if not is_openai_key_configured():
        raise ValueError("OPENAI_API_KEY is not configured")

    api_key = openai_api_key()

    model = getattr(settings, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    dim = EMBEDDING_DIM

    response = httpx.post(
        "https://api.openai.com/v1/embeddings",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "input": text[:8000],
            "dimensions": dim,
        },
        timeout=60.0,
    )
    response.raise_for_status()
    return response.json()["data"][0]["embedding"]


def resolve_provider() -> str:
    """Pick the best available provider based on settings."""
    configured = getattr(settings, "EMBEDDING_PROVIDER", "auto").lower()

    if configured == "hash":
        return "hash"

    if configured == "openai":
        if is_openai_key_configured():
            return "openai"
        logger.warning("EMBEDDING_PROVIDER=openai but OPENAI_API_KEY missing/invalid; using fallback")
        return _fallback_after_openai()

    if configured == "fastembed":
        return "fastembed" if _fastembed_available() else "hash"

    # auto: prefer fastembed, then openai, then hash
    if _fastembed_available():
        return "fastembed"
    if is_openai_key_configured():
        return "openai"
    return "hash"


def _fallback_after_openai() -> str:
    if _fastembed_available():
        return "fastembed"
    return "hash"


def active_model_name(provider: str) -> str:
    if provider == "openai":
        return getattr(settings, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    if provider == "fastembed":
        return getattr(settings, "EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    return "hash-v1"


def embed_text(
    text: str,
    provider: str | None = None,
    *,
    allow_fallback: bool = True,
) -> tuple[list[float], str, str]:
    """
    Embed text and return (vector, provider, model_name).
    """
    if not text or not text.strip():
        return [0.0] * EMBEDDING_DIM, "hash", "hash-v1"

    provider = provider or resolve_provider()

    try:
        if provider == "openai":
            vector = _embed_openai(text)
        elif provider == "fastembed":
            vector = _embed_fastembed(text)
        else:
            vector = _embed_hash(text)
            provider = "hash"
    except Exception as exc:
        if not allow_fallback:
            raise
        logger.warning("Embedding failed with %s: %s — using hash fallback", provider, exc)
        vector = _embed_hash(text)
        provider = "hash"

    return vector, provider, active_model_name(provider)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
