#!/bin/sh
set -e

exec celery -A config worker --loglevel=INFO