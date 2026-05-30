# Writing Handoff Package - 2026-05-31

This package is for relay writing on the NCS manuscript. It is intentionally a writing/revision bundle, not a full raw-data archive.

## Current manuscript identity

Title:
`Release cards for scientific AI candidate queues under scarce verification and reference drift`

Core framing:
AI-for-science pipelines increasingly generate finite top-K candidate queues faster than those candidates can be verified. A ranked list is an incomplete scientific release unit under scarce one-sided verification. The manuscript frames release cards as AI-for-science release infrastructure: a versioned layer that decides certified release, certified refusal, active audit, expiry, recertification and risk triage before candidates enter downstream scientific records.

## Current editorial story

1. Universal gap: scientific AI candidate queues enter lineage graphs, DFT follow-up queues, building maps and ecological observations before exhaustive verification is possible.
2. Tool: PARC is one construction of a release-card lifecycle under one-sided partial verification. It uses verified-positive removal, a conservative null superset, block-maximum e-values and self-consistency.
3. Main positive: PARC-A in CTC. A 0.2% score-targeted one-sided positive reveal unlocks strict seed-stable release at K=100; matched-budget random reveal releases in 0/20 seeds and random reveal needs full calibration-set reveal in the frozen grid. Mechanism: targeted positives remove limiting null-superset block maxima at 182.5-fold the random rate.
4. Materials role: reference-drift stress test, not materials discovery. WBM shows that release cards must be versioned: old cards can expire under a later Materials Project hull, passive/active recertification can refuse, and durability risk can be triaged from the chemical-system reference neighborhood.
5. Cross-domain breadth: CTC cell links, WBM crystal candidates, SpaceNet building links and iWildCam animal-present detections are four scientific candidate objects sharing the same release-card lifecycle.

## What changed most recently

- Title changed to emphasize scientific AI candidate queues, scarce verification and reference drift.
- Abstract ends with the general-purpose hook: PARC turns AI-generated scientific top-K lists into auditable lifecycle decisions before they enter scientific records.
- Introduction now foregrounds the shared workflow structure across scientific AI pipelines.
- Results include an early capability table (`tab:capability`) comparing top-K, threshold/split-conformal, e-BH-style selection and PARC release cards by lifecycle state.
- Cover letter first screen now says a top-K ranked list is an incomplete scientific release unit under scarce verification.

## Main files

- `writing_source/main.tex`: manuscript source.
- `writing_source/references.bib`: bibliography.
- `writing_source/cover_letter.md`: current NCS cover letter.
- `writing_source/supplement/supplement.tex`: supplementary source.
- `writing_source/figures/`: rebuilt main-figure assets needed by `main.tex`.
- `writing_source/data/` and `writing_source/scripts/`: public-safe table/figure support used for manuscript-facing summaries.
- `current_pdfs/main.pdf`: current compiled manuscript.
- `current_pdfs/supplement.pdf`: current compiled supplementary information.
- `submission_release_snapshot/`: current upload-ready submission snapshot, including PDFs, cover letter, source-data folders, checksums and `upload.zip`.

## Verification status before packaging

- `make main.pdf` succeeded.
- `make supplement` succeeded.
- Current upload-ready `SHA256SUMS.txt` checked OK.
- `pdftotext main.pdf` finds the new title and `Release-card capabilities` table.
- AI-text-lint style scan:
  - front: clean
  - discussion: clean
  - results: one remaining `not a` hit from necessary `not animal` label text.
- Remaining LaTeX warnings are non-fatal layout/PDF-version warnings already present in the source workflow.

## Known editorial risk

The main unresolved editorial risk is not proof soundness. It is editorial undeniability. The strongest positive is still a masked-label CTC positive-reveal emulation. The best high-leverage empirical addition would be a real CTC one-sided audit mini-study:

- 400-800 link clips;
- strata such as PARC release, raw-only, boundary and random controls;
- two blind reviewers;
- labels: same-cell supported, unsupported, uncertain;
- report agreement and support rates;
- goal: show that scarce targeted audit supports a real release-card workflow, not only masked-label emulation.

Do not try to make the current materials section into a headline discovery. In this A manuscript, materials should remain a reference-drift stress test. A separate B manuscript could pursue external AI-materials claim-decay as a broader discovery audit.

## Suggested next writing actions

1. Inspect whether Table 1 should stay in the main text or be integrated into Figure 1/6 in final layout.
2. If no new audit is added, keep the cover letter candid: PARC-A is the positive result; materials is a stress test.
3. If a CTC real audit is added, update abstract, Fig. 2/Extended Data, cover letter and Methods together; do not let it appear as an afterthought.
4. Keep the central sentence visible: top-K is not the scientific release unit; the release card is.

