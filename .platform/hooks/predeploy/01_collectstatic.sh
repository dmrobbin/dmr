#!/bin/bash
set -euo pipefail
cd /var/app/staging
source "$(ls -d /var/app/venv/*/bin/activate | head -n1)"
DJANGO_SECRET_KEY=collectstatic-only python manage.py collectstatic --noinput