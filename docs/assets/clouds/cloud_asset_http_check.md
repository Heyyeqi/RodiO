# Cloud Asset HTTP Check

Manual verification is required before E1 cloudMesh construction.

## Start local server

```bash
cd ~/Projects/RodiO/pwa
python3 -m http.server 8080
```

## Open these URLs

- `http://localhost:8080/assets/earth/clouds/cloud_alpha_2048x1024.png`
- `http://localhost:8080/assets/earth/clouds/cloud_alpha_4096x2048.png`

## Confirm manually

- Returns HTTP 200
- Image renders normally in the browser
- Not a 404
- Not a broken or empty file
- Cloud gray-scale mask is visible

