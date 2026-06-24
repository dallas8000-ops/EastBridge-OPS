import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-dev-only-change-me")
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

_allowed_hosts = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
for _railway_host in (
    os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip(),
    os.getenv("CUSTOM_DOMAIN", "").strip(),
):
    if _railway_host and _railway_host not in _allowed_hosts:
        _allowed_hosts.append(_railway_host)
if os.getenv("RAILWAY_ENVIRONMENT"):
    for _railway_suffix in ("healthcheck.railway.app", ".railway.app"):
        if _railway_suffix not in _allowed_hosts:
            _allowed_hosts.append(_railway_suffix)
ALLOWED_HOSTS = _allowed_hosts

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "accounts",
    "core",
    "regulatory",
    "playbooks",
    "vendors",
    "intelligence",
    "assistant",
    "ingestion",
    "trade",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres"):
    from urllib.parse import urlparse

    parsed = urlparse(DATABASE_URL)
    db_config = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/") or os.getenv("POSTGRES_DB", "eastbridge"),
        "USER": parsed.username or os.getenv("POSTGRES_USER", "eastbridge"),
        "PASSWORD": parsed.password or os.getenv("POSTGRES_PASSWORD", "eastbridge"),
        "HOST": parsed.hostname or os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": str(parsed.port or os.getenv("POSTGRES_PORT", "5432")),
    }
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("DATABASE_SSL_REQUIRE", "").lower() in (
        "true",
        "1",
        "yes",
    ):
        db_config["OPTIONS"] = {"sslmode": "require"}
    DATABASES = {"default": db_config}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]

_csrf_origins = [
    o.strip()
    for o in os.getenv(
        "CSRF_TRUSTED_ORIGINS",
        ",".join(CORS_ALLOWED_ORIGINS),
    ).split(",")
    if o.strip()
]
for _host in (os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip(), os.getenv("CUSTOM_DOMAIN", "").strip()):
    if _host:
        _origin = f"https://{_host}"
        if _origin not in _csrf_origins:
            _csrf_origins.append(_origin)
CSRF_TRUSTED_ORIGINS = _csrf_origins

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    _ssl_redirect = os.getenv("SECURE_SSL_REDIRECT", "").lower()
    if _ssl_redirect in ("true", "1", "yes"):
        SECURE_SSL_REDIRECT = True
    elif _ssl_redirect in ("false", "0", "no"):
        SECURE_SSL_REDIRECT = False
    elif os.getenv("RAILWAY_ENVIRONMENT"):
        # Railway probes health over plain HTTP; redirect breaks the check (301 vs 200).
        SECURE_SSL_REDIRECT = False

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}

from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=12),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

EAC_COUNTRIES = ["UG", "KE", "TZ", "RW", "BI", "SS"]

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "alerts@eastbridge.local")
ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "")

# Embeddings: fastembed (local), openai (API), hash (fallback)
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "auto")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "384"))

# Assistant answers: auto uses OpenAI when key set, else template synthesis
ANSWER_PROVIDER = os.getenv("ANSWER_PROVIDER", "auto")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    "ingest-regulatory-sources": {
        "task": "ingestion.tasks.run_regulatory_ingestion",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    "sync-economic-indicators": {
        "task": "ingestion.tasks.run_economic_ingestion",
        "schedule": crontab(minute=30, hour="2"),
    },
    "sync-trade-procedures": {
        "task": "trade.tasks.sync_trade_procedures_task",
        "schedule": crontab(minute=0, hour="3"),
    },
    "embed-evidence": {
        "task": "assistant.tasks.embed_evidence_task",
        "schedule": crontab(minute=15, hour="4"),
    },
}
