from django.core.management.base import BaseCommand, CommandError

from assistant.embeddings import active_model_name, provider_config_error, resolve_provider
from assistant.tasks import embed_all_evidence


class Command(BaseCommand):
    help = "Generate semantic embeddings for all evidence documents."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-embed all documents even if model unchanged.",
        )

    def handle(self, *args, **options):
        config_error = provider_config_error()
        if config_error:
            raise CommandError(config_error)

        provider = resolve_provider()
        model = active_model_name(provider)
        self.stdout.write(f"Provider: {provider} ({model})")

        result = embed_all_evidence(force=options["force"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Embedded {result['embedded']} documents ({result['skipped']} unchanged) "
                f"— {result['dimensions']}d via {result['provider']}"
            )
        )
