# Docker connectivity troubleshooting

Validated 2026-07-21 on Windows with Docker Desktop 29.5.3, Compose 5.1.4 and the WSL2 6.18.33.2 kernel.

## Incident and result

Image pulls originally failed because Docker Desktop and its `docker-desktop` WSL distribution were stopped. This was a host-state problem, not an application or registry DNS defect. Windows resolved `registry-1.docker.io`, `auth.docker.io`, and Docker's Cloudflare production endpoint and reached each on TCP 443. WSL resolution also worked. There was no user proxy environment variable, WinHTTP was direct, and the user daemon configuration contained no DNS override. Docker Desktop was started normally; no reset, credential removal, DNS change, or application change was made.

After startup the engine reported its expected internal proxy (`docker.internal:3128`). `alpine:3.21` pulled successfully. In the container, Docker DNS `192.168.65.7` resolved the registry and HTTPS returned the expected unauthenticated HTTP 401 from `/v2/`, proving routing, DNS and TLS worked.

## Safe verification

```powershell
docker version
docker compose version
Resolve-DnsName registry-1.docker.io
Resolve-DnsName auth.docker.io
Test-NetConnection registry-1.docker.io -Port 443
docker pull alpine:3.21
docker run --rm alpine:3.21 nslookup registry-1.docker.io
docker info
Get-ChildItem Env: | Where-Object Name -Match 'proxy'
netsh winhttp show proxy
wsl --list --verbose
```

If the daemon is stopped, start Docker Desktop from the Start menu and wait for `docker version` to show both client and server. If DNS fails only in containers, inspect `%USERPROFILE%\.docker\daemon.json` and Docker Desktop proxy settings before changing them.

## Approval-required escalation

Do not silently use “Reset to factory defaults”, remove Docker credentials, reinstall Docker Desktop, reset Windows networking, disable a VPN/firewall, run `wsl --shutdown`, or delete WSL distributions. Capture `docker info`, DNS/TCP results and Docker Desktop diagnostics, then obtain human approval. A temporary Hub outage should be verified against Docker status and retried before local resets.

