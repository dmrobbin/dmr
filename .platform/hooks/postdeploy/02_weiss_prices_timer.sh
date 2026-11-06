#!/bin/bash
# Install (or update) the timer that updates Weiss Schwarz card prices once a day.
# Amazon Linux 2023 has no cron, so this uses a systemd timer instead.
set -euo pipefail
cd /var/app/current

# Retire the old hourly weiss-fetch timer (it also looked for new sets) if this instance still has it.
if [ -e /etc/systemd/system/weiss-fetch.timer ] || [ -e /etc/systemd/system/weiss-fetch.service ]; then
  systemctl disable --now weiss-fetch.timer || true
  systemctl stop weiss-fetch.service || true
  rm -f /etc/systemd/system/weiss-fetch.timer /etc/systemd/system/weiss-fetch.service
  rm -f /opt/elasticbeanstalk/config/private/logtasks/{tail,bundle}/weiss-fetch.conf
  systemctl daemon-reload
fi

changed=0
for unit in weiss-prices.service weiss-prices.timer; do
  if ! cmp -s "deploy/systemd/$unit" "/etc/systemd/system/$unit"; then
    install -m 644 "deploy/systemd/$unit" "/etc/systemd/system/$unit"
    changed=1
  fi
done
if [ "$changed" = 1 ]; then
  systemctl daemon-reload
fi
# Starting an already-running timer is a no-op, so redeploys don't trigger extra runs.
systemctl enable --now weiss-prices.timer

# Include the job's log in `eb logs` (tail) and `eb logs --all` (bundle).
touch /var/log/weiss-prices.log
for kind in tail bundle; do
  dir=/opt/elasticbeanstalk/config/private/logtasks/$kind
  if [ -d "$dir" ]; then
    echo /var/log/weiss-prices.log > "$dir/weiss-prices.conf"
  fi
done
