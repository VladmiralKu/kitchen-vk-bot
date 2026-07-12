# Timeweb deploy

This deploy runs the VK kitchen bot on a Timeweb VPS:

- app container: FastAPI + Uvicorn on `127.0.0.1:8000`
- db container: PostgreSQL 16
- host Nginx: HTTPS reverse proxy
- Certbot: Let's Encrypt certificate

## 1. Prepare repository

Apply the Timeweb deploy files locally, then push:

```bash
git status
git add .env.timeweb.example Dockerfile docker-compose.yml nginx/kitchen-vk-bot.conf.example scripts/deploy_timeweb.sh scripts/backup_postgres.sh scripts/restore_postgres.sh docs/timeweb_deploy.md
git commit -m "Add Timeweb Docker deployment"
git push
```

## 2. Create VPS

Create a Timeweb VPS/VDS with Ubuntu 24.04.
Recommended minimum for MVP:

- 1 CPU
- 1 GB RAM
- 15 GB disk

Copy the server IPv4 address.

## 3. Point domain

Create an `A` record for a domain or subdomain:

```text
bot.example.com -> VPS IPv4
```

Wait until DNS resolves:

```bash
dig +short bot.example.com
```

## 4. Connect by SSH

```bash
ssh root@YOUR_SERVER_IP
```

## 5. Install packages

```bash
apt update && apt upgrade -y
apt install -y git nginx certbot python3-certbot-nginx ufw curl ca-certificates
```

Install Docker:

```bash
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo ${UBUNTU_CODENAME:-$VERSION_CODENAME}) stable" > /etc/apt/sources.list.d/docker.list
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Optional firewall:

```bash
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable
```

## 6. Clone project

```bash
git clone https://github.com/VladmiralKu/kitchen-vk-bot.git /opt/kitchen-vk-bot
cd /opt/kitchen-vk-bot
```

## 7. Create `.env`

```bash
cp .env.timeweb.example .env
nano .env
```

Fill real values:

```text
POSTGRES_PASSWORD=long_random_password
DATABASE_URL=postgresql+asyncpg://kitchen_bot:long_random_password@db:5432/kitchen_bot
VK_TOKEN=token_from_vk
VK_GROUP_ID=239829146
VK_SECRET=same_secret_as_vk_callback
VK_CONFIRMATION_CODE=code_from_vk_callback_screen
SUPERADMIN_VK_ID=your_numeric_vk_id
APP_TIMEZONE=Europe/Kirov
PUBLIC_BASE_URL=https://bot.example.com
```

Use the exact variable names above. Do not use `VK_GROUP_TOKEN` or `VK_SECRET_KEY` for this project.

## 8. Start app

```bash
docker compose up -d --build
docker compose exec app alembic upgrade head
docker compose ps
curl http://127.0.0.1:8000/health
```

Expected health result:

```text
{"status":"ok"}
```

## 9. Configure Nginx

```bash
cp nginx/kitchen-vk-bot.conf.example /etc/nginx/sites-available/kitchen-vk-bot
nano /etc/nginx/sites-available/kitchen-vk-bot
```

Replace `YOUR_DOMAIN` with your real domain.

```bash
ln -s /etc/nginx/sites-available/kitchen-vk-bot /etc/nginx/sites-enabled/kitchen-vk-bot
nginx -t
systemctl reload nginx
```

## 10. Enable HTTPS

