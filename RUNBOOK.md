# RUNBOOK - hardened Cloudflare + reverse-proxy edge with a private mTLS backend

Exact ordered commands to publish a **static site** (apex) and a **static SPA + API
demo** (subdomain) behind Cloudflare + a small hardened reverse-proxy VPS (**edge**),
with the application backend (**hub**) kept private behind a 1:1 mutual-TLS leg.

Fill in your own values (all placeholders below), then run in order. The hub-side
play is PREP / DO-NOT-APPLY by default: apply it only when you are ready to go live.

```
client -> Cloudflare (PROXIED orange-cloud; edge TLS; Security Level High +
          Bot Fight Mode; /api rate-limit; Full-strict + AOP to origin)
       -> edge nginx :443 (CF Origin cert; ufw admits ONLY Cloudflare ranges)
            * example.com + www  -> static SITE (no /api, no hub)
            * chat.example.com   -> static SPA + /api -> hub (mTLS)
       -> [SPA /api only] hub nginx (mutual TLS; requires the edge client cert)
       -> hub app 127.0.0.1:<app_port>   (hub ufw admits ONLY the edge IP)
```

The backend (hub) IP is a **HARD secret** (vault only). It must never reach a
client, a third party, a public DNS record, or a log. The edge's IP being public
in DNS is fine (it is a disposable proxy). The edge<->hub leg uses an **existing
1:1 mutual-TLS pair**, referenced by path, not regenerated.

---

## H. Harden the box FIRST

Run this BEFORE the Cloudflare/proxy phases, as soon as the edge box exists and you
have its **IP**. It takes a small box (e.g. 1 vCPU / 1 GB RAM) to **key-only** SSH
with NOPASSWD-sudo automation, fail2ban, automatic security updates, sysctl
hardening, a swap file, and **egress filtering** (ufw default-deny outgoing + a
tight allowlist). The inbound firewall (ufw 22 + 443-from-CF) is applied by
`edge_base` inside `harden.yml`.

**KEY-FIRST:** pre-add the automation public key
(`~/.ssh/id_ed25519_edge.pub`) to the box, so bootstrap connects over the KEY with
no password. The provider's initial password is only a **fallback** for the case
the key was not pre-added.

**Values to fill in `group_vars/all/vault.local.yml`** (gitignored):

| Variable | Meaning |
| --- | --- |
| `vault_edge_public_ip` | the edge box's public IP - **required** |
| `vault_hub_backend_ip` | backend IP (HARD secret) - needed for the **hub egress** allow-rule + the later proxy phase |
| `vault_edge_host_initial_password` | provider's initial SSH password - **fallback only**, if the key was not pre-added (also used once for sudo escalation to set NOPASSWD) |
| *(optional)* `vault_hardening_fail2ban_ignoreips` | IPs fail2ban must never ban (e.g. an admin IP) |

```
cd /path/to/this-repo
export ANSIBLE_VAULT_PASSWORD_FILE="$PWD/.vault_pass"

# 0. Prereqs: collections (+ sshpass ONLY if you need the password fallback).
ansible-galaxy collection install -r requirements.yml

# 1. Fill the values into the gitignored vault.local.yml:
cp -n group_vars/all/vault.local.example.yml group_vars/all/vault.local.yml
$EDITOR group_vars/all/vault.local.yml     # vault_edge_public_ip (+ vault_hub_backend_ip)

# 2. BOOTSTRAP over the pre-added KEY: sets hostname, grants NOPASSWD sudo, and
#    VERIFIES key login. Password auth is NOT disabled here (anti-lockout split).
ansible-playbook playbooks/bootstrap.yml
#    FALLBACK (only if the key was NOT pre-added) - install it over the password:
#      command -v sshpass >/dev/null || sudo apt-get install -y sshpass
#      ansible-playbook playbooks/bootstrap.yml -e bootstrap_use_password=true

# 3. HARDEN over the verified key: ufw + sshd key-only + fail2ban + unattended
#    security upgrades + sysctl + swap + egress lockdown (LAST). Dry-run first:
ansible-playbook playbooks/harden.yml --check --diff
ansible-playbook playbooks/harden.yml

# 4. VERIFY the box is locked down:
ansible edge -m ping                                               # key login works
ssh -i ~/.ssh/id_ed25519_edge deploy@<IP> 'hostnamectl --static; \
  sudo systemctl is-active fail2ban; sudo fail2ban-client status sshd; \
  sudo ufw status verbose; sudo systemctl is-active unattended-upgrades; \
  swapon --show; free -h'
# ufw status should show: default deny (incoming), deny (outgoing); 22 ALLOW IN;
# 443 ALLOW IN from CF ranges; and ALLOW OUT for 53/123/80/443 + the backend IP:port.
# Password auth MUST be refused (expect "Permission denied (publickey)"):
ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no \
    deploy@<IP> 'true' ; echo "exit=$? (non-zero/denied = GOOD)"
# Root login MUST be refused:
ssh -o PreferredAuthentications=publickey root@<IP> 'true' ; echo "exit=$? (denied = GOOD)"
```

