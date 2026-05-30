# AI-Assisted Human Review Instructions

Human labels must be entered independently from the AI suggestion.

Allowed human labels:

- `same_cell_supported`: the two adjacent-frame boxes plausibly identify the
  same cell/link and may be used as one-sided positive support.
- `unsupported`: the link is visibly implausible or points to a different cell.
- `uncertain`: the image evidence is insufficient, ambiguous, or needs
  adjudication.

Only `same_cell_supported` can become one-sided support.  `unsupported` and
`uncertain` labels are never trusted negatives for PARC calibration.
