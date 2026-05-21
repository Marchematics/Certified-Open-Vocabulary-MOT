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


## Round 2 (2026-05-21T17:31:53+00:00)

### Assessment (Summary)
- Score: 6.5/10
- Verdict: ready for NMI presubmission inquiry; almost, but not yet ready, for full submission.
- Key criticisms: final manuscript text still needs forbidden-claim compliance; comparator contract table must be tied to formal target objects; materials must remain public-label queue utility rather than materials science discovery; CTC artifact consequence needs exact denominator/source wording; release should be made from a clean tagged commit or release branch.

### Reviewer Raw Response

<details>
<summary>Click to expand full reviewer response</summary>

**Score: 6.5/10 for NMI readiness under the narrow release-governance framing.**

**Verdict: ready for NMI presubmission inquiry; almost, but not yet ready, for full submission.**

Phase37 materially addresses my Round 1 framing objections. The two-anchor evidence hierarchy, forbidden-claim replacements, and release/refuse comparator matrix are the right governance move. I would no longer reject the package for scope confusion if the manuscript actually follows this lock.

**Remaining Critical Weaknesses**

1. **The evidence package is still narrow: no prospective discovery, no positive independent external validation.**  
   This is acceptable only if the paper is explicitly about release-time governance, not scientific discovery performance.  
   **Minimum fix:** keep title/abstract/intro centered on “release/refuse certification for fixed candidate universes under partial verification.” Treat A3, external blind audit, OQMD/alex-mp, Route C as pending/diagnostic only.

2. **Scope lock exists as an artifact, but the final manuscript still needs to prove compliance.**  
   A reviewer will judge the paper text, figures, captions, and supplement, not just the phase37 tables.  
   **Minimum fix:** run a final forbidden-claim audit over manuscript, abstract, figure captions, README, claim table, and supplement. Forbidden terms can appear only in limitation/guardrail contexts.

3. **Comparator matrix is necessary but may look self-serving unless tied to formal target objects.**  
   Saying only PARC solves the full contract is plausible, but reviewers will push on e-BH, selective conformal, and PU baselines.  
   **Minimum fix:** include the comparator table with exact target object, assumptions, deployable rule, and missing contract component. Do not oversell baselines as “wrong”; say they solve different contracts.

4. **Materials anchor remains public-label replay utility.**  
   The K=500 result is strong as queue governance, but weak as materials science evidence.  
   **Minimum fix:** keep the lead as “public-label follow-up queue utility,” report raw top-K and raw top-R diagnostics, and place source-discordance stress results immediately nearby to prevent overinterpretation.

5. **CTC anchor needs very clean artifact-consequence wording.**  
   “0 false lineage edges” is compelling, but only if denominator, audit/GT source, and corruption-control behavior are transparent.  
   **Minimum fix:** define false lineage edge, state this is not an official leaderboard tracker score, and show strict alpha/K, held-out/audit FTR, and corrupted-ranking refusal in one compact table.

6. **Artifact hygiene is still a submission risk.**  
   I observed a dirty worktree with tracked modifications and untracked pending/probe material after `79e0cb2`. I am not counting those as evidence, but they could confuse artifact review.  
   **Minimum fix:** submit from a clean tagged commit or clean release branch. Keep phase37 validation in the pre-release checks, and exclude or clearly mark unrelated A3/QE/discordance work.

**Bottom Line**

The Round 1 concerns are addressed enough for **NMI presubmission**. For **full submission**, I would wait until the actual manuscript is fully scope-locked and the repository is clean. No need to wait for A3 or external blind labels if the paper is honestly framed as release-governance, but any drift back toward discovery or broad validation would drop this back below the line.

</details>

### Actions Taken
- Stopped the autonomous review loop because Round 2 met the configured stop condition: score >= 6 and verdict contains ready/almost.
- Preserved the reviewer’s raw response verbatim.
- Updated `review-stage/REVIEW_STATE.json` to `completed`.
- Added `CLAIMS_FROM_RESULTS.md` with the supported, unsupported, and remaining-evidence claims extracted from the completed review loop.

### Results
- Final loop score progression: 5.5/10 -> 6.5/10.
- Final decision: suitable for NMI presubmission inquiry under a narrow release-governance framing; not yet clean enough for full submission without manuscript-level forbidden-claim audit and a clean release branch.

### Status
- Stopping after Round 2.


## Final Summary

The autonomous review loop converged after two rounds. The Round 1 reviewer objected that the package was not credible as a broad scientific discovery paper because A3 remained non-positive/pending, external materials validation was discordant, and the blind audit packet was unlabeled. Phase37 addressed this by locking the submission to two completed hard anchors: materials fixed-budget public-DFT queue governance and CTC strict scientific-artifact protection. iWildCam/SpaceNet remain audited boundary evidence; OQMD/alex-mp and MP-Alex remain source-discordance stress tests; A3 remains pending/failed-gate material until DFT gates are actually met.

The Round 2 reviewer accepted the narrow framing for NMI presubmission and raised remaining full-submission tasks: audit the actual manuscript text and captions for forbidden claims, tie comparator baselines to formal target objects rather than calling them wrong, preserve materials as public-label queue utility, define CTC artifact-consequence denominators precisely, and submit from a clean tagged commit or clean release branch.

## Method Description

PARC is a release-time certification layer for frozen finite scientific AI candidate universes under one-sided partial verification. Given a fixed proposal backend, score, alpha/rho/K operating point, block definition, and verified-positive subset, PARC constructs block-calibrated e-values and uses a self-consistent selection rule to either release a certified subset or refuse the requested release. The method is not a generator and does not improve the upstream model; it governs which model-generated candidates can responsibly enter downstream artifacts.

The final review-approved evidence hierarchy uses two hard anchors. In materials, PARC is framed as public-label fixed-budget follow-up queue governance: it reduces unstable public-DFT follow-ups and supports certified stopping/refusal, while source-discordance diagnostics prevent overinterpretation as independent validation or prospective discovery. In CTC, PARC is framed as scientific-artifact protection: strict alpha release avoids false lineage edges under the declared official-GT/audit proxy and refuses corrupted rankings. Visual audits and source-discordance studies support boundary conditions rather than headline claims.
