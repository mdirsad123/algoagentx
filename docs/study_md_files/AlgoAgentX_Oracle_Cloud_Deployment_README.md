# AlgoAgentX on Oracle Cloud — Beginner Deployment Guide

> Complete beginner-friendly deployment guide for AlgoAgentX on Oracle Cloud Infrastructure (OCI) using an Always Free Ampere A1 VM, Ubuntu, Docker Compose, GitHub, SSH, Nginx, and a public IP.
>
> This guide also documents the real issues encountered and the fixes: signup failure, missing public IP, Windows SSH permission problems, Ubuntu upgrade, Docker ARM64 installation, Git-based deployment, missing Git-tracked Next.js files, fresh PostgreSQL schema problems, SSH tunneling, OCI firewall rules, Linux iptables ordering, Nginx reverse proxying, and public frontend/API configuration.

---

## Table of Contents

1. Final architecture
2. Oracle Cloud signup
3. Create the VM
4. Public IPv4 setup
5. Connect public subnet to the internet
6. SSH from Windows
7. Verify server resources
8. Upgrade Ubuntu
9. Install Docker + Compose
10. GitHub deployment workflow
11. Copy secret environment files
12. Deploy AlgoAgentX
13. Git / Docker build troubleshooting
14. Fresh DB / Alembic issue
15. SSH tunnel
16. Make the app public with Nginx
17. OCI HTTP/HTTPS firewall rules
18. Critical Linux iptables fix
19. Nginx reverse proxy for Web + API
20. Next.js public API URL
21. Verify phone/laptop access
22. Production hardening
23. Daily deployment workflow
24. Troubleshooting commands
25. Safety rules
26. Official references

---

# 1. Final architecture

```text
Phone / Tablet / Laptop / Any Internet Device
                    |
                    v
          Oracle Public IPv4
                    |
              TCP 80 / 443
                    |
                    v
                 Nginx
             /           \
            /             \
           v               v
  Next.js Web :3000   FastAPI :8000
           \               /
            \             /
             v           v
          PostgreSQL   Redis
          localhost    localhost

Workers:
- alert_worker
- live_market_worker
- live_strategy_worker
- live_reconcile_worker
```

The laptop does **not** need to remain ON. Once deployed, the Oracle VM runs independently.

---

# 2. Oracle Cloud signup

Official Oracle Cloud Free Tier landing page:

```text
https://www.oracle.com/cloud/free/
```

Oracle Console:

```text
https://cloud.oracle.com/
```

Click **Start for free / Sign up**.

Use your real details.

Recommended for an individual user:

```text
Customer Type: Individual
Country: India
Email: your real personal email
```

If you select **Corporate**, Oracle can ask for a legal company name.

Choose the home region carefully. In this deployment:

```text
Home Region: India West (Mumbai)
```

Oracle normally asks for a valid debit/credit card for identity verification. A small temporary authorization hold may appear.

Important:

- use your own valid card
- avoid unsupported virtual/prepaid/single-use cards
- do not create multiple accounts to bypass verification
- your card is not normally charged for Always Free usage unless you upgrade/use paid resources

If signup shows:

```text
Oops, we're sorry, an error occurred while creating your account
```

check:

- name/address/card details
- customer type
- region
- whether a VPN/proxy is enabled
- whether you previously attempted multiple accounts

Use Oracle signup support/chat if the error continues.

After signup you may see:

```text
Please wait while we finish setting up your account...
```

Wait until account provisioning finishes.

---

# 3. Create the Oracle Compute Instance

Go to:

```text
Navigation Menu
→ Compute
→ Instances
→ Create instance
```

## 3.1 Basic information

Example:

```text
Name: algoagentx-prod
Compartment: algoagentx (root)
Availability Domain: AD-1
Capacity Type: On-demand
```

## 3.2 Image

Recommended:

```text
Ubuntu 22.04 LTS
```

If you already created Ubuntu 20.04, this guide includes the 20.04 → 22.04 upgrade steps later.

For Ampere A1 use an ARM64-compatible image.

## 3.3 Shape

Click:

```text
Change shape
```

Then:

```text
Instance Type: Virtual Machine
Shape Series: Ampere
Shape: VM.Standard.A1.Flex
```

Configuration used here:

```text
OCPU: 2
Memory: 12 GB
```

