# Security Policy

ResearchInfra stores research state in local files and should not require cloud
accounts or embedded credentials.

## Reporting Vulnerabilities

Please report suspected vulnerabilities privately to the maintainers. Include a
clear description, affected versions or commits, reproduction steps, and any
known mitigations.

## Secrets

Do not commit API keys, tokens, passwords, private datasets, or confidential
review materials. Provider credentials should be supplied through environment
variables or caller-managed secret stores.

