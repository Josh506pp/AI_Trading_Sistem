# Cloudflare Tunnel Setup

This folder holds the template for a named Cloudflare Tunnel.

## How to use

1. Copy `config.yml.example` to `config.yml`.
2. Replace `YOUR_TUNNEL_NAME_OR_ID` with your tunnel name or UUID.
3. Replace `credentials-file` with the path to the tunnel credentials JSON created by Cloudflare.
4. Keep the hostname set to `candlekiller.dpdns.org` unless your registered FreeDomain name is different.
5. Start the app with:

```powershell
$env:CF_TUNNEL_NAME = 'trading-system'
$env:CF_TUNNEL_HOSTNAME = 'candlekiller.dpdns.org'
$env:CF_TUNNEL_CONFIG = 'C:\path\to\cloudflared\config.yml'
./start_with_cloudflare.ps1
```

## Notes

- Keep the credentials file private.
- Use DigitalPlat FreeDomain only for registration and delegation.
- Use Cloudflare DNS for the public hostname and tunnel routing.