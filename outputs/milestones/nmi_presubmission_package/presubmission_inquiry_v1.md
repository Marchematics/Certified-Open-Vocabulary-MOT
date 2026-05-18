# Presubmission Inquiry v1

Dear Editors,

We would like to ask whether Nature Machine Intelligence would consider a manuscript on release-time certification for scientific AI candidate pipelines under one-sided partial verification.

Scientific AI systems increasingly produce ranked lists of candidate objects before exhaustive verification is available: candidate stable crystals for computational follow-up, cell-link evidence for lineage graphs, and visual detections or temporal links for ecological and geospatial monitoring. The central decision is not only how to score candidates, but when an AI system should release a finite set and when it should refuse because the available verification support is insufficient.

We introduce PARC, a release-time certification layer that takes a frozen finite candidate universe and returns either a certified release set or a certified refusal. The presubmission package deliberately separates completed headline evidence from diagnostics and pending protocols. In particular, prospective materials discovery is not claimed unless the separate MatterGen/DFT gates are met.

The completed headline evidence is:

- K=300: raw top-K FTR 0.253; PARC FTR 0.087; prevented 64.25 unstable follow-ups on average
- K=500: raw top-K FTR 0.327; PARC FTR 0.048; prevented 158.30 unstable follow-ups on average
- K=300: PARC released 300.0 learned cell-link candidates in 20/20 seeds with zero false lineage edges under official GT consequence proxies

The manuscript also includes completed audited boundary evidence: iWildCam provides an operational human-audited ecology release, while SpaceNet 7 provides a real-audit release/refusal boundary. External materials-source joins with OQMD and alex-mp are reported only as source-discordance stress tests, not as positive independent validation.

We believe the paper fits NMI because it targets an increasingly common AI-for-science governance problem: how to decide which model-generated scientific candidates may responsibly enter downstream workflows when verification is one-sided and incomplete. The contribution is a general release/refuse interface, supported by completed artifact-level evidence and by explicit guardrails that prevent protocol-only, pending, or discordant diagnostics from being overstated.
