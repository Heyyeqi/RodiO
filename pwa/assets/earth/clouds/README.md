# Earth Clouds Assets

This directory is used for E1 Cloud Layer Foundation cloud alpha maps.

## Runtime assets

The current runtime assets used by E1-A cloudMesh are:

- `cloud_alpha_2048x1024_refined.png`
- `cloud_alpha_4096x2048_refined.png`

These are the only cloud alpha assets required by the current runtime code.

## Audit and processing files

The following files are kept for comparison, normalization, and refinement audit only:

- `cloud_alpha_2048x1024.png`
- `cloud_alpha_4096x2048.png`
- `cloud_alpha_2048x1024_norm.png`
- `cloud_alpha_4096x2048_norm.png`
- `cloud_alpha_2048x1024_candidate_a.png`
- `cloud_alpha_2048x1024_candidate_b.png`
- `cloud_alpha_normalization_preview.png`
- `cloud_alpha_refinement_preview.png`

These files are not required by runtime code unless explicitly promoted through a future resource audit.

## Requirements

1. Global equirectangular projection.
2. Aspect ratio must be 2:1.
3. Clouds should be white or light gray, and no-cloud areas should be black or near black.
4. No borders, watermarks, text, or terrain color contamination.
5. Sources and licenses must be recorded in `docs/assets/clouds/cloud_asset_sources.md`.
6. Do not enter E1 cloudMesh construction before source and license are confirmed.
7. Do not hard-code resource paths that have not passed audit.
