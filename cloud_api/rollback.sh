#!/usr/bin/env bash
set -euo pipefail

systemctl disable --now w7-product-api@demo-shop-b.service w7-product-api@demo-shop-c.service || true
ufw --force delete allow 3120/tcp || true
ufw --force delete allow 3121/tcp || true
echo "Services stopped and new public firewall rules removed. Restore a named backup from /root/w7-product-api-backups only if one existed before deployment."
