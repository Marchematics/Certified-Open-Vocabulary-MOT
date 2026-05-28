# Phase64 PARC-R Versioned Recertification

Status: `completed_versioned_recertification_refusal_boundary`.

PARC-R tests whether a materials release certificate should be inherited after
the reference hull moves from t0 to current-MP t1.  In the available
queue-limited t1 universe, recertification using t1 positives in calibration
blocks returns certified refusal for K=300 and K=500 under both scarce 10%
support and full calibration-block support.

Interpretation:

- This is not a positive current-MP alpha release result.
- It is a versioned refusal result: the old t0 release has current-MP FTR above
  alpha, and rerunning the release rule under t1 support refuses rather than
  inheriting the unsafe release.
- The result supports versioned release-card infrastructure: certificates are
  bound to their label version and should be renewed after database updates.

Headline positive PARC-R allowed: `false`.

Allowed claim: current-MP recertification detects insufficient t1 evidence mass
and returns refusal for the K=300/500 materials queues.

Forbidden claims:

- no prospective materials discovery;
- no DFT evidence;
- no t1 alpha certificate for the old t0 release;
- no claim that PARC-R creates a nonempty current-MP materials release.
