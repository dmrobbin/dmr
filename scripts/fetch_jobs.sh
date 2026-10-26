#!/bin/bash
# Pull new job leads into the database. Run on the EB instance after `eb ssh`:
#   bash /var/app/current/scripts/fetch_jobs.sh [--dry-run] [--query "..."] ...
set -euo pipefail
cd /var/app/current
source "$(ls -d /var/app/venv/*/bin/activate | head -n1)"
# EB environment properties aren't loaded in an SSH shell, so export them first.
eval "$(sudo /opt/elasticbeanstalk/bin/get-config environment \
  | python -c 'import json, shlex, sys; print("\n".join(f"export {k}={shlex.quote(v)}" for k, v in json.load(sys.stdin).items()))')"
python manage.py fetch_jobs "$@"
