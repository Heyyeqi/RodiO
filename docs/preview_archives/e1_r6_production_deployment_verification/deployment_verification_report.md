# E1-R6 Production Deployment Verification Report

**Date:** 2026-06-09 09:38
**URL:** https://web-production-a5193.up.railway.app  (no query params — default production load)
**Overall Verdict:** **PASS**

---

## Load Verification

| Check | Expected | Actual | Result |
|---|---|---|---|
| Page HTTP status | 200 | 200 | ✓ |
| Console variant log | `d5z_b` | `d5z_b` | ✓ |
| Texture path | `/assets/earth/production/…` | `https://web-production-a5193.up.railway.app/assets/earth/production/d5z_b_8192x4096.jpg` | ✓ |
| Texture HTTP status | 200 | 200 | ✓ |
| Texture dimensions | 8192×4096 | 8192×4096 | ✓ |
| earth3d.isReady | true | true | ✓ |
| TUNE IN overlay dismissed | true | true | ✓ |

## Screenshots

| Time | File | Size |
|---|---|---|
| noon | `production_default_noon.png` | 458 KB |
| afternoon | `production_default_afternoon.png` | 445 KB |

## Console Errors

- Failed to load resource: the server responded with a status of 404 ()

## Deployment Context

| Field | Value |
|---|---|
| Promoted commit | `56f66d4` feat(earth): promote d5z_b as default day texture |
| Main HEAD | `c080795` docs(earth): record E1 visual acceptance and D5z generator |
| DAY_TEXTURE_VARIANT | `d5z_b` |
| Production texture | `pwa/assets/earth/production/d5z_b_8192x4096.jpg` (7.6 MB) |
| E1-R5 verdict | Conditional Pass (RW, 2026-06-09) |