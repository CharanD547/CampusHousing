# Private LAN development

The active FastAPI/Uvicorn service was restarted on October 24, 2026 with:

```powershell
.\.venv\Scripts\python.exe -m uvicorn roomwise.main:app --app-dir src --host 0.0.0.0 --port 8001
```

This serves both frontend and backend; no Vite/Flask/Django server is needed. `0.0.0.0` is the listen address, not the address to enter on another device.

Current Wi-Fi address: **http://10.0.0.182:8001/**. Devices must be on a network that can reach this computer; the address can change with DHCP. The server listens on all IPv4 interfaces, not just Wi-Fi.

An operator bearer token is configured in ignored `.env`. Explicit `ROOMWISE_LOCAL_OPERATOR_ENABLED=true` now allows automatic access only when both the connecting client and URL are loopback, with same-origin checks. Open `http://127.0.0.1:8001/` on the server computer without a token prompt. Other devices/LAN-address requests still need the operator token from ignored `var/lan-access.txt` in the Backend access token form. It is a Roomwise operator token, not a Google key. The token grants access to the existing operator's records. Use trusted testers/private networks only; plain HTTP does not encrypt the token or traffic. Do not publish the access file or configure router port forwarding for this development server.

Verification from this machine succeeded using both loopback and the LAN address: page HTTP 200; loopback API automatically HTTP 200 with the explicit local operator setting; LAN API without a token HTTP 401 and with the token HTTP 200. Both existing Chrome tabs were verified connected. `Get-NetTCPConnection` confirmed `0.0.0.0:8001`. This does not prove a separate device can traverse Wi-Fi client isolation or Windows Firewall. No firewall rule or router configuration was changed. If another device cannot connect, check that it is on the same reachable network and that the private-network firewall policy permits the development port.

The frontend now supports LAN HTTP without `crypto.randomUUID`, which requires a secure context. It uses cryptographically random UUIDs via `getRandomValues` as a fallback; five frontend checks passed. Google Maps browser-key referrer restrictions may also need an owner-approved LAN/development origin; no provider restriction was changed and LAN-origin Maps authorization has not been verified.

To return to loopback-only service, restart with `--host 127.0.0.1`. Keep credentials out of commands/URLs and source control. For a shared public pilot, use HTTPS, individual access controls and the release gates in the completion report.
