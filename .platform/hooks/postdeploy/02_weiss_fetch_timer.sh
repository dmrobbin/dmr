#!/bin/bash
# Install (or update) the timer that fetches new Weiss Schwarz sets every 2 hours.
# Amazon Linux 2023 has no cron, so this uses a systemd timer instead.
set -euo pipefail
cd /var/app/current

changed=0
for unit in weiss-fetch.service weiss-fetch.timer; do
  if ! cmp -s "deploy/systemd/$unit" "/etc/systemd/system/$unit"; then
    install -m 644 "deploy/systemd/$unit" "/etc/systemd/system/$unit"
    changed=1
  fi
done
if [ "$changed" = 1 ]; then
  systemctl daemon-reload
fi
# Starting an already-running timer is a no-op, so redeploys don't trigger extra runs.
systemctl enable --now weiss-fetch.timer

# Include the job's log in `eb logs` (tail) and `eb logs --all` (bundle).
touch /var/log/weiss-fetch.log
for kind in tail bundle; do
  dir=/opt/elasticbeanstalk/config/private/logtasks/$kind
  if [ -d "$dir" ]; then
    echo /var/log/weiss-fetch.log > "$dir/weiss-fetch.conf"
  fi
done
