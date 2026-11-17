# Oracle Ubuntu ARM64 — Complete Setup & Recovery Guide

**A beginner-friendly, repeatable runbook based on the working `algoagentx-prod` setup (14–15 November 2026).**

> **Goal:** Run AlgoAgentX on Oracle Cloud Always Free, increase disk storage, access the original Ubuntu desktop from Windows/mobile through RustDesk, use Google Chrome and JobBots on the same machine, and edit files from Windows VS Code through SSH.
>
> **Read this first:** This is a record of what we configured and what was verified, plus clearly marked optional/future steps. **Never copy a password, private SSH key, or authentication token into this Markdown file.** Review free-tier limits, versions, and instance identifiers again when doing a fresh installation.

## Table of contents

1. [Final working architecture and status](#1-final-working-architecture-and-status)
2. [Important concepts: host, Docker Webtop, RustDesk and SSH](#2-important-concepts-host-docker-webtop-rustdesk-and-ssh)
3. [Connect to the Oracle VM from Windows](#3-connect-to-the-oracle-vm-from-windows)
4. [Check the Oracle Always Free quotas](#4-check-the-oracle-always-free-quotas)
5. [Resize the existing boot volume from 47 to 150 GB](#5-resize-the-existing-boot-volume-from-47-to-150-gb)
6. [Expand the Ubuntu partition and ext4 filesystem](#6-expand-the-ubuntu-partition-and-ext4-filesystem)
7. [Optional: Docker Webtop browser desktop](#7-optional-docker-webtop-browser-desktop)
8. [Install RustDesk and XFCE on the original Ubuntu host](#8-install-rustdesk-and-xfce-on-the-original-ubuntu-host)
9. [Fix the headless LightDM/Xorg display](#9-fix-the-headless-lightdmxorg-display)
10. [Use RustDesk from Windows or phone](#10-use-rustdesk-from-windows-or-phone)
11. [Install Google Chrome on Ubuntu ARM64](#11-install-google-chrome-on-ubuntu-arm64)
12. [Clone the JobBots Git repository](#12-clone-the-jobbots-git-repository)
13. [Windows VS Code Remote SSH setup](#13-windows-vs-code-remote-ssh-setup)
14. [Fix Windows SSH `Bad owner or permissions`](#14-fix-windows-ssh-bad-owner-or-permissions)
15. [Chrome debugger and JobBots deployment — pending](#15-chrome-debugger-and-jobbots-deployment--pending)
16. [Daily-use commands, checks and troubleshooting](#16-daily-use-commands-checks-and-troubleshooting)
17. [Security and recovery checklist](#17-security-and-recovery-checklist)
18. [Official reference links](#18-official-reference-links)

---

## 1. Final working architecture and status

```text
Windows laptop                          Android / other device
  ├─ PowerShell / SSH                    └─ RustDesk app
  ├─ VS Code + Remote-SSH                       │
  └─ RustDesk app ───────────────────────────────┤
                                                ▼
                                Oracle Cloud: algoagentx-prod
                                ARM64 Ubuntu host, Mumbai region
                                2 OCPUs / 12 GB RAM / 150 GB disk
                                                │
              ┌─────────────────────────────────┼───────────────────┐
              │                                 │                   │
       XFCE + LightDM + Xorg                Docker host         Chrome
       RustDesk remote desktop         ├─ AlgoAgentX (18)   browser GUI
                                       └─ Future JobBots      on Ubuntu
                                           + n8n

Optional separate Docker Webtop GUI (port 3001): tested, then stopped/removed.
```

### Results actually observed

| Item | Before | Verified after setup |
|---|---|---|
| Instance | `algoagentx-prod` | Same existing instance |
| CPU / memory | 2 OCPUs / 12 GB | Unchanged |
| Architecture | `aarch64` | ARM64 |
| Boot volume in OCI | 47 GB | **150 GB**, displayed as Always Free |
| Root filesystem `df -h /` | 45 GB, 18 GB free | **146 GB, 118 GB free (19% used)** |
| Docker | 18 AlgoAgentX containers | **18/18 healthy** at last check |
| Host RustDesk | Not installed | Installed, remote XFCE desktop accessed successfully |
| Headless GUI | No running Xorg | `lightdm active`, `Xorg :0`, `rustdesk active` |
| Webtop | Deployed temporarily | Stopped; removal was subsequently requested |
| Google Chrome | Not initially installed | Chrome GUI visible and working in RustDesk screenshot |
| JobBots Git repository | Not on Ubuntu | Clone succeeded |
| Windows SSH config | Permission error | Windows ACL problem identified; user later reported fixed |
| VS Code Remote SSH | Set up in progress | Configuration done; validate opening the project after fixing SSH |
| JobBots n8n + Chrome debugger | — | **Not yet confirmed deployed/configured** |

**Important:** CPU and memory are the main limits for running a browser alongside AlgoAgentX trading. Free disk space alone does not guarantee enough CPU headroom during live trading.

---

## 2. Important concepts: host, Docker Webtop, RustDesk and SSH

- **Original Ubuntu host** = the actual Oracle VM. It contains the Docker engine and AlgoAgentX. A terminal opened through the RustDesk host desktop operates here.
- **Docker Webtop** = a *different* Linux desktop inside a container. It has its own environment and consumes additional RAM/CPU. It is **optional** once RustDesk on the host works.
- **RustDesk** = remote GUI access by device ID and password. The installed RustDesk agent runs on the original Ubuntu host.
- **Windows SSH / VS Code Remote SSH** = access and edit the Ubuntu host from Windows, without installing full VS Code GUI on Ubuntu. Remote SSH still installs a small VS Code Server on Ubuntu and uses some host resources.
- **SSH tunnel** = forwards server-local ports such as 3000/8000, and optionally Webtop 3001, into Windows `localhost`. An SSH tunnel and RustDesk are separate connections.

**Final recommendation:** Keep **RustDesk + XFCE on the host**, skip Docker Webtop unless browser-based GUI is specifically needed, and run JobBots/n8n in their own containers.

---

## 3. Connect to the Oracle VM from Windows

### 3.1 Find the VM and IP — Oracle Console (click by click)

1. Sign in at <https://cloud.oracle.com/>.
2. Select the **India West (Mumbai)** region, or the actual region of your VM.
3. Go to **Compute → Instances**.
4. Click **`algoagentx-prod`**.
5. In **Instance access**, note **Public IP address**, **Username `ubuntu`**, and confirm the instance shows **Running**.
6. Keep the private key file stored **locally** on Windows; never upload it into Git.

### 3.2 Existing Windows SSH key and connection method

The uploaded BAT file used this folder and key name:

```text
D:\Stock_market\algoagentx\docs\oracle_cloud_keys\ssh-key-private.key
```

Actual SSH user in this setup: `ubuntu`. The public IP seen at setup time was `130.210.58.143` (**replace if your VM IP ever changes**).

Example Windows `.bat` file (`connect_oracle_ubuntu.bat`):

```bat
@echo off
title Connect Ubuntu - AlgoAgentX
cd /d "D:\Stock_market\algoagentx\docs\oracle_cloud_keys" || (pause & exit /b 1)
ssh -i ".\ssh-key-private.key" ubuntu@130.210.58.143
pause
```

Double-click the BAT file to open the Ubuntu SSH terminal. An SSH key passphrase may be requested if you configured one; it is **not** your RustDesk password.

### 3.3 Baseline host check (read-only)

```bash
uname -m
nproc
free -h
uptime
df -hT /
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS
docker ps --format 'table {{.Names}}\t{{.Status}}'
docker stats --no-stream
```

Expected for this VM: `aarch64`, `2` CPU cores, about 12 GB memory, Docker containers named `algoagentx_*`.

---

## 4. Check the Oracle Always Free quotas

**Do this before changing resources.** The Console's shape marketing banner is not proof of a larger free allowance.

### 4.1 CPU quota

1. Oracle Console → **Governance & Administration → Limits, quotas and usage**.
2. Click **Edit filters**; choose service **Compute** and the correct region/availability-domain scope.
3. In search, enter `standard-a1-core-count`.
4. Read **Service Limit**, **Usage** and **Available**.

Observed account result: **limit 2, usage 2, available 0**.

### 4.2 Memory quota

Search `standard-a1-memory-count` on the same page.

Observed account result: **limit 12, usage 12, available 0**.

### 4.3 Storage quota

1. On the same page change **Service** to **Block Volume**.
2. Check the **combined boot + block volumes** consumption in the home region.
3. Also review **Storage → Block Storage → Boot Volumes / Block Volumes** for other allocated volumes.
4. Verify the volume/resize displays **Always Free**, and check for any pricing warning.

At the time of this setup, Oracle documented **200 GB combined Always Free boot/block storage in the home region**. The example instance used **150 GB**, leaving theoretical room for other storage only if the tenancy is not already using it. Always recheck current quota and billing eligibility.

**Do not resize CPU to 4 OCPUs or memory to 24 GB based only on an older Console banner.**

---

## 5. Resize the existing boot volume from 47 to 150 GB

**Risk level: production storage operation.** Do this during a trading maintenance window. Save a boot volume backup **before** resizing; for AlgoAgentX PostgreSQL, take a database-consistent backup too. In the historical screenshots the backup warning was visible, so do **not** assume a backup existed in that run.

### 5.1 Find the correct volume

1. Oracle Console → **Compute → Instances → `algoagentx-prod`**.
2. Open the **Storage** tab.
3. Find the **Boot volume** row (it showed **47 GB**, **Attached**).
4. Click the **boot volume name** — `algoagentx-prod (Boot Volume)`.
5. You should now be on the **Boot volume information** page.

**Common confusion:** The section **Attached block volumes** can say *“There are no block volumes attached”*. That is OK. The system disk is a **boot volume**, not an extra block volume. **Do not use “Replace boot volume” or “Attach block volume.”**

### 5.2 Back up first

1. On the boot volume details page open **Backups**.
2. Choose **Create Boot Volume Backup**.
3. Use a clear name such as `algoagentx-before-storage-resize`.
4. Wait until its status indicates the backup is available/complete.
5. Separately make a PostgreSQL logical backup using your own database credentials and backup procedure; a volume backup alone may not provide transaction-consistent recovery of an active database.

### 5.3 Increase the size in Oracle Console

1. Boot volume details → **Edit** (top right), or **Actions → Edit**.
2. Change **Volume size (in GB)** from `47` to `150`.
3. Keep **Performance based auto-tune = Off**.
4. Keep the original **VPUs type = 10 VPUs/GB (Balanced)** (avoid extra performance tiers).
5. Review any pricing/free-tier warnings.
6. Click **Update / Save changes** only if backup and free quota are confirmed.
7. Wait for Oracle's volume resize/provisioning work to complete.
8. Oracle may show **Resize boot volume** with OS rescan commands. **Copy the commands for your specific instance**.

The historical setup did **not** stop/recreate the instance. Oracle supports online expansion; however, guest OS partition/filesystem growth is a separate step.

### 5.4 Rescan Ubuntu disk

Oracle displayed a command resembling the following on this instance. **Prefer the exact commands shown by your own Console** because device paths can differ:

```bash
sudo dd iflag=direct if=/dev/oracleoci/oraclevda of=/dev/null count=1
echo '1' | sudo tee /sys/class/block/$(readlink /dev/oracleoci/oraclevda | cut -d/ -f 2)/device/rescan
```

**Note:** This is a read-only `dd` probe using `of=/dev/null`, not a disk-wiping command. Do not alter the `of=/dev/null` part.

Inspect after rescan:

```bash
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS
df -hT /
findmnt -no SOURCE,FSTYPE /
```

Historical observation at this point:

```text
sda       150G
├─sda1    46.5G ext4  /
└─sda15     99M vfat  /boot/efi

df -h /: 45G total, 18G available
```

The larger virtual **disk** was present, but the **partition/filesystem** were still small. This is expected.

---

## 6. Expand the Ubuntu partition and ext4 filesystem

**Only for the verified partition layout above** (`/dev/sda1` mounted as `/`, ext4, and `sda15` EFI). On any different VM, inspect and adjust rather than blindly copying commands.

### 6.1 Check growpart and do a dry run

```bash
command -v growpart
sudo growpart -N /dev/sda 1
```

If missing:

```bash
sudo apt-get update
sudo apt-get install -y cloud-guest-utils
```

The dry run showed `CHANGE: partition=1`, and a new end sector. **Do not change `/dev/sda15` (EFI boot partition)**.

### 6.2 After backup and successful dry run, grow the partition

```bash
sudo growpart /dev/sda 1
```

Historical result began with `CHANGED: partition=1 ...`.

### 6.3 Expand ext4 online

```bash
sudo resize2fs /dev/sda1
```

Historical output confirmed the mounted `/` filesystem was resized online. **No instance reboot was required in that run**.

### 6.4 Verify final storage and Docker

```bash
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINTS
df -hT /
docker ps --format 'table {{.Names}}\t{{.Status}}'
```

Actual final result:

```text
sda       150G
├─sda1   149.9G ext4 /
└─sda15     99M vfat /boot/efi

/dev/sda1  ext4  146G  28G  118G  19% /
```

All 18 AlgoAgentX Docker containers showed `healthy` at final verification.

**Never:** run `mkfs`, `fdisk` delete/recreate, `dd` to a real disk output, or `docker system prune --volumes` as a shortcut for a storage resize.

---

## 7. Optional: Docker Webtop browser desktop

**Historical step:** This was installed and opened successfully at `https://localhost:3001`, but was later stopped because the **host XFCE + RustDesk** desktop met the user's actual needs. **Skip on a fresh setup unless you specifically want a browser-based desktop independent from the host.**

### 7.1 Install Webtop (optional)

On **Ubuntu SSH terminal**, not on Windows PowerShell:

```bash
mkdir -p ~/jobbots-webtop/config
cd ~/jobbots-webtop
cat > compose.yaml <<'EOF'
services:
  webtop:
    image: lscr.io/linuxserver/webtop:ubuntu-xfce
    container_name: jobbots-webtop
    environment:
      PUID: "1000"
      PGID: "1000"
      TZ: Asia/Kolkata
    volumes:
      - ./config:/config
    ports:
      - "127.0.0.1:3001:3001"
    shm_size: "1gb"
    mem_limit: 2g
    cpus: 0.75
    restart: "no"
EOF

docker compose pull
docker compose up -d
docker stats --no-stream jobbots-webtop
```

The separate Docker desktop used around **461 MiB RAM** immediately after startup in one measurement, and may use more later.

### 7.2 Windows SSH tunnel to Webtop

For an SSH tunnel in Windows PowerShell (replace IP and key path if they change):

```powershell
ssh -i "D:\Stock_market\algoagentx\docs\oracle_cloud_keys\ssh-key-private.key" -N -L 3001:127.0.0.1:3001 ubuntu@130.210.58.143
```

Keep that terminal open, then visit **<https://localhost:3001>**. A browser warning about a self-signed certificate can appear; proceed **only after confirming the URL is localhost and the tunnel is yours**.

If you also need AlgoAgentX frontend/API tunnels, the uploaded BAT used:

```bat
@echo off
title AlgoAgentX + JobBots Webtop - SSH Tunnel
cd /d "D:\Stock_market\algoagentx\docs\oracle_cloud_keys" || (pause & exit /b 1)
ssh -N -o ExitOnForwardFailure=yes -i ".\ssh-key-private.key" ^
  -L 3000:127.0.0.1:3000 ^
  -L 8000:127.0.0.1:8000 ^
  -L 3001:127.0.0.1:3001 ^
  ubuntu@130.210.58.143
pause
```

Don't run another tunnel using the same local ports simultaneously.

### 7.3 Stop or remove Webtop when not needed

```bash
docker stop jobbots-webtop
docker inspect --format '{{.State.Status}}' jobbots-webtop
```

Actual output after stopping was `exited`. `docker ps jobbots-webtop` is **invalid syntax**; use `docker ps -a --filter name=jobbots-webtop`.

If you decide to remove the Webtop container, image and Compose network:

```bash
cd ~/jobbots-webtop
docker compose down --rmi all
docker ps -a --filter name=jobbots-webtop
```

That command does **not** delete the `~/jobbots-webtop/config` directory. Confirm your Compose project before running it. **Stopping Webtop closes the application on port 3001; it does not inherently break SSH or RustDesk.**

---

## 8. Install RustDesk and XFCE on the original Ubuntu host

**Run everything in this section in the Oracle Ubuntu host SSH terminal**, not a terminal inside Docker Webtop.

### 8.1 RustDesk ARM64 package

The working release at the time was **RustDesk 1.5.3** for Linux AArch64. For later reinstalls, check the official release page for the current `.deb` name, version, and checksum.

```bash
cd /tmp
wget -O rustdesk-arm64.deb \
  https://github.com/rustdesk/rustdesk/releases/download/1.5.3/rustdesk-1.5.3-aarch64.deb
```

Checksum used and confirmed `OK` in this installation:

```bash
echo 'fa85e8d3ccd45e2e303c2d1359af5dc51aa93d880e39ba47c9b04bfabd82ae19  rustdesk-arm64.deb' | sha256sum -c -
```

**Never reuse this old checksum with a different package version.** Verify the expected digest from a trusted release source for that version.

Install and verify:

```bash
sudo apt-get install -y ./rustdesk-arm64.deb
rustdesk --version
systemctl status rustdesk --no-pager
```

Actual version: `1.5.3`; service: `active (running)`.

**If `rustdesk: command not found`:** Downloading the `.deb` is not the same as installing it. Run the `sudo apt-get install -y ./rustdesk-arm64.deb` step and check output.

### 8.2 Handle the “Daemons using outdated libraries” prompt

During apt installation Ubuntu showed a purple **Which services should be restarted?** dialog. To avoid restarting Docker/SSH/nginx unexpectedly on a live trading server, the historical flow chose **Cancel** on the optional restart prompt. This does not by itself mean package installation failed.

For subsequent installs, complete system-wide package/service updates during maintenance time rather than blindly restarting all selected services.

### 8.3 Install lightweight desktop dependencies

Host RustDesk initially logged `cannot open display :0`, because no host GUI was running. We therefore installed lightweight XFCE, LightDM and dummy Xorg:

```bash
sudo apt-get update
sudo env NEEDRESTART_MODE=l DEBIAN_FRONTEND=noninteractive \
  apt-get install -y --no-install-recommends \
  xfce4 xfce4-terminal xorg lightdm lightdm-gtk-greeter \
  xserver-xorg-video-dummy dbus-x11
```

These are **host packages** and not part of Docker Webtop. If another GUI/display manager already exists, assess first; do not overwrite custom setup.

### 8.4 Enable RustDesk headless mode and get its ID

```bash
sudo rustdesk --option allow-linux-headless Y
sudo rustdesk --get-id
```

The command returned an ID in the real setup. **Don't put the actual ID in a public document**. An ID does not guarantee screen sharing until Xorg is working.

---

## 9. Fix the headless LightDM/Xorg display

**What we actually fixed:** LightDM initially failed because a misconfigured line passed an unsupported `-layout` argument to Xorg. The log showed **`(EE) Unrecognized option: Layout`**. The fix was to **remove** the `xserver-layout=Dummy Layout` line; then Xorg started.

### 9.1 Create a dummy display at 1280×720

Back up an existing file if present:

```bash
sudo mkdir -p /etc/X11/xorg.conf.d
if [ -f /etc/X11/xorg.conf.d/20-dummy.conf ]; then
  sudo cp /etc/X11/xorg.conf.d/20-dummy.conf /etc/X11/xorg.conf.d/20-dummy.conf.bak
fi
```

Create the config:

```bash
sudo tee /etc/X11/xorg.conf.d/20-dummy.conf >/dev/null <<'EOF'
Section "Device"
    Identifier "Dummy Device"
    Driver "dummy"
    VideoRam 256000
EndSection

Section "Monitor"
    Identifier "Dummy Monitor"
    HorizSync 28.0-80.0
    VertRefresh 48.0-75.0
    Modeline "1280x720" 74.25 1280 1390 1430 1650 720 725 730 750 +HSync +VSync
EndSection

Section "Screen"
    Identifier "Dummy Screen"
    Device "Dummy Device"
    Monitor "Dummy Monitor"
    DefaultDepth 24
    SubSection "Display"
        Depth 24
        Modes "1280x720"
    EndSubSection
EndSection

Section "ServerLayout"
    Identifier "Dummy Layout"
    Screen "Dummy Screen"
EndSection
EOF
```

### 9.2 Configure LightDM — **correct final config**

```bash
sudo mkdir -p /etc/lightdm/lightdm.conf.d
sudo tee /etc/lightdm/lightdm.conf.d/50-xfce.conf >/dev/null <<'EOF'
[Seat:*]
user-session=xfce
greeter-session=lightdm-gtk-greeter
EOF
```

**Do not add `xserver-layout=Dummy Layout`.** That line was the cause of the observed failure.

### 9.3 Start graphical service and verify

```bash
sudo systemctl reset-failed lightdm
sudo systemctl start lightdm
systemctl is-active lightdm
pgrep -a Xorg || true
systemctl is-active rustdesk
```

Actual successful output:

```text
active
... /usr/lib/xorg/Xorg -core :0 ...
active
```

If it fails, inspect the actual reason:

```bash
sudo journalctl -u lightdm -n 40 --no-pager
sudo tail -n 60 /var/log/lightdm/x-0.log
```

Also check for an existing conflicting `/etc/X11/xorg.conf` or incompatible custom config. Do not reboot the production server casually.

### 9.4 Reboot persistence — check later in a maintenance window

```bash
systemctl is-enabled lightdm
systemctl is-enabled rustdesk
systemctl get-default
```

The service was successfully running during our session, but **we did not verify a reboot cycle**. Before relying on unattended access after a reboot, schedule a maintenance window, keep SSH/Oracle recovery access, and check startup behavior. If needed, enable appropriate services only after verifying the working config:

```bash
sudo systemctl enable lightdm rustdesk
```

Do not change boot targets or reboot just to test during live trading.

---

## 10. Use RustDesk from Windows or phone

### 10.1 Set the RustDesk remote-access password

RustDesk password and Ubuntu login password are **two different passwords**.

Safer interactive method (password not printed by `echo`):

```bash
read -rsp 'Choose a strong RustDesk remote-access password: ' RD_PASS
echo
sudo rustdesk --password "$RD_PASS"
unset RD_PASS
```

An alternative is to generate a random password and store it **in a password manager**. Never store or share it in source code, Git, screenshots, or this guide. In our historical session a password appeared in a screenshot; **rotate any screenshot-exposed password**.

If `sudo` asks for a password, it is authenticating the **Ubuntu account** (`sudo`), not asking you to invent the RustDesk password. The following confirms whether passwordless sudo is currently available:

```bash
sudo -n whoami
```

`root` means that check worked; a password-required message means you must authenticate as your Ubuntu user (don't disable security just to skip the prompt).

### 10.2 Install RustDesk on Windows

1. Open <https://github.com/rustdesk/rustdesk/releases>.
2. Download the **Windows x86-64** application, not the Linux ARM64 `.deb`.
3. Install/open RustDesk on Windows.
4. On Ubuntu, get the ID: `sudo rustdesk --get-id`.
5. In Windows RustDesk, enter the Ubuntu host's ID and choose **Connect**.
6. If the public server blocks connections with **“login required”**, use the app's **Account/Login** flow and sign in with the supported provider (in the observed session, Google/GitHub login solved it).
7. Enter your private **RustDesk remote-access password** when prompted.

**Production/security note:** RustDesk's public relay/server warned it was for testing/demo and not recommended for sensitive production work. AlgoAgentX involves trading, so consider a trusted private/self-hosted RustDesk server or another secure remote-access arrangement before relying on this long term.

### 10.3 Ubuntu graphical login password

After RustDesk connected, the LightDM login screen asked for the **Ubuntu user login password**, which was different from the RustDesk password. A user whose Ubuntu access was created with an SSH key may not have a usable interactive Linux password yet.

Set a strong Ubuntu user password from the already-working **SSH terminal**:

```bash
sudo passwd ubuntu
```

Enter and confirm a password **privately**. Then on the remote LightDM login screen choose **Ubuntu** and use the new **Ubuntu login password**. The screenshots subsequently showed the XFCE desktop and an Ubuntu terminal running Docker commands.

### 10.4 Connect from Android

1. Install RustDesk from an official/distributed trusted source.
2. Enter the same Ubuntu RustDesk ID.
3. Complete required account login if requested by the server.
4. Enter your saved RustDesk remote password.
5. If LightDM shows the Ubuntu login page, use the separate Ubuntu user password.

**This mobile flow was requested but not separately shown as tested in the screenshots.**

---

## 11. Install Google Chrome on Ubuntu ARM64

The screenshots showed **Google Chrome running on the original Ubuntu XFCE desktop via RustDesk**. Official Chrome releases now support Linux ARM64; confirm current package availability for future installs.

On the **Ubuntu host**:

```bash
uname -m
# Expected: aarch64

cd /tmp
wget -O google-chrome-arm64.deb \
  https://dl.google.com/linux/direct/google-chrome-stable_current_arm64.deb

sudo apt-get install -y ./google-chrome-arm64.deb
google-chrome --version
```

Open **Applications → Internet → Google Chrome** or launch it from the host terminal.

**Do not run Chrome as root and do not expose its remote debugging endpoint publicly.**

---

## 12. Clone the JobBots Git repository

On original Ubuntu terminal:

```bash
mkdir -p ~/ird-projects
cd ~/ird-projects
git clone https://github.com/mdirsad123/auto-email-recruiter-reply.git
cd auto-email-recruiter-reply
pwd
ls -la
```

Actual screenshot confirmed a successful clone of `auto-email-recruiter-reply`.

Expected working path:

```text
/home/ubuntu/ird-projects/auto-email-recruiter-reply
```

Useful subsequent commands:

```bash
cd ~/ird-projects/auto-email-recruiter-reply
git status
git pull --ff-only
```

**Do not** put `.env`, OAuth tokens, browser profiles, session cookies, recruiter credentials, or other secrets into Git. Review the project's `.gitignore` before pushing. JobBots/n8n production deployment was **not completed** in this conversation.

---

## 13. Windows VS Code Remote SSH setup

**Recommended:** Run the graphical VS Code app on **Windows**, and connect by Remote SSH to the Ubuntu host. You do not need to install full VS Code GUI inside Ubuntu. The Remote SSH extension does place a VS Code Server on Ubuntu, which consumes some resources.

### 13.1 Install the extension (Windows)

1. Open Windows **VS Code**.
2. Press **Ctrl+Shift+X** (Extensions).
3. Search **Remote - SSH** (Microsoft).
4. Click **Install**.
5. Press **Ctrl+Shift+P**, type `Remote-SSH: Open SSH Configuration File`.
6. Select:

```text
C:\Users\mdsah\.ssh\config
```

### 13.2 Add SSH host entry

Put these lines into the Windows config file (adjust the IP/key path if they change):

```sshconfig
Host oracle-algoagentx
    HostName 130.210.58.143
    User ubuntu
    IdentityFile D:/Stock_market/algoagentx/docs/oracle_cloud_keys/ssh-key-private.key
    IdentitiesOnly yes
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

Press **Ctrl+S**. This entry is for Windows OpenSSH; the key file must actually exist at that path.

### 13.3 Test SSH from **Windows PowerShell first**

```powershell
ssh -o ConnectTimeout=10 oracle-algoagentx "echo SSH_OK && uname -m"
```

Expected:

```text
SSH_OK
aarch64
```

Only continue to VS Code after this succeeds. It helps separate SSH-file problems from VS Code Server problems.

### 13.4 Open remote project in VS Code

1. In Windows VS Code press **Ctrl+Shift+P**.
2. Select **Remote-SSH: Connect to Host...**.
3. Choose `oracle-algoagentx`.
4. If asked **Select the platform of the remote host**, choose **Linux**.
5. On first connection, VS Code may install its remote VS Code Server on the Ubuntu machine.
6. When connected, select **File → Open Folder**.
7. Enter:

```text
/home/ubuntu/ird-projects/auto-email-recruiter-reply
```

8. Click **OK/Open**, and approve trust only if you recognize the repository.

**Note:** In one screenshot VS Code showed `Could not establish connection` because Windows SSH itself was rejecting the config file's permissions. After the permissions fix the user reported the situation was fine, but a screenshot of the final opened remote folder was not supplied. Verify it as needed.

---

## 14. Fix Windows SSH `Bad owner or permissions`

Actual error encountered:

```text
Bad permissions. Try removing permissions for user: UNKNOWN\\UNKNOWN (...SID...) on file C:/Users/mdsah/.ssh/config
Bad owner or permissions on C:\Users\mdsah\.ssh\config
```

This is **Windows local file ACL**, not an Ubuntu permission problem. **Do not change permissions on Ubuntu to fix it.**

### 14.1 Inspect config permissions — Windows PowerShell

```powershell
$cfg = "$env:USERPROFILE\.ssh\config"
icacls $cfg
```

### 14.2 Fix inheritance and give your own user control

In a Windows PowerShell shell **running as the actual account that owns the config**:

```powershell
$cfg = "$env:USERPROFILE\.ssh\config"
icacls $cfg /inheritance:r
icacls $cfg /grant:r "$($env:USERNAME):(F)"
```

If the original error specifically reports an **unknown SID** that still appears on the file, replace the placeholder with the exact SID shown by *your* error:

```powershell
# Example syntax; use your own SID from the error, not the literal placeholder.
icacls $cfg /remove "*S-1-5-21-REPLACE-WITH-SID-FROM-ERROR"
```

Recheck `icacls $cfg`. On some Windows installations owner/permissions may need repair through **File Properties → Security → Advanced** as the file owner or an administrator. Avoid broad rights for `Everyone`/`Users`.

### 14.3 Retest Windows SSH

```powershell
ssh -o ConnectTimeout=10 oracle-algoagentx "echo SSH_OK && uname -m"
```

Only after this works, retry **Remote-SSH: Connect to Host** in VS Code.

If you get `Identity file not accessible`, check the **IdentityFile path**. If you get `Permission denied (publickey)`, confirm the right private key and Ubuntu user. If network times out, check instance status, IP, and OCI network/security rules.

---

## 15. Chrome debugger and JobBots deployment — pending

These were the **next planned tasks**, **not confirmed completed** in the screenshots/conversation. Don't assume JobBots automation is deployed just because the repo is cloned.

### 15.1 Intended design

```text
Host Chrome on Ubuntu XFCE
  └─ separate JobBots browser profile
      └─ Chrome DevTools Protocol debugger on localhost (port 9222)

JobBots Python / n8n Docker services
  └─ access the debugger via a carefully configured private path
     (do not publicly expose port 9222)
```

### 15.2 Safe initial debugger test — interactive host session only

Close any Chrome instance using the dedicated profile first, then in the **Ubuntu XFCE user terminal**:

```bash
mkdir -p "$HOME/.config/jobbots-chrome-debug"
google-chrome \
  --remote-debugging-address=127.0.0.1 \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.config/jobbots-chrome-debug" \
  --no-first-run
```

This launches a separate profile so it does not interfere with normal Chrome sign-in/session data. In another Ubuntu terminal, verify locally:

```bash
curl -fsS http://127.0.0.1:9222/json/version
```

**Important:** This is a *reference test*, not a previously verified completed step. It may require changes for the user's exact Chrome/version/display/session. Debugger access from Docker needs additional deliberate networking, potentially a secure proxy; Docker containers do not normally share the host's `127.0.0.1`. **Never publish CDP/9222 directly on the public internet**, because it can give control of the browser and its logged-in sessions.

### 15.3 Recommended next checks before deploying JobBots/n8n

```bash
cd ~/ird-projects/auto-email-recruiter-reply
find . -maxdepth 2 -type f | sort | head -80
docker compose version
docker ps --format 'table {{.Names}}\t{{.Status}}'
free -h
uptime
```

Then inspect the actual repository's Compose, `.env.example`, Python requirements, and browser connection settings. Deploy **with its real files**; don't invent environment variables or docker services. Limit CPU/RAM usage while AlgoAgentX live trading is active.

---

## 16. Daily-use commands, checks and troubleshooting

### 16.1 Quick health check

```bash
printf '\n=== HOST ===\n'
uname -m; nproc; uptime; free -h; df -h /
printf '\n=== REMOTE DESKTOP ===\n'
systemctl is-active rustdesk lightdm
pgrep -a Xorg || true
printf '\n=== DOCKER ===\n'
docker ps --format 'table {{.Names}}\t{{.Status}}'
```

### 16.2 AlgoAgentX Docker usage

```bash
docker stats --no-stream
docker system df
```

`docker system df` may show reclaimable build cache. **Do not use destructive Docker prune commands casually** on a trading server.

### 16.3 Check RustDesk device ID and running state

```bash
sudo rustdesk --get-id
systemctl status rustdesk --no-pager
```

### 16.4 LightDM status or errors

```bash
systemctl is-active lightdm
sudo journalctl -u lightdm -n 40 --no-pager
sudo tail -n 60 /var/log/lightdm/x-0.log
```

If logs say `Unrecognized option: Layout`, check `/etc/lightdm/lightdm.conf.d/50-xfce.conf` and remove the invalid `xserver-layout=...` entry (keep the actual dummy Xorg config in `/etc/X11/xorg.conf.d/20-dummy.conf`).

### 16.5 Webtop status (only if still installed)

```bash
docker ps -a --filter name=jobbots-webtop
docker inspect --format '{{.State.Status}}' jobbots-webtop
```

An `exited` container is stopped; port 3001 will not respond. SSH tunnels for other ports may still work.

### 16.6 Windows SSH quick test

```powershell
ssh oracle-algoagentx "echo SSH_OK && hostname && uname -m"
```

### 16.7 Difference between the various passwords

| Prompt | Password required |
|---|---|
| Windows SSH | SSH private key (plus key passphrase if configured) |
| `sudo` on Ubuntu | Ubuntu user's sudo authentication |
| RustDesk remote connection | RustDesk remote-access password |
| XFCE/LightDM login screen | Ubuntu `ubuntu` user's login password |
| RustDesk public-server login | Supported Google/GitHub account (when required) |

**Do not reuse the same password for all of them.**

---

## 17. Security and recovery checklist

- [ ] Check **Always Free eligibility, current quota and expected charges** before increasing any volume or shape.
- [ ] Create a **boot volume backup** and **database-consistent PostgreSQL backup** before risky storage operations.
- [ ] Keep original **Windows private SSH key** safe; never commit it to Git.
- [ ] Keep SSH and Oracle Console recovery access available while configuring Xorg/LightDM.
- [ ] Use strong **separate RustDesk and Ubuntu login passwords**.
- [ ] **Rotate any password shown in a screenshot**. A previous RustDesk password was visible in this conversation's screenshots.
- [ ] Use an access method appropriate for a **trading production server**; public RustDesk infrastructure displayed a demo/testing warning.
- [ ] Never expose port **9222** (Chrome debugger) to the public internet.
- [ ] Bind temporary Webtop to `127.0.0.1` and use SSH tunneling rather than opening it publicly.
- [ ] Restrict JobBots/Chrome CPU and memory and monitor live trading behavior on the **2-OCPU** host.
- [ ] Verify Docker containers are healthy after maintenance.
- [ ] If you need desktop access after reboot, explicitly verify LightDM/RustDesk startup **during a maintenance window**; no reboot persistence test was shown in the conversation.
- [ ] Keep `.env`, tokens, credentials, logs with secrets and browser profiles out of Git.

### On a new VM, safest order of operations

1. Provision a supported Always Free **ARM64 Ubuntu** VM (confirm quota, SSH key, region).
2. Confirm SSH login from Windows and make recovery/backup plan.
3. Install Docker/AlgoAgentX as separately documented (not reproduced here; they existed already).
4. Expand boot volume only if needed, with backup, rescan and filesystem expansion.
5. Install RustDesk, XFCE, dummy Xorg and LightDM, then test from Windows.
6. Install host Chrome, clone JobBots and verify the code.
7. Connect with VS Code Remote SSH from Windows; fix Windows `.ssh\config` ACL if needed.
8. Test Chrome debugger **privately**, then integrate actual n8n/JobBots Docker services.
9. Test resource usage again **when trading is live**, not only during the weekend.

---

## 18. Official reference links

- [Oracle Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
- [Oracle: Online resizing of block/boot volumes](https://docs.oracle.com/en-us/iaas/Content/Block/Tasks/update-online-resize-block-boot-volume.htm)
- [Oracle: Rescan an expanded volume](https://docs.oracle.com/en-us/iaas/Content/Block/Tasks/rescanningdisk.htm)
- [LinuxServer Webtop documentation](https://docs.linuxserver.io/images/docker-webtop/)
- [RustDesk official releases](https://github.com/rustdesk/rustdesk/releases)
- [RustDesk headless Linux notes](https://github.com/rustdesk/rustdesk/wiki/Headless-Linux-Support)
- [RustDesk public server login requirement](https://github.com/rustdesk/rustdesk/wiki/Login-required-for-public-server)
- [Google Chrome install instructions](https://support.google.com/chrome/answer/95346)
- [Arm: Google Chrome on Arm Linux](https://learn.arm.com/install-guides/browsers/chrome/)
- [VS Code Remote SSH](https://code.visualstudio.com/docs/remote/ssh)
- [VS Code Linux/ARM remote requirements](https://code.visualstudio.com/docs/remote/linux)

---

**End of guide.** Recorded installation succeeded through RustDesk GUI, Google Chrome, Git clone and Windows SSH permission repair. The **Chrome debugger + JobBots/n8n production deployment still needs its own verified runbook** after the actual project files are inspected.
