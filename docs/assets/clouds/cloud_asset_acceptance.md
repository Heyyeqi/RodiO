# E1-0G Normalized Cloud Asset Acceptance

## Selection Conclusion

- E1 first-pass cloudMesh test mount should default to refined / R2:
  - `pwa/assets/earth/clouds/cloud_alpha_2048x1024_refined.png`
  - `pwa/assets/earth/clouds/cloud_alpha_4096x2048_refined.png`

## Reasons for Not Using the Original Images

- The original images are too gray and too full overall.
- The no-cloud areas are not black enough.
- Using them directly as `alphaMap` may produce a gray-white haze.

## Reasons for Not Preferring the Norm Version

- The norm version is a clear improvement.
- However, the cloud coverage is still too dense.
- The refined version is better suited for an E1 low-opacity test mount.

## Refined Version Advantages

- Mean value is lower.
- The proportion of near-black regions is higher.
- Bright pixels above 180 are reduced.
- Gray haze is reduced.
- The main cloud bands are still preserved.

## Remaining Risks for E1 Real-Scene Testing

- Visual appearance of abnormal black patches on the globe.
- Whether the cloud layer blocks night-city lights.
- Whether the southern hemisphere cloud bands are too heavy.
- Whether daytime opacity still needs to be lowered further.

## Suggested E1 Construction Parameter Bounds

- Desktop should prioritize `4096x2048` refined.
- Mobile should prioritize `2048x1024` refined.
- Daytime opacity should start around `0.10–0.16`.
- `goldenApproach` / `sunset` opacity should start around `0.08–0.12`.
- `lateEvening` / `deepNight` opacity should start around `0.00–0.03`.
- `setCloudVisible()` must be provided.
- `getDebugState()` must include cloud state.
- Must be reversible.
- Must not affect city lights, skyMesh, fallback, or player.

## Explicit Forbidden Actions

- Do not use the original images directly for cloudMesh.
- Do not use the norm version as the default unless the refined version fails in real-scene testing.
- Do not enter PBR.
- Do not enter terminator.
- Do not enter Sky P1B.
- Do not enter dual LUT.
- Do not modify `index.html`.
- Do not modify the player or the service worker.