Final target:

```text
VM.Standard.A1.Flex
2 OCPU
12 GB RAM
ARM64 / aarch64
```

Always Free usage is subject to Oracle limits, capacity, and Free Tier policies.

## 3.4 Security

The documented deployment used the normal defaults:

```text
Shielded Instance: disabled
Confidential Computing: disabled
```

Keep your own security requirements in mind.

## 3.5 Networking

Choose:

```text
Create new virtual cloud network
```

Example:

```text
VCN Name: algoagentx-vcn
```

Then choose:

```text
Create new public subnet
```

Example:

```text
Subnet Name: algoagentx-public-subnet
CIDR Block: 10.0.0.0/24
```

Private IPv4:

```text
Automatically assign private IPv4 address
```

Public IPv4:

```text
Automatically assign public IPv4 address
```

If the public IPv4 toggle is unavailable, continue and assign it after creation.

IPv6 is not required for this setup.

## 3.6 SSH keys

Choose:

```text
Generate a key pair for me
```

Download both keys, especially the **private key**.

Example:

```text
ssh-key-private.key
```

Never upload the private key to GitHub.

## 3.7 Storage

The deployment used the default boot volume:

```text
Boot Volume: ~45–47 GB
Use in-transit encryption: enabled
Custom encryption key: disabled
Additional block volumes: none
```

## 3.8 Review and create

Verify:

```text
Name: algoagentx-prod
Image: Ubuntu
Shape: VM.Standard.A1.Flex
OCPU: 2
RAM: 12 GB
Public subnet configured
SSH key downloaded
Default boot volume
```

Click **Create** and wait for:

```text
State: Running
```

---

# 4. Assign / verify the Public IPv4 address

Open:

```text
Compute
→ Instances
→ algoagentx-prod
→ Networking
```

You should see a private and public IPv4.

Example:

```text
Private IPv4: 10.0.0.57
Public IPv4: 130.210.58.143
```

If the public IP is empty (`-`):

```text
Networking
→ Attached VNICs
→ click Primary VNIC
→ IP administration
→ primary private IP
→ ⋮ / Edit
→ Public IP Type
→ Ephemeral Public IP
→ Update
```

For a permanent production domain, consider a Reserved Public IP later.

---

# 5. Connect the public subnet to the internet

A public IP alone is not enough.

Go to:

```text
Compute
→ Instances
→ algoagentx-prod
→ Networking / Quick Actions
→ Connect public subnet to internet
```

Example prefix:

```text
algoagentx
```

Click **Create**.

This quick action can configure:

- Internet Gateway
- Route Table rule
- Network Security Group
- required associations

Verify the route table:

```text
Destination: 0.0.0.0/0
Target Type: Internet Gateway
Target: Internet Gateway algoagentx-vcn
```

---

# 6. Connect from Windows to Ubuntu with SSH

Suppose the private key is:

```text
C:\Users\<WINDOWS_USER>\Downloads\ssh-key-private.key
```

Open Windows Command Prompt:

```cmd
cd C:\Users\<WINDOWS_USER>\Downloads
```

Connect:

```cmd
ssh -i ".\ssh-key-private.key" ubuntu@<PUBLIC_IP>
```

Example:

```cmd
ssh -i ".\ssh-key-private.key" ubuntu@130.210.58.143
```

First connection:

