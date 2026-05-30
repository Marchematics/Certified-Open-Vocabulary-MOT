# Phase67d Durability-Risk Headline Hardening

Status: `completed_headline_display_hardening`.

This milestone answers the review-facing Phase A hardening checklist for the
durability-risk centerpiece.

Completed:

- headline pruned model: `system_margin_distribution + system_size_activity`;
- chemical-system bootstrap confidence intervals;
- calibration table over cross-fitted GroupKFold predictions;
- train-fold base-rate baseline and memorization control;
- near-hull-density is kept as an Extended Data negative ablation, not the
  headline model.

Headline model:

- ROC-AUC: `0.809` (95% chemical-system bootstrap
  CI `0.722` to `0.874`);
- base flip rate: `0.227`;
- top-30% risk triage retained flip rate: `0.107`
  (95% CI `0.038` to `0.223`);
- top-30% high-risk rows capture `0.670`
  of observed flips.

Scope guardrails:

- not a release certificate;
- not DFT evidence;
- not prospective materials discovery;
- not a label-free deployment predictor because the strongest features depend
  on t0 public-label margin landscapes;
- do not present the near-hull-density ablation as the headline model.
