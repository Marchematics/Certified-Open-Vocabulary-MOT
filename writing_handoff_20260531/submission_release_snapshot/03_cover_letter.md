Dear Editors,

Scientific AI systems increasingly generate candidate objects faster than they can be verified. These objects enter downstream scientific records: lineage graphs, DFT follow-up queues, building maps and ecological observations. A top-\(K\) ranked list is therefore an incomplete scientific release unit under scarce verification. We submit this manuscript as an Article for Nature Computational Science because it introduces release cards as a computational layer that decides release, refusal, audit, expiry and recertification under scarce one-sided verification.

The manuscript introduces PARC, one construction of this release-card lifecycle framework for finite scientific AI candidate queues. PARC keeps unverified candidates in a conservative null superset, constructs block-maximum e-values and returns explicit release-card states: certified release, certified refusal, active audit, expiry, recertification and risk triage. This is intended as reusable AI-for-science release infrastructure between candidate generators and downstream workflows, with prediction, tracking, detection and ranking treated as upstream inputs.

The primary constructive result is PARC-A in cell tracking. In a CTC release task, a 0.2% score-targeted one-sided positive-reveal budget unlocks strict certified release at K = 100 with 20/20 non-empty safe masks and observed FTR 0.000, while matched-budget random reveal releases in 0/20 masks and random reveal requires full calibration-set reveal in the frozen grid. Mechanistically, targeted positives remove limiting null-superset block maxima at 182.5-fold the random rate. This gives a concrete positive message for a diverse computational-science readership: scarce verification can be converted into certified release when it is spent at the right candidates.

The materials experiments play a different role. They are scoped as a reference-drift stress test showing why release cards must be versioned. In WBM materials screening, a certificate calibrated under one public hull can expire under a later Materials Project hull, passive and active recertification can refuse, and durability risk can be triaged from the chemical-system reference neighborhood. These experiments are outside prospective discovery, independent DFT validation and current-MP alpha certification. Together with SpaceNet and iWildCam operating envelopes, they show that the same release-card lifecycle applies across multiple scientific candidate objects while preserving explicit claim boundaries.

The public-safe code, derived outputs, provenance manifests and reproducibility materials supporting the manuscript are archived at https://doi.org/10.5281/zenodo.20395413. The development repository is available at https://github.com/Marchematics/PARC-Certified-Open-Vocabulary-MOT.

This manuscript is not under consideration elsewhere, and all authors have approved the submission.

Sincerely,

The authors
