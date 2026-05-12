# OVTrack Baseline Status

Status: `converter_ready_requires_prediction_file`

We checked the public OVTrack, OVT-B-Dataset, and TETA repositories for
ready-to-use OVT-B prediction files. The repositories expose OVTrack/OVT-B
configs, model checkpoints, prompt files, and evaluation instructions, but no
packaged OVT-B prediction JSON/PKL was found in the cloned file trees.

Prepared interface:

```bash
python -m parc_track.cli phase7 ovtrack-convert \
  --pred PATH_TO_OVTRACK_JSON \
  --ann <PARC_ROOT>/data/OVT-B/ovtb_ann.json \
  --out-dir <PARC_ROOT>/outputs/phase7_ovtrack_ovtb

python -m parc_track.cli phase3 matrix \
  --config <PARC_ROOT>/configs/phase7_ovtrack_ovtb_matrix.yaml
```

Expected prediction format is TAO/TETA COCO-VID JSON:

```json
[
  {
    "image_id": 1,
    "video_id": 10,
    "track_id": 7,
    "category_id": 1,
    "bbox": [x, y, w, h],
    "score": 0.9
  }
]
```

Primary source status:

- SysCV/ovtrack: model/config instructions, no prediction file in repo.
- Coo1Sea/OVT-B-Dataset: OVT-B dataset plus OVTrack-derived configs, no
  prediction file in repo.
- siyuanliii/TETA: evaluation scripts and example prediction links for TAO-style
  evaluation, no OVTrack OVT-B prediction file in repo.

Paper usage: this baseline should be reported only after an actual OVTrack
prediction file is converted and run through the fixed `M=150`, `alpha in
{0.10,0.20}`, seed `{0,1,2}` matrix. Until then, the status is a prepared
adapter, not an experimental result.
