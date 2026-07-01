# Reference IaC: hardened Cloudflare + reverse-proxy edge with a private mTLS backend

Reproducible Infrastructure-as-Code (Ansible) for a common production pattern:
publish a **static site** at the apex domain and a **static SPA + JSON API** at a
subdomain, both behind **Cloudflare**, terminating on a small **hardened
reverse-proxy VPS ("edge")**. The heavy application backend (the **"hub"**) stays
completely private and is reachable ONLY by the edge over a **1:1 mutual-TLS leg**,
so the backend's IP never appears in DNS, in a committed file, or in a log.

This repo is a sanitized **reference architecture** extracted from a real
deployment. All hostnames, IPs, domains and secrets have been replaced with
obvious placeholders (`example.com`, `edge-01`, `deploy`, `YOUR_*`, `FILL_ME-*`).
Fill in the vault values for your own environment before applying. Nothing here
runs against anything until you provide real values and choose to apply.

## Architecture

```
        example.com + www              chat.example.com
        (PROXIED A records)            (PROXIED A record)
                   \                    /
  client --HTTPS:443--> Cloudflare edge
                   |   - terminates PUBLIC TLS (edge cert, automatic)
                   |   - hides origin IPs (proxied / orange-cloud)
                   |   - Security Level HIGH + Bot Fight Mode (managed challenge
                   |     to suspicious traffic = primary bot defense)
                   |   - rate-limit on the API path (protect the backend)
                   |   - SSL "Full (strict)" + Authenticated Origin Pulls to origin
                   v
             edge VPS - public nginx, ufw: 22 + 443-from-Cloudflare-only
              |  vhost 1: example.com + www  = PURE STATIC site (no /api)
              |  vhost 2: chat.example.com   = static SPA at "/"  + "/api/" --,
              |                                                                |
              |  (CF Origin cert + AOP on both vhosts)                         |
              v                                                                |
   edge presents its CLIENT cert  --- 1:1 mutual TLS -------------------------->'
                                                                               v
                                    hub nginx (mTLS terminator, requires the edge
                                    client cert; ssl_verify_client on) -> app on
                                    127.0.0.1  (hub ufw admits ONLY the edge IP)
```

The static site touches no backend. Only the SPA `/api` reaches the hub, over
mutual TLS, and the hub answers only to the edge. Public visitors are managed-
challenged by Cloudflare rather than blocked by a login wall.

## Layout

```
.
  ansible.cfg                      inventory + ssh defaults
  requirements.yml                 Galaxy collections (community.general, ansible.posix)
  site.yml                         full deploy: cloudflare -> edge
  RUNBOOK.md                       exact ordered apply + verify commands (READ THIS)
  inventory/hosts.yml              parameterized edge + cloudflare + hub (no real values)
  group_vars/all/
    vars.yml                       non-secret config + references to vault_* (committed)
    vault.example.yml              plaintext placeholders documenting vault.yml
    vault.local.example.yml        placeholders for the never-commit values
  playbooks/
    bootstrap.yml                  first-contact: install + verify the automation key
    harden.yml                     edge_base ufw + full host hardening (key-only SSH, etc.)
    cloudflare.yml                 CF edge: DNS (apex+www+chat) + SSL + security + rate-limit
    edge.yml                       edge_base + edge_proxy (two vhosts)
    hub.yml                        PREP / DO-NOT-APPLY: hub_mtls_proxy + hub_allowlist
    teardown.yml                   remove our changes (mTLS pair preserved)
  roles/
    edge_base/                     ufw: deny-in, 22, 443-from-Cloudflare-only
    edge_proxy/                    nginx: Origin cert + AOP, apex static vhost +
      templates/portfolio.conf.j2    SPA vhost (static + /api over mTLS)
      templates/demo.conf.j2
    cloudflare_edge/               CF API: dns/ssl/security/ratelimit/per-hostname AOP
    hardening/                     sshd key-only (anti-lockout), fail2ban, unattended
                                   security upgrades, sysctl, swap, egress lockdown
    hub_mtls_proxy/                PREP: hub nginx terminating the mTLS leg -> app
      templates/hub-mtls.conf.j2
    hub_allowlist/                 PREP: ufw allow ONLY the edge -> hub mTLS port
  .ansible-lint / .gitignore
```

## TLS / cert summary

| Leg | Server cert | Client cert | Verifies against |
| --- | --- | --- | --- |
| client -> Cloudflare | Cloudflare edge cert (auto) | - | public CAs |
| Cloudflare -> edge | CF **Origin cert** (apex + wildcard) on the edge | Cloudflare AOP client cert | edge: AOP CA (`ssl_verify_client`) |
| edge -> hub (API only) | hub server cert (1:1 pair) | **edge client cert** (1:1 pair) | shared mTLS CA, both ends |

