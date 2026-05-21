# Auto Review Loop

Started: 2026-05-21T17:25:34.180457+00:00

Context: Autonomous review after phase36; focus on whether current non-A3 evidence package is submission-ready and what minimum fixes remain.


## Round 1 (2026-05-21T17:27:02.725298+00:00)

### Assessment (Summary)
- Score: 5.5/10
- Verdict: Almost, not ready as broad discovery paper
- Key criticisms: no completed prospective discovery evidence; external materials validation is discordant; external blind audit labels pending; novelty may read as wrapper; breadth must be two-anchor; utility wording must emphasize stopping/refusal; clean submission artifact index needed.

### Reviewer Raw Response

<details>
<summary>Click to expand full reviewer response</summary>

**Score: 5.5/10 for Nature Machine Intelligence readiness.**

**Verdict: Almost, but only as a narrow release-governance paper. Not ready as a broad scientific AI discovery paper.** If the manuscript still implies prospective materials discovery, independent external materials validation, or broad cross-domain reliability, the answer is **No**.

**Critical Weaknesses**

1. **No completed prospective scientific discovery evidence.**
   Materials is currently a retrospective/public-label fixed-budget utility result. That is useful, but it is not discovery.
   **Minimum fix:** either complete A3 under the frozen gate with `released_n >= 25`, `dft_completed_n >= 25`, and primary DFT FTR `<= alpha`, or fully remove prospective discovery language from title, abstract, intro, figures, and claims.

2. **Materials external validation is negative/discordant, not confirmatory.**
   OQMD/alex-mp and MP-Alex discordance show label-source fragility. They help the honesty of the paper, but they weaken any “independent validation” story.
   **Minimum fix:** make this a limitation/stress-test panel, not validation. Explicitly state that external databases are non-interchangeable label sources and that PARC certification is relative to the declared verification source.

3. **External blind audit is frozen but unlabeled.**
   A frozen 484-item audit packet is good process evidence, not result evidence.
   **Minimum fix:** either get the blind labels/adjudication completed and report them conservatively, or move the packet to “pending external audit” with no positive evidentiary weight.

4. **The main novelty may read as wrapper/incremental.**
   Reviewers may say: e-values + conformal/selective release + multiple testing, applied to candidate queues.
   **Minimum fix:** sharpen the contribution around the release/refuse object: fixed finite candidate universe, one-sided partial positives, block-calibrated e-values, SCS release/refusal, and scientific governance consequences. Include direct comparator table showing why PU/conformal/e-BH/threshold baselines do not solve the same release/refuse contract.

5. **Breadth still looks fragile.**
   Strongest completed anchors are materials public-label utility and CTC strict artifact consequence. iWildCam/SpaceNet are boundary/audit/refusal examples, not equal pillars.
   **Minimum fix:** present a two-anchor paper: materials queue governance plus CTC scientific artifact protection. Put iWildCam/SpaceNet in a boundary/robustness section.

6. **Utility claim needs careful wording.**
   PARC improves certified stopping/refusal and reduces false follow-ups; it does not necessarily improve fixed-size ranking quality.
   **Minimum fix:** make “raw top-R matched-volume diagnostic” visually secondary. Lead with “false follow-ups prevented,” “cost per true candidate,” and “certified refusal at unsafe K.”

7. **Repository/package hygiene risk remains.**
   Dirty/untracked A3/QE/discordance files could confuse reviewers or artifact evaluators.
   **Minimum fix:** freeze a clean submission artifact index where every claim-bearing row is tagged `primary`, `secondary`, `diagnostic`, `pending`, or `forbidden`, and ensure no pending A3 material appears in main evidence tables.

**Submission Call**

**Almost** for a carefully scoped NMI presubmission inquiry on *release-time certification/governance for scientific AI candidate pipelines*.

**No** for full NMI submission if the paper depends on prospective materials discovery, positive independent materials validation, or the pending blind audit. The credible submission version is narrower, honest, and potentially interesting: PARC as a release/refuse certification layer with strong CTC and retrospective materials utility evidence, plus explicit refusal and source-discordance diagnostics.

</details>

### Actions Taken
- Pending: implement scope-lock artifacts and comparator contract tables.

### Results
- Pending.

### Status
- Continuing to Round 2 after fixes.
