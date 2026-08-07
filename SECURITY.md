# Security policy

## Supported versions

Security fixes are made on the latest published `0.2.x` release line. Older patch releases may
be used to understand impact, but users should upgrade to the newest patch before requesting a
backport.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Submit a private report through the
[GitHub security advisory form](https://github.com/NeuralBinary/SAGE/security/advisories/new).
Include the affected version, deployment assumptions, reproduction steps or a proof of concept,
potential impact, and any suggested mitigation. Remove real credentials, customer data, and
private model inputs from the report.

Maintainers aim to acknowledge a complete report within three business days and provide an
initial triage within seven business days. These are response targets, not a disclosure SLA.
Reporter and maintainer should coordinate disclosure after a fix or mitigation is available.

## Security boundaries

The operational security model, credential and network requirements, reference authorization,
signature handling, and production configuration are documented in
[docs/SECURITY.md](docs/SECURITY.md). Threats, trust boundaries, and mitigations are cataloged
in [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).

Local unauthenticated mode is for a trusted loopback development environment only. Production
deployments must use authentication, managed migrations, a server database, explicit allowed
hosts, TLS at the deployment boundary, and appropriately managed signing and encryption keys.