```text
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

Type:

```text
yes
```

Successful prompt:

```text
ubuntu@algoagentx-prod:~$
```

## Windows SSH config permission error

A real issue encountered:

```text
Bad owner or permissions on C:\Users\<USER>\.ssh\config
```

Temporary workaround used:

```cmd
ren C:\Users\<WINDOWS_USER>\.ssh\config config.bak
```

Then retry SSH.

If the error points to the private key itself, fix that file's Windows ACL rather than deleting the key.

---

# 7. Verify CPU, RAM, disk, and architecture

Run:

```bash
uname -m
nproc
free -h
df -h /
```

Expected approximately:

```text
Architecture: aarch64
CPU: 2
RAM: ~11 GiB usable
Disk: ~45 GB
```

---

# 8. Update / upgrade Ubuntu

Normal updates:

```bash
sudo apt update
sudo apt upgrade -y
```

Reboot:

```bash
sudo reboot
```

Reconnect after 30–60 seconds.

## If already on Ubuntu 22.04

Check:

```bash
lsb_release -a
```

If it shows Jammy/22.04, skip the release-upgrade section.

## Upgrade Oracle Ubuntu 20.04 → 22.04

First update/reboot:

```bash
sudo apt update
sudo apt upgrade -y
sudo reboot
```

Reconnect.

Stop Oracle cloud agent during the release upgrade:

```bash
sudo snap stop oracle-cloud-agent
```

Then:

```bash
sudo systemctl stop unified-monitoring-agent
```

If that service is not installed, an error saying the unit is not loaded can be ignored.

Start upgrade:

```bash
sudo do-release-upgrade
```

### Prompt: Continue running under SSH?

Type:

```text
y
```

Ubuntu may start temporary SSH recovery on port `1022`.

When asked to press Enter, press Enter.

### Prompt: Start upgrade?

Type:

```text
y
```

### Prompt: Restart services automatically?

On the purple package configuration screen choose:

```text
Yes
```

After completion verify:

```bash
lsb_release -a
```

Expected:

```text
Description: Ubuntu 22.04.x LTS
Codename: jammy
```

Then reboot:

```bash
sudo reboot
```

Reconnect and verify:

```bash
uname -r
```

Example from this deployment:

```text
6.8.0-1061-oracle
```

---

# 9. Install Docker Engine + Docker Compose

Docker officially supports Ubuntu 22.04 on ARM64.

Run:

```bash
sudo apt update
sudo apt install -y ca-certificates curl
```

Create keyring directory:

```bash
sudo install -m 0755 -d /etc/apt/keyrings
```

Download Docker GPG key:

```bash
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg   -o /etc/apt/keyrings/docker.asc
```

Permissions:

```bash
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

Create repository configuration:

```bash
sudo tee /etc/apt/sources.list.d/docker.sources > /dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
```

Update:

```bash
sudo apt update
```

Check:

```bash
apt-cache policy docker-ce
```

Install:

```bash
sudo apt install -y   docker-ce   docker-ce-cli   containerd.io   docker-buildx-plugin   docker-compose-plugin
```

Verify:

```bash
sudo systemctl status docker --no-pager
sudo docker --version
sudo docker compose version
```

Use Docker without sudo:

```bash
sudo usermod -aG docker $USER
newgrp docker
```

Test:

```bash
docker ps
docker run --rm hello-world
```

Expected:

```text
Hello from Docker!
```

---

# 10. Recommended GitHub deployment workflow

Use Git rather than repeatedly uploading ZIP files.

Recommended structure:

```text
/home/ubuntu/
└── stock_market/
    └── algoagentx/
        ├── .git/
        ├── AlgoAgentXAPI/
        ├── AlgoAgentXApp/
        ├── docker/
        ├── docs/
        ├── docker-compose.yml
        └── ...
```

Create parent folder:

```bash
mkdir -p ~/stock_market
cd ~/stock_market
```

Git identity:

```bash
git config --global user.name "YOUR NAME"
git config --global user.email "YOUR_GITHUB_EMAIL"
```

Create Oracle → GitHub SSH key:

```bash
ssh-keygen -t ed25519 -C "algoagentx-oracle"
```

Press Enter for default path. Show public key:

```bash
cat ~/.ssh/id_ed25519.pub
```

On GitHub:

```text
Profile
→ Settings
→ SSH and GPG keys
→ New SSH key
```

Example title:

```text
AlgoAgentX Oracle Production
```

Test:

```bash
ssh -T git@github.com
```

Clone:

```bash
cd ~/stock_market
git clone git@github.com:YOUR_USERNAME/YOUR_REPO.git algoagentx
```

Then:

```bash
cd ~/stock_market/algoagentx
git status
git pull
```

---

# 11. Copy secret environment files

Do not commit secret environment files to GitHub.

Example local project:

```text
D:\Stock_market\algoagentx
```

Oracle:

```text
/home/ubuntu/stock_market/algoagentx
```

From Windows CMD/PowerShell:

```cmd
scp -i "C:\Users\<WINDOWS_USER>\Downloads\ssh-key-private.key" "D:\Stock_market\algoagentx\.env.dev" ubuntu@<PUBLIC_IP>:/home/ubuntu/stock_market/algoagentx/.env.dev
```

