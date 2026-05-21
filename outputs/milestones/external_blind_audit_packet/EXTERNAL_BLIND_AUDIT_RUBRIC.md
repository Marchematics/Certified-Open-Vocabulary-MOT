# External Blind Audit Rubric

Status: frozen audit packet, not completed audit evidence.

Auditors receive only blinded item ids, dataset/task context, asset references, and the audit question. They do not receive PARC/raw arm, score, rank, existing human labels, official labels, or DFT/benchmark truth.

Allowed labels:

- iWildCam animal-present boxes: `animal`, `not_animal`, `uncertain`.
- SpaceNet7 temporal links: `same_building`, `not_same_building`, `uncertain`.

Conservative adjudication policy: disagreements and uncertain labels are counted as false/unsupported for conservative FTR unless adjudicated otherwise with a recorded reason.

Raw media are not redistributed in this public-safe repository. External auditors require a restricted dataset asset resolver keyed by `asset_ref`.
