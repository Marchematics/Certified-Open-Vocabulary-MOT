# Phase63 PARC-A Preregistration

Objective: evaluate PARC as a certificate-directed active verification policy:
given a scarce one-sided audit budget, can targeted verification turn refusal
into certified release?

Frozen primary row:

- CTC learned-hybrid, strict alpha=0.10, K=100.
- Audit policy: top-score one-sided verification over calibration candidates.
- Budget: 0.5% of calibration candidates.
- Comparator: matched-budget random audit and full random-audit transition.

Primary pass rule:

- 20/20 nonempty safe seeds;
- zero observed false releases;
- matched-budget random audit remains empty;
- random audit requires at least 100x the targeted budget to transition.

Materials rows are included only as public-label boundary/secondary evidence.
No new DFT, no new human labels, and no prospective materials-discovery claim.
