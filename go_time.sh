#!/bin/bash
# Shortcut for manage.py that works locally and on the EB instance.
#   ./go_time.sh                                  # no command: run the dev server (locally)
#   ./go_time.sh fetch_cards --expansion 290      # any manage.py command and its options
#   ./go_time.sh test
# On EB (after `eb ssh`): bash /var/app/current/go_time.sh <command> [options]
set -euo pipefail
cd "$(dirname "$0")"

if [ -d /opt/elasticbeanstalk ]; then
  source "$(ls -d /var/app/venv/*/bin/activate | head -n1)"
  # EB environment properties aren't loaded in an SSH shell, so export them first.
  eval "$(sudo /opt/elasticbeanstalk/bin/get-config environment \
    | python -c 'import json, shlex, sys; print("\n".join(f"export {k}={shlex.quote(v)}" for k, v in json.load(sys.stdin).items()))')"
  PYTHON=python
elif [ -x .venv/Scripts/python.exe ]; then
  PYTHON=.venv/Scripts/python.exe  # Windows
else
  PYTHON=.venv/bin/python
fi

if [ $# -eq 0 ]; then
  set -- runserver
fi
exec "$PYTHON" manage.py "$@"
