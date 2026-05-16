# Limitations

PARC is designed as a release/refusal layer for finite candidate universes under
one-sided partial verification.  The public package is intentionally explicit
about where this interface is powerful and where it refuses.

## Scope of the Certificate

- PARC certifies a released subset, not the full candidate universe.
- The guarantee is an expected false-release-fraction guarantee for the
  released set, not a per-candidate truth certificate and not a high-probability
  guarantee for every run.
- Empty release is a valid certified outcome when evidence mass, coverage, or
  compatibility constraints are insufficient.

## Verification Assumptions

- The one-sided verified-positive rule is essential: verified positives must be
  high precision.
- Uncertain or disputed labels remain unverified.
- If the positive rule is semantically wrong, as in fine-grained prompt
  misgrounding, the row should be reported as an assumption-boundary diagnostic.

## Blocks and Exchangeability

- Domain-respecting blocks are part of the protocol, not a cosmetic
  hyperparameter.
- Block sensitivity and coverage diagnostics should be reported for each
  primary domain.
- Rows with poor coverage should be interpreted as covered-regime or refusal
  diagnostics.

## Public Package Boundary

This repository excludes raw videos, raw images, raw annotations, raw crystal
structures, model weights, detector/tracker repositories, Hugging Face caches,
GPU caches, frame caches, and montage images.  Full end-to-end regeneration
requires downloading original datasets and proposal-generator outputs from
their maintainers.

## Domain Status

- CTC learned-hybrid and materials discovery provide strict `alpha=0.10`
  controlled partial-verification evidence.
- CTC strict human-audit closeout confirms the reviewed strict-release queue,
  but does not claim microscopy-expert adjudication unless separately
  documented.
- iWildCam is an operational human-audited ecology release at `alpha=0.20`;
  strict `alpha=0.10` remains certified refusal.
- SpaceNet 7 real audit is a release/refusal workflow check: K=50 is diagnostic
  low-volume success and K=100 is certified refusal.
- Proposed molecular/protein extensions in the success map are protocol-only
  and must not be cited as completed evidence.
