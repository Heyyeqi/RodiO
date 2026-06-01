# E1-A Cloud Mesh Foundation Phase Closure

## Phase Objective

E1-A's goal was to add an optional cloudMesh foundation so that RodiO has a basic cloud-layer capability, without doing final visual tuning.

E1-A only solved:

- cloudMesh can load
- cloudMesh can display
- cloudMesh can be disabled
- cloudMesh can be restored
- cloudMesh can be observed
- cloudMesh does not regress the main system

E1-A did not solve:

- final cloud art quality
- opacity fine tuning
- night-side blocking optimization
- transparent sorting fine tuning
- real weather cloud maps
- terminator
- PBR
- Sky P1B
- dual LUT

## Completed Commit Chain

1. `e0b6e5d Add optional cloud mesh foundation`
   - committed `pwa/earth3d.js`
   - added optional cloudMesh foundation
   - added `setCloudVisible()`
   - added `cloud` fields to `getDebugState()`

2. `c2f4e58 Add E1-A cloud mesh acceptance record`
   - committed `cloud_mesh_foundation_acceptance.md`
   - froze browser acceptance results

3. `bf6e8ac Add refined cloud alpha runtime assets`
   - committed refined 2K / 4K runtime assets
   - ensured fresh clone / deployment environments can load the cloud alphaMap

4. `47aae3e Add cloud asset audit documentation`
   - committed source, processing, HTTP check, visual check, and implementation-plan documents

## Current Runtime Cloud Assets

The only runtime cloud assets currently required are:

- `pwa/assets/earth/clouds/cloud_alpha_2048x1024_refined.png`
- `pwa/assets/earth/clouds/cloud_alpha_4096x2048_refined.png`

Notes:

- 2K refined is intended for mobile / small viewport / low DPR usage.
- 4K refined is intended for desktop usage.
- Refined assets are E1 trial assets, not final art.
- Original, norm, candidate, and preview files are not runtime dependencies.

## Untracked Files Handling

The following untracked file is a collaboration discipline file and may be handled separately later:

- `docs/codex_handoff_protocol.md`

The following untracked files under `pwa/assets/earth/clouds/` are historical / candidate / processing / preview materials and are not runtime dependencies:

- original images
- norm images
- candidate images
- preview images

## Browser Acceptance Conclusion

`E1-A Browser Acceptance passed.`

Confirmed:

- page renders normally
- `window.earth3d` is accessible
- `getDebugState().cloud` is valid
- `cloud.enabled: true`
- `cloud.visible: true`
- `cloud.loaded: true`
- `cloud.loadError: null`
- `setCloudVisible(false)` works
- `setCloudVisible(true)` works
- theme switching works for:
  - `morning`
  - `noon`
  - `goldenApproach`
  - `sunset`
  - `lateEvening`
  - `deepNight`
- opacity switches by theme correctly
- no blocking issues were found

## Remaining Risks

- Night city lights still need screenshot review to verify they are not partially blocked.
- Extreme viewing angles still need regression review for local transparency artifacts.
- Mobile and desktop resource selection still need real-device verification.
- The refined cloud asset may still be somewhat dense.
- E1-B must use a separate screenshot-driven tuning pass.

## Stage Boundary Conclusion

- E1-A is complete.
- E1-A can be considered closed.
- Do not enter E1-B yet.
- E1-B must be a separate task.
- E1-B may only cover cloud visual tuning.
- E1-B must not mix in Sky P1B, dual LUT, terminator, PBR, player, service worker, or `index.html`.
