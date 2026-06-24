"""Enable pgvector extension and sync JSON embeddings to vector column (PostgreSQL only)."""

from django.db import migrations


def enable_pgvector(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    try:
        schema_editor.execute("CREATE EXTENSION IF NOT EXISTS vector")
        schema_editor.execute(
            "ALTER TABLE assistant_evidencedocument "
            "ADD COLUMN IF NOT EXISTS embedding_vector vector(384)"
        )

        EvidenceDocument = apps.get_model("assistant", "EvidenceDocument")
        with schema_editor.connection.cursor() as cursor:
            for doc in EvidenceDocument.objects.exclude(embedding__isnull=True).iterator():
                if not doc.embedding or len(doc.embedding) != 384:
                    continue
                vec_literal = "[" + ",".join(str(v) for v in doc.embedding) + "]"
                cursor.execute(
                    "UPDATE assistant_evidencedocument SET embedding_vector = %s::vector WHERE id = %s",
                    [vec_literal, doc.id],
                )

        schema_editor.execute(
            """
            CREATE INDEX IF NOT EXISTS evidence_embedding_hnsw
            ON assistant_evidencedocument
            USING hnsw (embedding_vector vector_cosine_ops)
            """
        )
    except Exception:
        # Managed Postgres without pgvector (e.g. Railway) — JSON embeddings still work.
        return


def disable_pgvector(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("DROP INDEX IF EXISTS evidence_embedding_hnsw")
    schema_editor.execute(
        "ALTER TABLE assistant_evidencedocument DROP COLUMN IF EXISTS embedding_vector"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("assistant", "0002_assistantquery_organization_and_more"),
    ]

    operations = [
        migrations.RunPython(enable_pgvector, disable_pgvector),
    ]