**Apply order is the safety guarantee:** bootstrap installs + *verifies* the key
while password auth is still on; harden only disables password auth, and it
connects *over the key* - so a broken key fails to connect and never reaches the
"disable passwords" step. The `hardening` role additionally asserts a non-empty
`authorized_keys` for `deploy` before writing the key-only sshd config.

**Egress allowlist (default-deny outgoing).** The box may reach ONLY: DNS (53),
NTP (123), HTTP/HTTPS (80/443, for apt + unattended-upgrades + the CF IP-range
fetch), and the hub mTLS upstream (`vault_hub_backend_ip` : `hub_mtls_port`).
Everything else outbound is dropped. The egress lockdown runs LAST in the role,
after every package install, so apt never breaks mid-run. If `vault_hub_backend_ip`
is not set at hardening time the hub rule is skipped (with a warning) - set it and
re-run before the proxy phase, or the proxy cannot reach the hub.

*How to add an egress exception:* add an entry to `hardening_egress_extra_rules`
in `group_vars/all/vars.yml` (or `-e`), e.g.
`hardening_egress_extra_rules: [{ port: 587, proto: tcp, to_ip: "203.0.113.5" }]`,
then re-run `ansible-playbook playbooks/harden.yml --tags egress`. (To open a port
to anywhere, omit `to_ip`.)

**fail2ban is intentionally LENIENT.** SSH is key-only, so brute-force is toothless;
fail2ban only stops egregious persistent abuse (sshd jail: `normal` mode, maxretry
10, 1h non-escalating ban). nginx/HTTP jails are OFF (Cloudflare fronts HTTP and
absorbs bursts). Loopback, the backend IP (`vault_hub_backend_ip`), and any
management IPs (`vault_hardening_fail2ban_mgmt_ips`, e.g. `10.0.0.0/24`) are never
banned, so automation and admins can't be locked out. The CF `/api` rate-limit is a
last-resort flood backstop only.

### Lockout recovery
If you ever cannot log in after hardening:
1. **You still have a window:** the running sshd is only reloaded after `sshd -t`
   passes; an existing SSH session stays alive across the reload. Keep one session
   open during step 3 and test a second login before closing it.
2. **Re-enable password auth** (from a working session, or the provider console):
   `sudo rm /etc/ssh/sshd_config.d/60-hardening.conf && sudo systemctl reload ssh`
   then re-run bootstrap to (re)install the key and re-verify before re-hardening.
3. **Provider console / recovery mode:** most VPS panels give VNC/serial console
   access that bypasses SSH entirely - log in as `deploy` (password still valid for
   console + sudo), fix `authorized_keys` or the sshd drop-in.
4. **fail2ban locked you out** (too many failed tries): wait out the bantime or,
   via console, `sudo fail2ban-client set sshd unbanip <your-ip>`. Add your admin
   IP to `vault_hardening_fail2ban_ignoreips` to prevent recurrence.

---

## 0. One-time prerequisites (control machine)

```
cd /path/to/this-repo
ansible-galaxy collection install -r requirements.yml

# Cloudflare: zone example.com active; create an Origin certificate covering
#   BOTH  example.com  AND  *.example.com ; note the Account ID.
# Builds: static-site build at portfolio_dist; SPA demo build at flutter_dist.
# mTLS: the existing 1:1 edge<->hub pair present on the edge + hub (see step 1).
```

---

## 1. Fill the secrets (ansible-vault + gitignored vault.local)

```
# (a) Vault password (gitignored; ansible.cfg points vault_password_file at it):
echo 'your-strong-vault-password' > .vault_pass && chmod 600 .vault_pass

# (b) Rotatable secrets in the ENCRYPTED vault.yml (create it from the example):
cp group_vars/all/vault.example.yml group_vars/all/vault.yml
ansible-vault encrypt group_vars/all/vault.yml
ansible-vault edit group_vars/all/vault.yml
#   vault_cloudflare_api_token, vault_cloudflare_account_id,
#   vault_cloudflare_origin_cert, vault_cloudflare_origin_key, vault_edge_ssh_key_path

# (c) The never-commit values in the gitignored vault.local.yml:
cp group_vars/all/vault.local.example.yml group_vars/all/vault.local.yml
$EDITOR group_vars/all/vault.local.yml
#   vault_hub_backend_ip (HARD secret), vault_edge_public_ip, flutter_dist,
#   and (optional) the mTLS *_content vars incl. the mTLS PRIVATE KEY.
```

Values to fill:

