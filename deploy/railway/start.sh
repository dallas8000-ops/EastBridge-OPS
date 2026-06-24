#!/bin/sh
set -e

PORT="${PORT:-8080}"
# Django ALLOWED_HOSTS must accept this Host on proxied health/API requests.
DJANGO_HOST="${RAILWAY_PUBLIC_DOMAIN:-${CUSTOM_DOMAIN:-127.0.0.1}}"

# Always migrate at startup (idempotent). railway.toml preDeployCommand is an extra pass
# when DATABASE_URL is available in the pre-deploy container — do not rely on it alone.
python manage.py migrate --noinput

if [ "${SEED_ON_DEPLOY:-false}" = "true" ]; then
  python manage.py seed_data || true
fi

gunicorn config.wsgi:application \
  --bind 127.0.0.1:8000 \
  --workers 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - &

# Wait until gunicorn serves health before nginx proxies Railway's probe.
until python -c "
import urllib.request
urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/', timeout=2)
" 2>/dev/null; do
  sleep 1
done

cat > /etc/nginx/conf.d/default.conf <<NGINX
server {
    listen ${PORT};
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    client_max_body_size 25M;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location = /api/v1/health/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host ${DJANGO_HOST};
        proxy_set_header X-Forwarded-Proto https;
        proxy_connect_timeout 5s;
        proxy_read_timeout 10s;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_read_timeout 120s;
        proxy_connect_timeout 30s;
    }

    location /admin/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /media/ {
        alias /app/media/;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
NGINX

exec nginx -g 'daemon off;'
