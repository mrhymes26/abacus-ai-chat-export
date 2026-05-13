# Security policy

## Supported versions

Security fixes are applied to the **latest minor release** in the **1.x** line (see [CHANGELOG.md](CHANGELOG.md)). Use the current release tag or default branch.

## Reporting a vulnerability

Please report security issues **privately**:

- Use **GitHub Security Advisories** if the repository has them enabled: **Security** tab → **Report a vulnerability**.
- Otherwise contact the repository maintainers through a **private** channel (for example a maintainer email listed on the profile or organization site).

Do **not** post Abacus.AI API keys, passwords, or contents of backups in public issues or discussions.

## Scope notes

This application is intended to run **locally** (for example Docker on your machine). If you expose it to a network, use strong authentication (for example `APP_BASIC_AUTH_*`) and restrict access. Backups contain sensitive chat data; protect the Docker volume and any downloaded ZIP files like any other confidential material.
