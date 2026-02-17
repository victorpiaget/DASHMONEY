This folder contains deployment templates (systemd units, scripts, env example).

## systemd (Ubuntu)
1) Create env file with secrets (do NOT commit):
- Copy `infra/env/backend.env.example` to `/etc/dashmoney/backend.env` and edit.

2) Install units:
- Copy `infra/systemd/*.service` and `*.timer` into `/etc/systemd/system/`
- Copy `infra/scripts/dashmoney-update-prices.sh` into `/usr/local/bin/`

3) Enable:
- `dashmoney-backend.service`
- `dashmoney-update-prices.timer`