```cmd
scp -i "C:\Users\<WINDOWS_USER>\Downloads\ssh-key-private.key" "D:\Stock_market\algoagentx\.env.prod" ubuntu@<PUBLIC_IP>:/home/ubuntu/stock_market/algoagentx/.env.prod
```

```cmd
scp -i "C:\Users\<WINDOWS_USER>\Downloads\ssh-key-private.key" "D:\Stock_market\algoagentx\AlgoAgentXAPI\.env" ubuntu@<PUBLIC_IP>:/home/ubuntu/stock_market/algoagentx/AlgoAgentXAPI/.env
```

```cmd
scp -i "C:\Users\<WINDOWS_USER>\Downloads\ssh-key-private.key" "D:\Stock_market\algoagentx\AlgoAgentXApp\.env.local" ubuntu@<PUBLIC_IP>:/home/ubuntu/stock_market/algoagentx/AlgoAgentXApp/.env.local
```

Secure:

```bash
cd ~/stock_market/algoagentx
chmod 600 .env.dev .env.prod
chmod 600 AlgoAgentXAPI/.env
chmod 600 AlgoAgentXApp/.env.local
```

Check Git ignores them:

```bash
git check-ignore .env.dev .env.prod AlgoAgentXAPI/.env AlgoAgentXApp/.env.local
```

---

# 12. Deploy AlgoAgentX with Docker Compose

Go to project:

```bash
cd ~/stock_market/algoagentx
```

Build/start:

```bash
docker compose --env-file .env.prod -f docker-compose.yml up -d --build
```

Check:

```bash
docker ps
```

Detailed status:

```bash
docker ps --format "table {{.Names}}	{{.Status}}	{{.Ports}}"
```

Typical services:

```text
algoagentx_web
algoagentx_api
algoagentx_postgres_prod
algoagentx_redis
algoagentx_alert_worker
algoagentx_live_market_worker
algoagentx_live_strategy_worker
algoagentx_live_reconcile_worker
```

Keep PostgreSQL and Redis private:

```text
127.0.0.1:5432
127.0.0.1:6379
```

Local tests:

```bash
curl -I http://127.0.0.1:3000
curl -I http://127.0.0.1:8000/docs
curl http://127.0.0.1:8000/openapi.json
```

---

# 13. Git / Docker build troubleshooting

## Missing `@/lib/...` Next.js modules

Example:

```text
Module not found: Can't resolve '@/lib/route'
Module not found: Can't resolve '@/lib/timezone'
Module not found: Can't resolve '@/lib/api/admin'
```

The cause in this deployment was an over-broad `.gitignore`.

Do **not** globally ignore:

```gitignore
lib/
lib64/
package-lock.json
```

Your real app source under:

```text
AlgoAgentXApp/lib/
```

must be committed.

Keep generated folders ignored:

```gitignore
node_modules/
.next/
.venv/
.env
.env.prod
.env.dev
.env.local
__pycache__/
*.log
```

Check ignored files locally:

```cmd
git status --ignored --short AlgoAgentXApp\lib
```

Check tracked files:

```cmd
git ls-files AlgoAgentXApp/lib
git ls-files AlgoAgentXApp/package-lock.json
```

Also check Docker ignore rules:

```bash
cat AlgoAgentXApp/.dockerignore
```

Do not ignore real source directories such as:

```text
lib
app
components
hooks
contexts
types
public
```

Remember Linux is case-sensitive:

```text
lib/timezone.ts
```

is not the same as:

```text
lib/Timezone.ts
```

---

# 14. Fresh PostgreSQL / Alembic issue

A PostgreSQL container can be healthy while tables are missing.

Example:

```text
asyncpg.exceptions.UndefinedTableError:
relation "strategy_deployments" does not exist
```

Meaning:

```text
PostgreSQL running          ✅
API can reach PostgreSQL    ✅
Database schema/tables      ❌
```

Inspect:

```bash
docker logs algoagentx_api --tail 200
docker logs algoagentx_postgres_prod --tail 100
docker logs algoagentx_alert_worker --tail 100
```

Locate Alembic:

```bash
docker exec -it algoagentx_api sh -lc 'pwd && find /app -maxdepth 2 \( -name "alembic.ini" -o -name "alembic" \) -print'
```

