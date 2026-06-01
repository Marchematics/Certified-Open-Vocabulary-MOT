# Phase91 Protocol: CTC Strong-Model Surrogate Annotation

Model id: `phase91_ctc_image_template_segmentation_surrogate_v1`.

Inputs:

- Phase84 blinded packet templates;
- local CTC raw training frames under the configured data root;
- CTC `*_ERR_SEG` masks where available.

Forbidden inputs:

- intended arm;
- PARC status;
- score/rank;
- prior human labels;
- official GT labels.

Algorithm:

1. Resolve source and target adjacent frames.
2. Extract local bbox-context crops.
3. Compute crop normalized correlation.
4. Match the source crop template in the target-frame neighborhood.
5. Combine image-template, geometry, bbox-area, frame-gap and segmentation
   center evidence into a deterministic support score.
6. Emit `same_cell_supported`, `unsupported` or `uncertain`.

The output can replace manual labels operationally for dry runs, but it is not
external human evidence.