The 1:1 edge<->hub pair is referenced by path under `mtls_dir` and regenerates
nothing. `proxy_ssl_name` is set to the hub cert CN (`hub_mtls_server_name`),
never the hub IP, so the upstream is verified without leaking the address.
Private keys are gitignored / vaulted only.

## Cloudflare token scopes

Use a single scoped token (NOT the Global API Key): **Zone:Read**,
**Zone.DNS:Edit**, **Zone.SSL and Certificates:Edit**, **Zone Settings:Edit**,
**Zone WAF:Edit**, **Zone Rate Limit:Edit**. Keep it in the encrypted vault or an
untracked env file; never commit or echo it.

## Secrets model (ansible-vault, not third-party secret stores)

A third-party secret store would place the backend IP on someone else's
infrastructure, which breaks the "never expose the backend IP" rule. Instead this
repo uses ansible-vault, and the two truly-never-commit values stay out of git
entirely. Three tiers:

| File | Committed? | Holds |
| --- | --- | --- |
| `group_vars/all/vars.yml` | yes, plaintext | non-secret config; maps friendly names to `vault_*` |
| `group_vars/all/vault.yml` | **no** in this reference repo (gitignored); encrypt with ansible-vault in your own copy | rotatable secrets: CF API token, CF Origin cert+key, SSH key path |
| `group_vars/all/vault.local.yml` | **no (gitignored)** | HARD-EXCEPTION values: `hub_backend_ip` + the edge<->hub mTLS **private key** (+ the edge public IP) |

> This reference repo ships only the `*.example.yml` placeholder files. Create your
> own `vault.yml` from `vault.example.yml` and encrypt it with `ansible-vault`;
> create your own `vault.local.yml` from `vault.local.example.yml`. Both real files
> are gitignored so they can never be committed by accident.

Workflow:

```
# 1. Vault password (gitignored). ansible.cfg points vault_password_file at it.
echo 'your-strong-vault-password' > .vault_pass && chmod 600 .vault_pass

# 2. Rotatable secrets -> encrypted vault.yml:
cp group_vars/all/vault.example.yml group_vars/all/vault.yml
ansible-vault encrypt group_vars/all/vault.yml
ansible-vault edit group_vars/all/vault.yml            # put real values

# 3. The never-commit values -> gitignored vault.local.yml:
cp group_vars/all/vault.local.example.yml group_vars/all/vault.local.yml
$EDITOR group_vars/all/vault.local.yml                 # backend IP + mTLS private key
```

The backend IP and the mTLS private key are never committed at all, encrypted or
not.

## Apply

See **RUNBOOK.md** for the exact ordered commands. In short:

```
echo 'your-vault-password' > .vault_pass && chmod 600 .vault_pass
cp group_vars/all/vault.local.example.yml group_vars/all/vault.local.yml && $EDITOR group_vars/all/vault.local.yml
cp group_vars/all/vault.example.yml group_vars/all/vault.yml && ansible-vault encrypt group_vars/all/vault.yml && ansible-vault edit group_vars/all/vault.yml
ansible-galaxy collection install -r requirements.yml
ansible-playbook playbooks/bootstrap.yml               # install + verify the automation key
ansible-playbook playbooks/harden.yml                  # ufw + key-only SSH + host hardening
ansible-playbook site.yml                              # Cloudflare edge + edge reverse proxy
ansible-playbook playbooks/hub.yml --check             # hub side is PREP; apply only when ready
```

## Security / coexistence notes

- **Public site, no login gate.** Bot defense is Cloudflare Security Level High +
  Bot Fight Mode (managed challenge) and an `/api` rate-limit, not basic-auth.
- **No certbot.** Public TLS is Cloudflare's edge cert; the edge holds only the CF
  Origin cert (Full strict) for the Cloudflare->edge hop, with Authenticated
  Origin Pulls + ufw 443-from-Cloudflare-only (Cloudflare-only at both layers).
- **Backend stays private.** Only the SPA `/api` reaches it, over mutual TLS; the
  hub nginx requires the edge's client cert and the hub ufw admits only the edge's
  IP. The backend IP is a vault-only secret, never in DNS or a committed file.
- The roles only add their own nginx/ufw; teardown removes only those changes and
  never deletes a pre-existing mTLS pair.
- No secrets, IPs, keys, tokens or real domains are committed. Only the
  `*.example.yml` placeholder files are tracked.

## Verify before a live apply

- The edge + hub OS family is Debian/Ubuntu (apt); nginx/ufw available.
- The CF Origin cert covers `example.com` AND `*.example.com` (your real domain).
- `edge_public_ip` + `hub_backend_ip` filled (no `FILL_ME`); `portfolio_dist` +
  `flutter_dist` point at real build outputs.
- The 1:1 edge<->hub mTLS pair is in place at `mtls_dir` on both hosts (or the
  `*_content` vars are set).
- `ansible-playbook site.yml --syntax-check` and `ansible-lint` are clean; then
  dry-run with `--check` before applying.