If your container has `/app/alembic.ini`, typical commands are:

```bash
docker exec -it algoagentx_api sh -lc 'cd /app && alembic current'
docker exec -it algoagentx_api sh -lc 'cd /app && alembic upgrade head'
```

If you need existing users/strategies/backtests, restore your previous PostgreSQL backup instead of relying only on migrations.

---

# 15. Temporary SSH tunnel access

Before public exposure, tunnel through SSH:

```cmd
ssh -i ".\ssh-key-private.key" -L 3000:127.0.0.1:3000 -L 8000:127.0.0.1:8000 ubuntu@<PUBLIC_IP>
```

Then open:

```text
http://127.0.0.1:3000
http://127.0.0.1:8000/docs
```

The SSH window must remain open for tunnel access.

The Oracle VM/Docker containers continue running even if your laptop shuts down; only the tunnel disappears.

---

# 16. Make AlgoAgentX public with Nginx

Install:

```bash
sudo apt update
sudo apt install -y nginx
```

Check:

```bash
sudo systemctl status nginx --no-pager
```

Expected:

```text
Active: active (running)
```

Local test:

```bash
curl -I http://127.0.0.1
```

---

# 17. OCI HTTP / HTTPS firewall rules

Go to:

```text
OCI Console
→ Networking
→ Virtual Cloud Networks
→ algoagentx-vcn
→ Network Security Group
→ algoagentxNSG
→ Security Rules
→ Add Rules
```

HTTP:

```text
Direction: Ingress
Source Type: CIDR
Source: 0.0.0.0/0
Protocol: TCP
Source Port: All
Destination Port: 80
Description: AlgoAgentX HTTP
```

HTTPS:

```text
Direction: Ingress
Source Type: CIDR
Source: 0.0.0.0/0
Protocol: TCP
Source Port: All
Destination Port: 443
Description: AlgoAgentX HTTPS
```

Do not expose:

```text
5432 PostgreSQL
6379 Redis
```

Once Nginx is in front, do not publicly expose 3000/8000 unless you have a specific reason.

---

# 18. Critical Linux iptables fix

This was the key public-access issue.

Symptom:

```bash
curl -I http://127.0.0.1
```

worked, but Windows:

```cmd
curl -I http://<PUBLIC_IP>
```

timed out.

Check Nginx:

```bash
sudo ss -ltnp | grep ':80 '
```

Expected:

```text
0.0.0.0:80
[::]:80
```

Inspect firewall order:

```bash
sudo iptables -L INPUT -n -v --line-numbers
```

The real server had a REJECT rule **before** the initial 80/443 ACCEPT rules.

Bad order example:

```text
1 ACCEPT RELATED,ESTABLISHED
...
4 ACCEPT tcp dpt:22
5 REJECT all
6 ACCEPT tcp dpt:80
7 ACCEPT tcp dpt:443
```

Rules after REJECT never get a chance.

Correct fix:

```bash
sudo iptables -I INPUT 1 -p tcp --dport 80 -m conntrack --ctstate NEW -j ACCEPT
sudo iptables -I INPUT 2 -p tcp --dport 443 -m conntrack --ctstate NEW -j ACCEPT
```

Persist:

```bash
sudo netfilter-persistent save
```

If needed:

```bash
sudo apt install -y iptables-persistent
sudo netfilter-persistent save
```

Verify:

```bash
sudo iptables -L INPUT -n -v --line-numbers | head -15
```

Port 80/443 ACCEPT must appear **before** REJECT.

## tcpdump proof

Install:

```bash
sudo apt install -y tcpdump
```

Capture:

```bash
sudo tcpdump -ni enp0s6 tcp port 80
```

From Windows:

```cmd
curl -I http://<PUBLIC_IP>
```

If you see SYN packets such as:

```text
CLIENT_IP.xxxxx > 10.0.0.57.80: Flags [S]
```

OCI is delivering traffic to the VM.

After the iptables order fix, Windows should return:

```text
HTTP/1.1 200 OK
Server: nginx
```

---

# 19. Nginx reverse proxy for Web + API

Create:

```bash
sudo nano /etc/nginx/sites-available/algoagentx
```

Use:

```nginx
server {
    listen 80;
    listen [::]:80;

    server_name _;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host $host;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8000/openapi.json;
        proxy_set_header Host $host;
    }
}
```