| Variable | Where | Source |
| --- | --- | --- |
| `vault_hub_backend_ip` | vault.local.yml (**never commit**) | you |
| `vault_edge_public_ip` | vault.local.yml | you, after the edge is up |
| `flutter_dist` | vault.local.yml | you |
| `vault_cloudflare_api_token` | encrypted vault.yml | CF dashboard / env file |
| `vault_cloudflare_account_id` | encrypted vault.yml | CF dashboard |
| `vault_cloudflare_origin_cert` / `_key` | encrypted vault.yml | CF dashboard (apex + wildcard) |
| `vault_edge_ssh_key_path` | encrypted vault.yml | you |
| `portfolio_dist`, `demo_subdomain` | vars.yml (non-secret) | defaults; override if needed |

mTLS material (the existing 1:1 pair): by default the roles **reference** files at
`mtls_dir` (`/etc/edge-mtls/`) on each host and do NOT regenerate. Only set the
`*_content` vars in vault.local.yml if you want Ansible to install the PEM (the
private key stays out of git either way).

---

## 2. (Optional) override the Cloudflare token from an env file

The token normally lives in the encrypted vault. To override it at run time from an
untracked env file (never echoed, never committed):

```
set -a; . /path/to/cloudflare.env; set +a
export CF_API_TOKEN="${CLOUDFLARE_API_TOKEN:-$CF_API_TOKEN}"
test -n "$CF_API_TOKEN" && echo "token loaded (len ${#CF_API_TOKEN})"   # length only
# then append:  -e "cloudflare_api_token=$CF_API_TOKEN"   to the commands below
```

Token scopes: Zone:Read, Zone.DNS:Edit, Zone.SSL and Certificates:Edit, Zone
Settings:Edit, Zone WAF:Edit, Zone Rate Limit:Edit.

---

## 3. Cloudflare edge (run after vault_edge_public_ip is filled; local-only)

```
ansible-playbook playbooks/cloudflare.yml --check    # dry run (add -e token override if used)
ansible-playbook playbooks/cloudflare.yml            # apply
```

Creates: proxied A records `example.com` + `www` + `chat.example.com` -> the edge;
Full-strict SSL + zone AOP; Security Level High + Bot Fight Mode; the SPA `/api/*`
rate-limit rule.

---

## 4. Edge reverse proxy (only after it is provisioned and its IP is filled)

```
ansible edge -m ping
ansible-playbook playbooks/edge.yml --check --diff      # dry run
ansible-playbook playbooks/edge.yml                     # apply: ufw + two-vhost nginx
```

Re-publish a single static build later:
```
ansible-playbook playbooks/edge.yml --tags portfolio    # apex only
ansible-playbook playbooks/edge.yml --tags demo         # SPA only
```

---

## 5. Hub side (PREP / DO-NOT-APPLY until you go live)

