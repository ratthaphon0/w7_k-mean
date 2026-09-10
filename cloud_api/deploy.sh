#!/usr/bin/env bash
set -euo pipefail

readonly stage_dir="${1:-/tmp/w7-product-apis-stage}"
readonly install_dir=/opt/w7-product-apis
readonly env_dir=/etc/w7-product-apis
readonly unit=/etc/systemd/system/w7-product-api@.service
readonly backup_root=/root/w7-product-api-backups
readonly backup_dir="${backup_root}/$(date -u +%Y%m%dT%H%M%SZ)"

for required in server.py demo-shop-b.json demo-shop-c.json demo-shop-b.env demo-shop-c.env w7-product-api@.service; do
  test -f "${stage_dir}/${required}" || { echo "missing staged file: ${required}" >&2; exit 66; }
done
for port in 3120 3121; do
  if ss -H -ltn "sport = :${port}" | grep -q .; then
    echo "port ${port} is already in use" >&2
    exit 65
  fi
done

install -d -o root -g root -m 0700 "$backup_dir"
for path in "$install_dir" "$env_dir" "$unit"; do
  if test -e "$path"; then
    case "$path" in
      "$install_dir") cp -a "$path" "${backup_dir}/opt-w7-product-apis" ;;
      "$env_dir") cp -a "$path" "${backup_dir}/etc-w7-product-apis" ;;
      "$unit") cp -a "$path" "${backup_dir}/w7-product-api@.service" ;;
    esac
  fi
done
ufw status numbered >"${backup_dir}/ufw-status.before.txt"
systemctl is-enabled 'w7-product-api@demo-shop-b.service' >"${backup_dir}/service-enabled.before.txt" 2>&1 || true
systemctl is-active 'w7-product-api@demo-shop-b.service' >"${backup_dir}/service-active.before.txt" 2>&1 || true

install -d -o root -g root -m 0755 "$install_dir" "$env_dir"
install -o root -g root -m 0755 "${stage_dir}/server.py" "${install_dir}/server.py"
install -o root -g root -m 0644 "${stage_dir}/demo-shop-b.json" "${install_dir}/demo-shop-b.json"
install -o root -g root -m 0644 "${stage_dir}/demo-shop-c.json" "${install_dir}/demo-shop-c.json"
install -o root -g root -m 0644 "${stage_dir}/demo-shop-b.env" "${env_dir}/demo-shop-b.env"
install -o root -g root -m 0644 "${stage_dir}/demo-shop-c.env" "${env_dir}/demo-shop-c.env"
install -o root -g root -m 0644 "${stage_dir}/w7-product-api@.service" "$unit"

systemctl daemon-reload
systemctl enable --now w7-product-api@demo-shop-b.service w7-product-api@demo-shop-c.service
ufw allow 3120/tcp comment 'W7 demo product API B'
ufw allow 3121/tcp comment 'W7 demo product API C'

for attempt in $(seq 1 20); do
  if curl --fail --silent http://127.0.0.1:3120/health >/dev/null \
    && curl --fail --silent http://127.0.0.1:3121/health >/dev/null; then
    break
  fi
  if test "$attempt" -eq 20; then
    echo "services did not become healthy" >&2
    exit 1
  fi
  sleep 0.25
done
curl --fail --silent --show-error http://127.0.0.1:3120/health; echo
curl --fail --silent --show-error http://127.0.0.1:3121/health; echo
echo "backup_dir=${backup_dir}"
