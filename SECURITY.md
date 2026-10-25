# Security policy

## Reporting a vulnerability

Please do not open a public issue for a security problem. Report it privately through GitHub's **Report a vulnerability** option on this repository's Security tab, or contact the maintainer through the repository profile.

Include:

- A description of the issue and its impact
- Steps to reproduce, or a minimal request that demonstrates it
- The commit or version you tested

You can expect an acknowledgement within a few working days. Please allow time for a fix before public disclosure.

## Scope and expectations

Roomwise is designed for a single local operator on a loopback address by default. Reports about exposing it to a network without the documented safeguards (see [operations](docs/OPERATIONS.md) and [LAN access](docs/LAN_DEVELOPMENT.md)) are still welcome, but please distinguish between a flaw and a misconfiguration.

## Secrets

- Never commit `.env` files, provider keys, backend bearer tokens or local databases.
- Google's Maps JavaScript key is delivered to the browser by design. Private Places, Routes and model credentials stay on the server.
- If you accidentally publish a secret, rotate it first, then report it.
