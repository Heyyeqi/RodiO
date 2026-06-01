# E1-A Cloud Mesh Foundation Acceptance

## Corresponding Code Commit

- `commit hash`: `e0b6e5d`
- `commit message`: `Add optional cloud mesh foundation`
- This commit only included `pwa/earth3d.js`.

## Implementation Summary

- Added optional cloudMesh foundation.
- Added cloud alphaMap loading logic.
- Added desktop / mobile texture selection logic.
- `cloudMaterial` uses `THREE.MeshBasicMaterial`.
- Cloud radius is `2.04`.
- Cloud `renderOrder` is `2`.
- Cloud is attached under `earthGroup`, so it follows the earth pose.
- Added `setCloudVisible(visible)`.
- Added cloud read-only state in `getDebugState()`.
- Cloud load failure does not trigger overall 3D fallback.
- No impact to `dayTexture`, `nightTexture`, city lights, `skyMesh`, fallback, or player.

## Browser Acceptance Result

- Page renders normally.
- `window.earth3d` is accessible.
- `getDebugState().cloud` is present and valid.
- `cloud.enabled: true`
- `cloud.visible: true`
- `cloud.loaded: true`
- `cloud.texturePath` resolves correctly.
- `cloud.radius: 2.04`
- `cloud.renderOrder: 2`
- `cloud.materialType: MeshBasicMaterial`
- `cloud.loadError: null`
- `setCloudVisible(false)` works.
- `setCloudVisible(true)` works.
- Theme switching works for:
  - `morning`
  - `noon`
  - `goldenApproach`
  - `sunset`
  - `lateEvening`
  - `deepNight`

## Opacity Acceptance Result

- `morning: 0.12`
- `noon: 0.14`
- `goldenApproach: 0.10`
- `sunset: 0.08`
- `lateEvening: 0.02`
- `deepNight: 0.01`

Opacity changes by theme are working as expected.
`lateEvening` and `deepNight` remain intentionally low.
No visual tuning beyond the foundation pass was performed.

## Verification

- `node -c pwa/earth3d.js`: passed
- `npm test`: passed

## Acceptance Conclusion

`E1-A Cloud Mesh Foundation Browser Acceptance: passed`

- cloudMesh loads successfully.
- cloudMesh is visible.
- cloudMesh can be disabled.
- cloudMesh can be restored.
- cloudMesh is observable through debug state.
- No blocking issues were found.
- The main earth rendering chain is not regressed.

## Remaining Risks

- Night city lights may still be partially affected by cloud coverage in some views.
- Extreme viewing angles may still show local transparency sorting artifacts.
- Mobile and desktop texture selection should still be checked on real devices.
- The refined cloud asset is still an E1 test-mount resource, not final art.
- E1-B must be a separate visual tuning pass and must not be merged into this acceptance record.

## Stage Boundary Conclusion

- E1-A is complete.
- E1-A may be closed out.
- Do not enter E1-B yet.
- E1-B must be a separate task.
- E1-B may only cover cloud visual tuning.
- E1-B must not mix in Sky P1B, dual LUT, terminator, PBR, player, service worker, or `index.html`.