Run LAST, only after steps 3-4 succeeded and you are ready. Installs the hub mTLS
nginx (requires the edge's client cert) and the edge-only ufw rule.

```
ansible-playbook playbooks/hub.yml --check --diff          # dry run (NO change)
ansible-playbook playbooks/hub.yml                         # apply (only when ready)
```

### Hub mgmt ingress + admin lockdown (internal-only) - PREP/DO-NOT-APPLY

The admin lock/unlock endpoint (`/api/admin/*`) is **internal-only**: reachable ONLY
from localhost + the management subnet (`hub_mgmt_cidr`, default `10.0.0.0/24`),
never via Cloudflare. It is blocked at **THREE layers** (defense-in-depth):

1. **edge public proxy** (`demo.conf.j2`): `location /api/admin/` returns 404 - the
   public edge never forwards admin to the hub.
2. **hub mTLS nginx** (`hub-mtls.conf.j2`): a regex `location ~ ^/(api/)?admin/`
   returns 404. Important because public traffic reaches the app as `127.0.0.1`
   *through* this nginx; without this strip a public user could pass an app-side
   localhost allow. (The edge proxy strips the `/api/` prefix, so the regex covers
   both `/api/admin/*` and `/admin/*`.)
3. **hub firewall**: the app port is NOT publicly exposed - allowed from localhost
   (loopback) + `hub_mgmt_cidr` only; everything else is denied.

All three are GATED/templated and applied by `hub_allowlist` (firewall) +
`hub_mtls_proxy` (nginx). The firewall rules are default-OFF:

```
# Opens the web/admin port + app port to the mgmt subnet only, and denies the app
# port to everyone else:
ansible-playbook playbooks/hub.yml --check --diff -e hub_admin_ingress_enabled=true
ansible-playbook playbooks/hub.yml -e hub_admin_ingress_enabled=true
```

Set `hub_admin_mgmt_port` to the real hub web/admin port if it differs from
`hub_app_port` (the app port, locked to localhost + mgmt). **Responses** from the
hub admin port back to the mgmt subnet must escape any existing hub **deny-out to
`10.0.0.0/24`**. ufw's `before.rules` accepts `ESTABLISHED,RELATED` in
`ufw-before-output` ABOVE all user rules, so stateful responses are already
permitted; the play verifies this and warns if missing. If the hub uses a CUSTOM
raw deny-out that precedes conntrack, layer the established allow ABOVE it, e.g.:

```
# Insert an established/related response-allow above the deny-out (run on the hub):
sudo iptables -I OUTPUT 1 -d 10.0.0.0/24 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
# (persist via the hub's iptables-persistent / its own runbook)
```

Verify after apply:
```
# From a mgmt-subnet (10.0.0.x) box, the admin port answers:
curl -fsS http://<hub-internal-ip>:<admin_port>/api/admin/health
# From the PUBLIC edge it must 404 (never reaches the hub) - BOTH nginx layers:
curl -fsSI https://chat.example.com/api/admin/health | head -n1   # 404
# The app port is NOT reachable from a non-mgmt host (expect timeout/refused):
curl -sS --max-time 8 http://<hub-other-ip>:<app_port>/ ; echo "  (expect blocked)"
# But the hub's own loopback + a mgmt box still reach it:
ssh hub 'curl -fsS http://127.0.0.1:<app_port>/health'            # 200 on the hub
```

---

## 6. VERIFY the backend IP is exposed nowhere

```
# (a) Each public name resolves to CLOUDFLARE IPs ONLY - never the edge, never the hub:
for h in example.com www.example.com chat.example.com; do
  echo "== $h =="; dig +short "$h"
done
#   -> expect Cloudflare addresses (104.* / 172.6x.* / 188.114.* ...), NOT the
#      edge public IP and NEVER the backend IP.

# (b) Cross-check against Cloudflare's published ranges:
dig +short chat.example.com | while read ip; do
  grep -q "$(echo "$ip" | cut -d. -f1-2)" <(curl -s https://www.cloudflare.com/ips-v4) \
    && echo "$ip = Cloudflare OK" || echo "$ip = NOT Cloudflare - STOP"
done

# (c) Site + demo are publicly reachable (no login gate):
curl -fsSI https://example.com/        | head -n1     # 200
curl -fsSI https://chat.example.com/   | head -n1     # 200

# (d) The SPA API works through the full chain (CF -> edge -> mTLS -> hub):
curl -fsS https://chat.example.com/api/health

# (e) The backend IP appears in NO tracked file (it lives ONLY in the gitignored
#     vault.local.yml). Prove it is absent from everything git tracks:
HUBIP=$(sed -n 's/^vault_hub_backend_ip:[[:space:]]*"\{0,1\}\([0-9.]*\).*/\1/p' group_vars/all/vault.local.yml)
git grep -nF "$HUBIP" -- . || echo "clean: backend IP not in tracked files"

# (f) The edge is NOT reachable on 443 except via Cloudflare (direct hit fails):
curl -sS --max-time 8 -k https://<edge_public_ip>/ ; echo "  (expect timeout/refused/403)"

# (g) The hub mTLS port rejects anyone without the edge's client cert:
curl -sS --max-time 8 -k https://<hub_ip_or_host>:<mtls_port>/ ; echo "  (expect 400/403 - no client cert)"

# (h) The secret files are gitignored:
git check-ignore -v group_vars/all/vault.local.yml .vault_pass
```

If any of (a), (b), (e) shows the backend IP or a non-Cloudflare address, STOP and
fix before handing the link to anyone.

---

## 7. Rollback

```
ansible-playbook playbooks/teardown.yml      # removes OUR vhosts/cert/ufw on the edge + hub
# The existing 1:1 mTLS pair is preserved. Cloudflare records/settings are left
# in place by design; delete them in the dashboard if you want them fully gone.
```

---

## Values to fill before a live apply

In **vault.local.yml** (gitignored, never committed):
1. **`vault_hub_backend_ip`** - the backend IP (HARD secret).
2. **`vault_edge_public_ip`** - the edge's public IP (unknown until provisioned).
3. **`flutter_dist`** - local SPA `build/web` path.
4. (optional) the mTLS `*_content` vars incl. the mTLS PRIVATE KEY.

In **vault.yml** (encrypted, created from vault.example.yml):
5. `vault_cloudflare_api_token` (or override via an env file),
   `vault_cloudflare_account_id`, `vault_cloudflare_origin_cert`/`_key`
   (apex + wildcard), `vault_edge_ssh_key_path`.

Plus: `.vault_pass` created; `demo_subdomain`/`portfolio_dist` in vars.yml if the
defaults need overriding; the existing 1:1 edge<->hub mTLS pair in place at
`mtls_dir` on the edge + hub (or provide the `*_content` vars).
