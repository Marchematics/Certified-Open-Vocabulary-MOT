# Related-Work Positioning Notes

Web-checked references (2026-05-13):

- Angelopoulos, Bates, Fisch, Lei, and Schuster, *Conformal Risk Control*, arXiv:2208.02814, https://arxiv.org/abs/2208.02814. PARC differs by controlling set-level release under path conflicts and incomplete annotations.
- Angelopoulos et al., *Conformal Risk Control for Non-Monotonic Losses*, arXiv:2602.20151, https://arxiv.org/abs/2602.20151. This is relevant for non-monotone/discrete-grid risk; PARC's SCS feasibility and null-superset audit mechanism are the tracking-specific additions.
- Wang and Ramdas, *False discovery rate control with e-values*, arXiv:2009.02824 / JRSSB, https://arxiv.org/abs/2009.02824. PARC uses e-value-style evidence but couples it to path compatibility and a uniform SCS release rule rather than applying e-BH directly.
- Vovk, *Conformal e-prediction*, arXiv:2001.05989 / Pattern Recognition, https://arxiv.org/abs/2001.05989. PARC is closest in spirit to e-value conformal evidence, but targets auditable release-time decisions under partial labels.

Suggested prose: PARC is not a replacement for CRC or e-BH. It combines conformal/e-value evidence with a one-sided audit protocol and a compatibility-constrained selector for open-world perception outputs.
