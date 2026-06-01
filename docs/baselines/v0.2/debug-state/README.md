# E0.2 Debug State Export

This directory is reserved for manual `window.earth3d.getDebugState()` exports.

Export these six themes from a browser session:

```js
window.earth3d.setTimeOfDay('morning')
JSON.stringify(window.earth3d.getDebugState(), null, 2)
```

Repeat for:

- `morning`
- `noon`
- `afternoon`
- `goldenApproach`
- `lateEvening`
- `deepNight`

Save the JSON output as:

- `morning_78cca42_debugState.json`
- `noon_78cca42_debugState.json`
- `afternoon_78cca42_debugState.json`
- `goldenApproach_78cca42_debugState.json`
- `lateEvening_78cca42_debugState.json`
- `deepNight_78cca42_debugState.json`

Do not fabricate JSON. If a browser export is not available, leave this directory as a manual step for later capture.
