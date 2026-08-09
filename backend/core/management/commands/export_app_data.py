"""Export committed JSON fixtures — the app image shipped in GitHub zip downloads."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from io import StringIO

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

FIXTURE_DIR = Path(__file__).resolve().parents[3] / "fixtures"

FIXED_TIMESTAMP = "2026-01-01T00:00:00Z"
FIXED_DEMO_PASSWORD = (
    "pbkdf2_sha256$1000000$eastbridgedemosalt$fecsud40/HTcajUZIgCJk7bHWzcvwv1biwupklmzTZQ="
)
VOLATILE_FIELDS = frozenset(
    {
        "password",
        "date_joined",
        "last_login",
        "created_at",
        "updated_at",
        "joined_at",
        "uploaded_at",
        "last_synced_at",
        "detected_at",
        "indexed_at",
        "fetched_at",
        "last_checked_at",
    }
)

# Load order for loaddata (foreign keys).
FIXTURE_EXPORTS: list[tuple[str, list[str]]] = [
    (
        "initial_01_core.json",
        ["core.country", "core.datasource", "playbooks.industry"],
    ),
    (
        "initial_02_accounts.json",
        ["auth.user", "accounts.organization", "accounts.organizationmembership"],
    ),
    (
        "initial_03_vendors.json",
        ["vendors.vendor", "vendors.vendorcontractrecord", "vendors.vendorpaymentrecord"],
    ),
    (
        "initial_04_regulatory.json",
        ["regulatory.regulatorychange", "regulatory.changealertsubscription"],
    ),
    (
        "initial_05_intelligence.json",
        ["intelligence.economicindicator", "intelligence.countryrisksnapshot"],
    ),
    (
        "initial_06_trade.json",
        ["trade.tradeprocedure", "trade.tradeprocedurestep"],
    ),
    (
        "initial_07_evidence.json",
        ["assistant.evidencedocument"],
    ),
]


def _normalize_records(records: list) -> list:
    """Stable timestamps/password so fixture checksums do not drift between exports."""
    normalized = []
    for record in records:
        entry = dict(record)
        fields = dict(entry.get("fields", {}))
        if entry.get("model") == "auth.user":
            fields["password"] = FIXED_DEMO_PASSWORD
        if entry.get("model") == "assistant.evidencedocument" and fields.get("embedding"):
            fields["embedding"] = [round(float(value), 8) for value in fields["embedding"]]
        for key in list(fields.keys()):
            if key in VOLATILE_FIELDS and fields[key] is not None:
                if key == "password":
                    continue
                fields[key] = FIXED_TIMESTAMP
        entry["fields"] = fields
        normalized.append(entry)
    normalized.sort(key=lambda item: (item.get("model", ""), item.get("pk", 0)))
    return normalized


def _dump_fixture(labels: list[str]) -> str:
    buffer = StringIO()
    call_command("dumpdata", *labels, indent=2, stdout=buffer)
    records = json.loads(buffer.getvalue())
    return json.dumps(_normalize_records(records), indent=2, sort_keys=True) + "\n"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _count_records(path: Path) -> int:
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    return len(data) if isinstance(data, list) else 0


class Command(BaseCommand):
    help = "Export backend/fixtures/initial_*.json — the data image in every GitHub zip."

    def add_arguments(self, parser):
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Rebuild a clean SQLite DB from seed commands, then export (deterministic).",
        )
        parser.add_argument(
            "--check",
            action="store_true",
            help="Fail if committed fixtures differ from a fresh --refresh export.",
        )
        parser.add_argument(
            "--with-live-ingest",
            action="store_true",
            help="With --refresh, also run live ingest (network). Default is offline snapshot only.",
        )

    def handle(self, *args, **options):
        FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

        if options["check"]:
            self._check_fixtures(options["with_live_ingest"])
            return

        if options["refresh"]:
            self._refresh_canonical_dataset(options["with_live_ingest"])

        self._export_fixtures()
        self.stdout.write(self.style.SUCCESS(f"Exported app data to {FIXTURE_DIR}"))

    def _reset_local_sqlite(self) -> None:
        db = settings.DATABASES["default"]
        if "sqlite" not in db["ENGINE"]:
            raise CommandError(
                "--refresh requires SQLite (empty DATABASE_URL). "
                "Use a local dev DB or run export without --refresh on Postgres."
            )
        db_path = Path(db["NAME"])
        if db_path.exists():
            db_path.unlink()
        call_command("migrate", "--noinput", verbosity=0)

    def _refresh_canonical_dataset(self, with_live_ingest: bool) -> None:
        self.stdout.write("Refreshing canonical app dataset...")
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        self._reset_local_sqlite()
        os.environ.setdefault("EMBEDDING_PROVIDER", "hash")

        steps = [
            ("seed_data", {}),
            ("seed_demo_org", {}),
            ("sync_trade_procedures", {"offline": True}),
        ]
        if with_live_ingest:
            steps.append(("ingest", {"target": "all"}))
        else:
            steps.append(("seed_offline_snapshot", {}))

        steps.extend(
            [
                ("embed_evidence", {"force": True}),
                ("verify_data", {}),
            ]
        )

        for command, kwargs in steps:
            self.stdout.write(f"  -> {command}")
            call_command(command, **kwargs)

    def _export_fixtures(self) -> None:
        manifest_files: list[dict] = []

        for filename, labels in FIXTURE_EXPORTS:
            target = FIXTURE_DIR / filename
            target.write_text(_dump_fixture(labels), encoding="utf-8")
            manifest_files.append(
                {
                    "file": filename,
                    "models": labels,
                    "records": _count_records(target),
                    "sha256": _sha256(target),
                }
            )

        # Retire legacy single-file export if present.
        legacy = FIXTURE_DIR / "initial_core.json"
        if legacy.exists():
            legacy.unlink()

        manifest = {
            "exported_at": FIXED_TIMESTAMP,
            "description": "Committed app image for GitHub zip downloads. Regenerate with: npm run export:fixtures",
            "files": manifest_files,
        }
        manifest_path = FIXTURE_DIR / "MANIFEST.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    def _check_fixtures(self, with_live_ingest: bool) -> None:
        import tempfile

        from django.db import connections

        committed = {p.name: _sha256(p) for p in FIXTURE_DIR.glob("initial_*.json")}

        with tempfile.TemporaryDirectory() as tmp:
            original_name = settings.DATABASES["default"]["NAME"]
            tmp_db = Path(tmp) / "check.sqlite3"
            settings.DATABASES["default"]["NAME"] = str(tmp_db)

            try:
                self._refresh_canonical_dataset(with_live_ingest)
                for filename, labels in FIXTURE_EXPORTS:
                    out = Path(tmp) / filename
                    out.write_text(_dump_fixture(labels), encoding="utf-8")
                    if filename not in committed:
                        raise CommandError(f"Missing committed fixture: {filename}")
                    if _sha256(out) != committed[filename]:
                        raise CommandError(
                            f"Fixture drift: {filename} is out of date. "
                            "Run: npm run export:fixtures"
                        )
            finally:
                connections.close_all()
                settings.DATABASES["default"]["NAME"] = original_name

        self.stdout.write(self.style.SUCCESS("Committed fixtures match canonical app image."))
