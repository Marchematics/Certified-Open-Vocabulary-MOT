# NMI Reframing Notes

**Abstract opening.** Open-world perception systems increasingly make release-time decisions from incomplete annotations: which detections, tracks, or mask paths should be trusted, sent to humans, or admitted into downstream datasets? PARC provides an auditable certification layer for these release decisions.

**Intro framing.** Tracking is the main instantiation because it exposes path conflicts, temporal dependence, and partial labels, but the broader problem is release-time certification for open-vocabulary visual AI under incomplete supervision.

**Deployment scenario.** A monitoring or dataset-curation system may prefer a certified subset plus explicit refusals over an uncalibrated top-M dump. PARC's value is the risk knob and the refusal diagnostic, not SOTA HOTA maximization.

**TAO framing.** Use TAO alpha=0.10 as a hard partial-annotation stress/refusal setting and TAO alpha=0.20 as a positive sensitivity result.