Save:

```text
Ctrl + O
Enter
Ctrl + X
```

Disable default site:

```bash
sudo rm -f /etc/nginx/sites-enabled/default
```

Enable AlgoAgentX:

```bash
sudo ln -s /etc/nginx/sites-available/algoagentx /etc/nginx/sites-enabled/algoagentx
```

Test:

```bash
sudo nginx -t
```

Expected:

```text
syntax is ok
test is successful
```

Reload:

```bash
sudo systemctl reload nginx
```

Now:

```text
http://<PUBLIC_IP>
```

should open AlgoAgentX.

---

# 20. Next.js production API URL

If the Next.js production build contains:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

phone access will fail because `localhost` on the phone means the phone.

Find the setting:

```bash
cd ~/stock_market/algoagentx
```

```bash
grep -Rni   --exclude-dir=node_modules   --exclude-dir=.next   --exclude-dir=.git   "NEXT_PUBLIC_API_URL" .
```

In this deployment the correct production file was:

```text
/home/ubuntu/stock_market/algoagentx/.env.prod
```

Edit:

```bash
nano .env.prod
```

Change:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

to:

```env
NEXT_PUBLIC_API_URL=http://<PUBLIC_IP>
```

Example:

```env
NEXT_PUBLIC_API_URL=http://130.210.58.143
```

Verify:

```bash
grep NEXT_PUBLIC_API_URL .env.prod
```

Rebuild web because `NEXT_PUBLIC_*` values are compiled into the Next.js production build:

```bash
docker compose --env-file .env.prod -f docker-compose.yml up -d --build web
```

Later, after domain + HTTPS:

```env
NEXT_PUBLIC_API_URL=https://yourdomain.com
```

Then rebuild web again.

---

# 21. Verify phone / laptop access

From any external device:

```text
http://<PUBLIC_IP>
```

Windows test:

```cmd
curl -I http://<PUBLIC_IP>
```

Expected:

```text
HTTP/1.1 200 OK
```

API:

```text
http://<PUBLIC_IP>/openapi.json
```

If `/docs` is blank but `/openapi.json` returns JSON, the API is reachable and Swagger may be blocked by your Content-Security-Policy.

---

# 22. Recommended production hardening

## Bind Next.js/API to localhost

Prefer:

```yaml
ports:
  - "127.0.0.1:3000:3000"
```

and:

```yaml
ports:
  - "127.0.0.1:8000:8000"
```

so Nginx is the only public entry point.

## Keep DB/Redis private

Good:

```text
127.0.0.1:5432
127.0.0.1:6379
```

## Restart policies

Consider:

```yaml
restart: unless-stopped
```

for long-running services.

## Reserved Public IP

Use a Reserved Public IP for a long-lived production domain.

## Domain

Create a DNS `A` record pointing to the Oracle public IP.

## HTTPS

Add Let's Encrypt / Certbot once the domain resolves. Do not treat plain HTTP as production-ready for login/trading.

## Database backups

Back up PostgreSQL before major migrations/deployments.

Never casually run:

```bash
docker compose down -v
```

`-v` can remove named volumes, including your database.

## Worker health

If a worker is unhealthy:

```bash
docker logs <container_name> --tail 200
```

Example:

```bash
docker logs algoagentx_alert_worker --tail 200
```

---

# 23. Daily Git deployment workflow

Local laptop:

```bash
git add .
git commit -m "your change"
git push origin main
```

Oracle:

```bash
cd ~/stock_market/algoagentx
git pull origin main
```

Deploy:

```bash
docker compose --env-file .env.prod -f docker-compose.yml up -d --build
```

Verify:

```bash
docker ps
```

Long-term improvement: create a `deploy.sh` that runs pull → migrations → build → health checks.

---

# 24. Useful troubleshooting commands

Docker:

```bash
docker ps
docker ps --format "table {{.Names}}	{{.Status}}	{{.Ports}}"
```

API logs:

```bash
docker logs algoagentx_api --tail 200
```

Web logs:

```bash
docker logs algoagentx_web --tail 200
```

Postgres logs:

```bash
docker logs algoagentx_postgres_prod --tail 100
```

Worker logs:

```bash
docker logs algoagentx_alert_worker --tail 200
```

