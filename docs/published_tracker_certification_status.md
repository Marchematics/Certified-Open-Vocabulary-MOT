# Published OVMOT Tracker Certification Status

Phase-8 adds a post-hoc certification interface for published OVMOT tracker
outputs.  The interface is deliberately prediction-file first: official tracker
models may be run in their own environments, but PARC only consumes derived
TAO/TETA-style prediction rows and never silently substitutes another generator.

## Supported Tracker Families

| Tracker | Repository | Status |
| --- | --- | --- |
| OVTrack | `https://github.com/SysCV/ovtrack` | local repo present; no ready prediction JSON/PKL found |
| OVT-B baseline | `https://github.com/Coo1Sea/OVT-B-Dataset` | local repo present; no ready prediction JSON/PKL found |
| OVTR | `https://github.com/jinyanglii/OVTR` | local repo present; no ready prediction JSON/PKL found |

## Canonical Prediction Format

The converter accepts `.json`, `.pkl`, or `.pickle` only when the contents can
be interpreted as COCO-VID / TAO / TETA rows with at least:

```text
image_id, video_id, track_id, category_id, bbox, score
```

Unsupported PKL/MMTracking objects fail loudly with
`unsupported_prediction_format`.

## Commands

Create manifests and matrix configs:

```bash
python -m parc_track.cli phase8 published-trackers scaffold \
  --output-dir /home/waas/paper_experiments/outputs/phase8_published_trackers
```

Inspect local repos / public prediction availability:

```bash
python -m parc_track.cli phase8 published-trackers inspect \
  --output-dir /home/waas/paper_experiments/outputs/phase8_published_trackers
```

Convert one official prediction file:

```bash
python -m parc_track.cli phase8 published-trackers convert \
  --tracker ovtrack \
  --dataset ovtb \
  --pred PATH_TO_OFFICIAL_PREDICTIONS \
  --out-dir /home/waas/paper_experiments/outputs/phase8_published_trackers/ovtrack/ovtb
```

Run PARC wrapping after conversion:

```bash
python -m parc_track.cli phase8 published-trackers matrix \
  --config /home/waas/paper_experiments/configs/phase8_published_ovtrack_ovtb_matrix.yaml
```

Export released unsupported paths for audit:

```bash
python -m parc_track.cli phase8 published-trackers export-release-audit \
  --config /home/waas/paper_experiments/configs/phase8_published_ovtrack_ovtb_matrix.yaml \
  --unsupported-only
```

Aggregate completed tracker rows:

```bash
python -m parc_track.cli phase8 published-trackers report \
  --output-dir /home/waas/paper_experiments/outputs/phase8_published_trackers
```

## Current Empirical Status

The scaffold, converter, M-effective-aware wrapper matrix, release-audit export,
and report aggregator are implemented and tested.  No paper-facing tracker
result is claimed until official prediction files or official model runs produce
derived prediction JSON/PKL files.
