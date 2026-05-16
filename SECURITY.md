# Security Policy

This repository is a research artifact and reproducibility package.  It does
not provide a network service, hosted API, or production deployment.

## Supported Versions

The public branch and tagged public-safe releases are maintained for
reproducibility issues.  Historical experiment branches may not receive fixes.

## Reporting Issues

Please report security or privacy issues through GitHub issues if they do not
contain sensitive information.  If a report involves private paths, accidental
raw-data inclusion, credentials, or dataset-license concerns, avoid posting the
sensitive content publicly and contact the repository maintainers privately.

## Public-Safe Data Boundary

The package should not contain raw videos, raw images, raw dataset annotations,
model weights, credentials, access tokens, caches, or private local paths.  The
included validation script checks common public-bundle hazards:

```bash
python scripts/validate_public_bundle.py outputs/milestones/reliability_fortress
```

If you find a public-safety leak, treat it as a release-blocking issue.
