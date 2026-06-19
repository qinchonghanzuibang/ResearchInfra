# Security Policy

ResearchInfra stores research state in local files and should not require cloud
accounts or embedded credentials.

## Reporting Vulnerabilities

Use GitHub's private vulnerability reporting for this repository when the
**Security** tab offers a **Report a vulnerability** action. Do not include a
proof of concept or sensitive details in a public issue.

If private reporting is not available, open a minimal GitHub Issue asking the
maintainers for a private contact channel, without disclosing vulnerability
details. Include a clear description, affected versions or commits,
reproduction steps, and known mitigations once a private channel is arranged.

## Secrets

Do not commit API keys, tokens, passwords, private datasets, or confidential
review materials. Provider credentials should be supplied through environment
variables or caller-managed secret stores.
