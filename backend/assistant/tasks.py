from celery import shared_task
from django.conf import settings
from django.db import connection

from assistant.embeddings import EMBEDDING_DIM, active_model_name, embed_text, resolve_provider
from assistant.models import EvidenceDocument


def _sync_pgvector(doc_id: int, embedding: list[float]) -> None:
    if connection.vendor != "postgresql" or not embedding:
        return
    if len(embedding) != EMBEDDING_DIM:
        return
    vec_literal = "[" + ",".join(str(v) for v in embedding) + "]"
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE assistant_evidencedocument SET embedding_vector = %s::vector WHERE id = %s",
                [vec_literal, doc_id],
            )
    except Exception:
        pass


def _needs_reembed(doc: EvidenceDocument, force: bool = False) -> bool:
    if force:
        return True
    expected_model = f"{resolve_provider()}:{active_model_name(resolve_provider())}"
    if doc.embedding_model != expected_model:
        return True
    if not doc.embedding or doc.embedding_dims != EMBEDDING_DIM:
        return True
    return False


def embed_document(doc: EvidenceDocument, force: bool = False) -> bool:
    if not _needs_reembed(doc, force=force):
        return False

    text = f"{doc.title}\n{doc.content}"
    provider = resolve_provider()
    embedding, used_provider, model = embed_text(
        text,
        provider=provider,
        allow_fallback=provider == "hash",
    )
    model_key = f"{used_provider}:{model}"

    doc.embedding = embedding
    doc.embedding_dims = len(embedding)
    doc.embedding_model = model_key
    doc.save(update_fields=["embedding", "embedding_dims", "embedding_model"])
    _sync_pgvector(doc.id, embedding)
    return True


def embed_all_evidence(force: bool = False) -> dict:
    provider = resolve_provider()
    model = active_model_name(provider)
    embedded = 0
    skipped = 0

    for doc in EvidenceDocument.objects.iterator():
        if embed_document(doc, force=force):
            embedded += 1
        else:
            skipped += 1

    return {
        "embedded": embedded,
        "skipped": skipped,
        "provider": provider,
        "model": model,
        "dimensions": EMBEDDING_DIM,
    }


@shared_task
def embed_evidence_task(force: bool = False):
    return embed_all_evidence(force=force)
