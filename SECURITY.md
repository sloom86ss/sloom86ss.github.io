# Security Policy — SLOOM365

## Supported deployment
SLOOM365 is a static website hosted on GitHub Pages.

## Reporting a vulnerability
Please report suspected security issues privately to the repository owner through GitHub's private vulnerability reporting feature when available. Do not publish passwords, API keys, tokens, or personal data in public issues.

## Security practices
- Never place API keys, access tokens, or private credentials in browser JavaScript or public repository files.
- Keep GitHub account two-factor authentication enabled.
- Review GitHub Actions permissions and workflow changes before merging.
- The site chat reads public match/news data only; it does not request passwords or sensitive information.
- Browser-side input checks are not a substitute for server-side validation or a web application firewall.

## Hosting limitation
GitHub Pages does not provide configurable origin response headers or a configurable web application firewall for the default github.io hostname. Strong edge filtering, custom security headers, and managed bot protection require a supported edge service and, typically, a domain controlled by the site owner.
