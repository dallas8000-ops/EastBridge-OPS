"""Grounded LLM answers using retrieved evidence only."""

from __future__ import annotations

import logging

import httpx
from django.conf import settings

from assistant.embeddings import is_openai_key_configured, openai_api_key
from assistant.models import EvidenceDocument
from ingestion.services.retrieval import best_excerpt, tokenize

logger = logging.getLogger(__name__)


def should_use_llm() -> bool:
    configured = getattr(settings, "ANSWER_PROVIDER", "auto").lower()
    if configured == "template":
        return False
    if configured == "openai":
        return is_openai_key_configured()
    return is_openai_key_configured()


def generate_grounded_answer(
    question: str,
    matches: list[tuple[EvidenceDocument, object]],
) -> str | None:
    if not should_use_llm() or not matches:
        return None

    tokens = tokenize(question)
    evidence_blocks: list[str] = []
    for index, (doc, _score) in enumerate(matches, start=1):
        excerpt = best_excerpt(doc.content, tokens, max_len=1200)
        date_str = doc.published_at.isoformat() if doc.published_at else "undated"
        evidence_blocks.append(
            f"[{index}] {doc.title} ({date_str})\n"
            f"Source: {doc.source_url}\n"
            f"{excerpt}"
        )

    model = getattr(settings, "OPENAI_CHAT_MODEL", "gpt-4o-mini")
    system_prompt = (
        "You are EastBridge Ops Intelligence, a compliance and market-entry assistant for "
        "European companies operating in East Africa. Answer ONLY using the numbered evidence "
        "snippets provided. Cite sources inline as [1], [2], etc. Do not invent facts, URLs, "
        "dates, or requirements not supported by the evidence. If the evidence is partial, "
        "state what is known and what remains unverified."
    )
    user_prompt = f"Question: {question}\n\nEvidence:\n\n" + "\n\n".join(evidence_blocks)

    try:
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {openai_api_key()}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 900,
            },
            timeout=90.0,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.warning("LLM answer generation failed: %s", exc)
        return None
