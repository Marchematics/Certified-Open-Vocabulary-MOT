# MatterGen--PARC A3-v4 Closeout

Status: protocol/environment gate plus MatterGen smoke-generation gate. No
public-label-free candidate universe, no consensus scoring, no PARC selection,
no DFT job manifest and no DFT outcomes are included.

## Completed gate

- MatterGen generated a 100-candidate smoke batch in the private generation
  workspace.
- `100` candidates were pymatgen-readable and recorded as public-safe
  metadata in `raw_mattergen_candidates.csv`.
- `0` generated CIF members failed parsing.
- Raw CIF/EXTXYZ files are not included in the public-safe bundle; only
  candidate metadata, private references and structure SHA-256 hashes are
  recorded.

## Interpretation

This is not a prospective positive result. It only shows that MatterGen
candidate generation can produce real structures in the local environment. The
A3-v4 trial advances beyond this gate only after public-label exclusion,
CHGNet/MACE consensus scoring, and a nonempty PARC release selection are frozen
before any DFT outcomes.
