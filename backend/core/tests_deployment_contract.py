from pathlib import Path

from django.test import SimpleTestCase


REPO_ROOT = Path(__file__).resolve().parents[2]


class RailwayDeploymentContractTests(SimpleTestCase):
    def test_web_startup_uses_strict_idempotent_initializer(self):
        startup = (REPO_ROOT / "deploy" / "railway" / "start.sh").read_text(encoding="utf-8")

        self.assertIn('INITIALIZE_DEMO_DATA:-false', startup)
        self.assertIn('python manage.py initialize_demo_data', startup)
        self.assertNotIn('python manage.py initialize_demo_data || true', startup)
        self.assertNotIn('python manage.py seed_data || true', startup)

    def test_worker_and_beat_process_commands_are_available(self):
        worker = (REPO_ROOT / "deploy" / "railway" / "worker.sh").read_text(encoding="utf-8")
        beat = (REPO_ROOT / "deploy" / "railway" / "beat.sh").read_text(encoding="utf-8")
        dockerfile = (REPO_ROOT / "Dockerfile.railway").read_text(encoding="utf-8")

        self.assertIn('celery -A config worker', worker)
        self.assertIn('celery -A config beat', beat)
        self.assertIn('COPY deploy/railway/worker.sh /worker.sh', dockerfile)
        self.assertIn('COPY deploy/railway/beat.sh /beat.sh', dockerfile)