#!/bin/bash
# Run this ONCE on a fresh EC2 instance to bootstrap ConfDex.
# Usage: bash setup-server.sh <server-ip> <admin-password>
#
# Example:
#   bash scripts/setup-server.sh 203.0.113.10 MyPassword123

set -euo pipefail

SERVER_IP="${1:?Usage: $0 <server-ip> <admin-password> [path-to-key.pem]}"
ADMIN_PASSWORD="${2:?Usage: $0 <server-ip> <admin-password> [path-to-key.pem]}"
PEM_KEY="${3:-}"
SSH_USER="ubuntu"   # change to "ec2-user" if using Amazon Linux

SSH_OPTS="-o StrictHostKeyChecking=no"
if [ -n "$PEM_KEY" ]; then
  chmod 400 "$PEM_KEY"
  SSH_OPTS="$SSH_OPTS -i $PEM_KEY"
fi

echo "==> Bootstrapping ConfDex on $SERVER_IP"

ssh $SSH_OPTS "$SSH_USER@$SERVER_IP" bash <<REMOTE
set -euo pipefail

echo "--- Installing Docker ---"
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker \$USER
newgrp docker || true

echo "--- Creating app directory ---"
mkdir -p ~/confdex/nginx

echo "--- Downloading compose files ---"
cd ~/confdex
curl -fsSL https://raw.githubusercontent.com/mkassaf/ConfDex/main/docker-compose.yml          -o docker-compose.yml
curl -fsSL https://raw.githubusercontent.com/mkassaf/ConfDex/main/docker-compose.selfsigned.yml -o docker-compose.selfsigned.yml
curl -fsSL https://raw.githubusercontent.com/mkassaf/ConfDex/main/nginx/selfsigned.conf        -o nginx/selfsigned.conf

echo "--- Writing .env ---"
cat > .env <<EOF
HOST_IP=$SERVER_IP
ADMIN_PASSWORD=$ADMIN_PASSWORD
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
DEEPSEEK_API_KEY=
GEMINI_API_KEY=
GROQ_API_KEY=
MISTRAL_API_KEY=
EOF

echo "--- Starting ConfDex ---"
docker compose -f docker-compose.yml -f docker-compose.selfsigned.yml up -d

echo ""
echo "Done! ConfDex is running at https://$SERVER_IP"
echo "Username: (leave blank)"
echo "Password: $ADMIN_PASSWORD"
REMOTE
