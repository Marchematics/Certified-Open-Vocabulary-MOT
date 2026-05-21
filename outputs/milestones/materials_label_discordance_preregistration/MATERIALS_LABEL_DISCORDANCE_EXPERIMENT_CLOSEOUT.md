# Materials Label Discordance Experiment Closeout

This artifact executes the first clean experiment after the preregistration.
It uses the existing alex-mp exact-structure diagnostic as a minimal probe.

## Step 1

- Source pair: WBM/Matbench labels versus alex-mp v20 local public snapshot.
- Primary denominator: exact-structure matches only.
- Matched structures: `270`.
- Binary exact-stability discordance: `0.522`.
- Status: passes the preregistered `>=0.40` launch-signal threshold for this
  minimal existing probe.

This is not yet the final MP-vs-alex full-snapshot result. It is a go signal
to freeze broader source snapshots and run the same exact-match probe there.

## Step 2

The preregistered primary frontier-model endpoint requires ALIGNN-FF, CHGNet
and MACE-MP scores on the same matched denominator. If
`table_frontier_model_scores.csv` is present, CHGNet and MACE-MP were generated
from public weights on the exact-match structures and the endpoint is evaluated
under the frozen stable-class F1 rule. These locally generated scores are
raw-energy utility scores, so the artifact remains a go/no-go experiment rather
than a completed paper claim until the full MP-vs-alex source snapshots are
frozen.

The primary frontier-model ranking endpoint is now executable because
CHGNet/MACE-MP raw-energy scores were generated on the same 270-structure
denominator. The primary stable-class F1 ranking did not materially flip
between WBM and alex-mp labels, so the preregistered primary downstream
conclusion-flip gate is not met. Discovery-count consequences are reported as
supporting diagnostics only.
