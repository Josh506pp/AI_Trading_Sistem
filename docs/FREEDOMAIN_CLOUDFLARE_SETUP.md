# FreeDomain + Cloudflare Domain Setup

This project follows the DigitalPlat FreeDomain model: DigitalPlat is used for registration and delegation, while ordinary DNS records are managed in an external authoritative DNS service such as Cloudflare.

## What the repository means for this app

1. Register the FreeDomain name in DigitalPlat.
2. In DigitalPlat, set the assigned Cloudflare nameservers.
3. In Cloudflare, create the DNS entry for the hostname you want to use.
4. Point that hostname to this app through a named Cloudflare Tunnel or a CNAME target, depending on your setup.

DigitalPlat itself does not provide a normal DNS editor for A, AAAA, or CNAME records. That part belongs in Cloudflare.

## Recommended setup for this trading dashboard

Use the registered FreeDomain host `candlekiller.dpdns.org` as the public name for this dashboard.

### Option A: Named Cloudflare Tunnel, recommended

Use this when you want the app available without exposing your home IP.

1. Register the domain in DigitalPlat.
2. Add the domain to Cloudflare.
3. Copy the Cloudflare nameservers into DigitalPlat.
4. Wait for delegation to become active.
5. Create a Cloudflare Tunnel and a DNS route for the hostname.
6. Run the app with `start_with_cloudflare.ps1` and set:

```powershell
$env:CF_TUNNEL_NAME = 'trading-system'
$env:CF_TUNNEL_HOSTNAME = 'candlekiller.dpdns.org'
$env:CF_TUNNEL_CONFIG = 'C:\path\to\cloudflared\config.yml'
./start_with_cloudflare.ps1
```

The startup script will use the named tunnel when those values are present.

If you need a template, copy `cloudflared/config.yml.example` to `cloudflared/config.yml` and fill in the real tunnel values.

### Automated setup command

After `cloudflared tunnel login` is completed, you can run one command from project root:

```powershell
.\tools\setup_freedomain_cloudflare.ps1 -Domain candlekiller.dpdns.org -TunnelName trading-system -LocalPort 5000
```

This command creates or reuses the named tunnel, configures DNS routing, and writes `cloudflared/config.yml` automatically.

### Option B: Temporary quick tunnel

Use this only for testing.

```powershell
./start_with_cloudflare.ps1
```

This produces a temporary `trycloudflare.com` URL.

## Cloudflare DNS record pattern

For a named tunnel, use the hostname you want the public to visit, such as `candlekiller.dpdns.org`.

The exact DNS target depends on the tunnel type and Cloudflare's current tooling. The safe rule is:

- Use DigitalPlat only for delegation.
- Use Cloudflare for DNS records.
- Use Cloudflare Tunnel or your host provider to reach the app.

## Production checklist

- FreeDomain registered and active.
- Cloudflare nameservers copied into DigitalPlat.
- DNS delegation confirmed.
- Named tunnel or target hostname created.
- `candlekiller.dpdns.org` opens the dashboard.
- `/api/status` responds over HTTPS.
- A rollback path exists if the tunnel or DNS changes break access.

## Important note for MT5

If MT5 control is required, the app still needs to run on a Windows machine that has MT5 available.
Cloudflare only handles public access to the web dashboard; it does not replace the MT5 terminal.