Nginx:

```bash
sudo systemctl status nginx --no-pager
sudo nginx -t
sudo systemctl reload nginx
```

Ports:

```bash
sudo ss -ltnp
```

Firewall:

```bash
sudo iptables -L INPUT -n -v --line-numbers
```

Persist firewall:

```bash
sudo netfilter-persistent save
```

Local tests:

```bash
curl -I http://127.0.0.1
curl -I http://127.0.0.1:3000
curl -I http://127.0.0.1:8000/docs
curl http://127.0.0.1:8000/openapi.json
```

Packet capture:

```bash
sudo tcpdump -ni enp0s6 tcp port 80
```

Resources:

```bash
free -h
df -h /
nproc
uname -m
uname -r
```

Git:

```bash
git status
git remote -v
git pull origin main
```

---

# 25. Important safety rules

1. Never commit `.env.prod`, passwords, API keys, broker credentials, Twilio credentials, Telegram tokens, cTrader secrets, DB passwords, or cloud credentials.
2. Never commit the Oracle SSH private key.
3. Do not expose PostgreSQL `5432` publicly.
4. Do not expose Redis `6379` publicly.
5. Prefer Nginx on 80/443 as the only public entry point.
6. Bind 3000/8000 to `127.0.0.1` once Nginx is working.
7. Do not use `docker compose down -v` unless you intentionally want to remove volumes.
8. Back up PostgreSQL before migrations/major deployment changes.
9. Add HTTPS before production use.
10. Verify all live-trading/background workers, not only the web page.
11. Keep Ubuntu and Docker updated.
12. Test trading changes on demo/simulation before real-money automation.

---

# 26. Official references

Oracle Free Tier:

```text
https://docs.oracle.com/en/learn/cloud_free_tier/
```

Always Free resources:

```text
https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
```

Create an OCI compute instance:

```text
https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/launchinginstance.htm
```

Public IP management:

```text
https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/managingpublicIPs.htm
```

Connect public subnet to Internet:

```text
https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/quick-action-internet-gateway.htm
```

OCI SSH troubleshooting:

```text
https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/troubleshooting-ssh-connection.htm
```

Canonical Oracle Ubuntu 20.04 → 22.04 upgrade:

```text
https://documentation.ubuntu.com/oracle/oracle-how-to/upgrade-from-focal-to-jammy/
```

Docker Engine for Ubuntu:

```text
https://docs.docker.com/engine/install/ubuntu/
```

Docker Compose plugin:

```text
https://docs.docker.com/compose/install/linux/
```

---

# Final quick checklist

```text
[ ] Oracle account created
[ ] Home region selected
[ ] Ampere A1 VM created
[ ] Ubuntu 22.04 running
[ ] 2 OCPU / 12 GB RAM verified
[ ] Public IPv4 assigned
[ ] Public subnet connected to Internet Gateway
[ ] SSH from Windows working
[ ] Docker installed
[ ] Docker Compose working
[ ] GitHub SSH configured
[ ] AlgoAgentX cloned
[ ] Secret env files copied separately
[ ] Docker services built
[ ] PostgreSQL private
[ ] Redis private
[ ] Nginx installed
[ ] OCI NSG port 80 opened
[ ] OCI NSG port 443 opened
[ ] iptables 80 rule before REJECT
[ ] iptables 443 rule before REJECT
[ ] Nginx reverse proxy to Next.js
[ ] Nginx reverse proxy to FastAPI
[ ] NEXT_PUBLIC_API_URL set to public server/domain
[ ] Phone can open AlgoAgentX
[ ] Login/API works from phone
[ ] Reserved IP considered
[ ] Domain configured
[ ] HTTPS configured
[ ] DB backup configured
[ ] Docker restart policies configured
[ ] All workers healthy
```

---

## Result

```text
Laptop OFF
    |
    |  does not matter
    v
Oracle Cloud VM continues running
    |
    +--> Docker
          |
          +--> Next.js
          +--> FastAPI
          +--> PostgreSQL
          +--> Redis
          +--> Live workers
          |
          v
        Nginx
          |
          v
Public Internet
          |
    +-----+-----+
    |     |     |
  Phone Tablet Laptop
```

After this setup, AlgoAgentX can be accessed independently from any device without keeping the development laptop powered on.
