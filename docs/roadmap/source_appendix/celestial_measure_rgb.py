import os, json
import numpy as np
from PIL import Image

BASE = "pwa/assets/textures"

def measure_disk(path):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(float)
    H, W, _ = a.shape
    lum = a.mean(2)
    mx = lum.max()
    mask = lum > 0.06 * mx
    ys, xs = np.where(mask)
    if len(xs) < 50:
        return None
    cx, cy = xs.mean(), ys.mean()
    dx, dy = xs - cx, ys - cy
    r = np.sqrt(dx**2 + dy**2)
    rmax = r.max()
    frac = len(xs) / (H * W)
    if frac > 0.35:                      # 全圆盘图：取内盘避临边
        inner = r < 0.85 * rmax
    else:                               # 表面近景：取全部天体像素
        inner = np.ones(len(xs), dtype=bool)
    yi, xi = ys[inner], xs[inner]
    cols = a[yi, xi, :]                 # N x 3
    if cols.ndim == 1:
        cols = cols.reshape(1, 3)
    cl = cols.mean(1)                   # N 亮度
    lo, hi = np.percentile(cl, [2, 98])
    keep = (cl > lo) & (cl < hi)
    sel = cols[keep]
    if len(sel) < 20:
        return None
    mean = sel.mean(0)
    # 灰度风险判定：用全部天体像素(剔除暗亮2%)的通道差，避免暗边污染
    rg = float(np.abs(sel[:,0]-sel[:,1]).mean())
    rb = float(np.abs(sel[:,0]-sel[:,2]).mean())
    gray = bool(rg < 4 and rb < 4)
    return {
        "file": os.path.basename(path),
        "size": f"{W}x{H}",
        "body_frac": round(float(frac),3),
        "sample_pixels": int(keep.sum()),
        "rgb": [round(float(mean[0]),1), round(float(mean[1]),1), round(float(mean[2]),1)],
        "hex": "#%02X%02X%02X" % (int(mean[0]), int(mean[1]), int(mean[2])),
        "mean_abs_RG": round(rg,1),
        "mean_abs_RB": round(rb,1),
        "grayscale_risk": gray,
    }

def measure_ring(path, bands=24):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(float)
    H, W, _ = a.shape
    y0, y1 = int(H*0.35), int(H*0.65)
    strip = a[y0:y1]                     # band x W x 3
    perx = strip.mean(0)                 # W x 3  (每列径向均值)
    edges = np.linspace(0, W, bands+1).astype(int)
    prof = []
    for i in range(bands):
        s, e = edges[i], edges[i+1]
        seg = perx[s:e]                  # (w_seg, 3)
        seg_rgb = seg.mean(0)            # (3,)
        prof.append({
            "seg": i+1,
            "x_range": f"{s}-{e}",
            "rgb": [round(float(seg_rgb[0]),1), round(float(seg_rgb[1]),1), round(float(seg_rgb[2]),1)],
            "lum": round(float(seg_rgb.mean()),1),
        })
    overall = perx.mean(0)
    return {
        "file": os.path.basename(path),
        "size": f"{W}x{H}",
        "bands": bands,
        "overall_rgb": [round(float(overall[0]),1), round(float(overall[1]),1), round(float(overall[2]),1)],
        "profile": prof,
    }

results = {"planets": [], "rings": []}
for f in sorted(os.listdir(os.path.join(BASE,"planets"))):
    if f.lower().endswith((".jpg",".png")):
        r = measure_disk(os.path.join(BASE,"planets",f))
        if r: results["planets"].append(r)
for f in sorted(os.listdir(os.path.join(BASE,"saturn_rings"))):
    if f.lower().endswith((".jpg",".png")):
        r = measure_ring(os.path.join(BASE,"saturn_rings",f))
        if r: results["rings"].append(r)

print("========== 行星 / 卫星 disk 实测 RGB ==========")
print(f"{'file':30s} {'size':10s} {'frac':5s} {'RGB':16s} {'hex':9s} |RG| |RB| gray")
for r in results["planets"]:
    print(f"{r['file']:30s} {r['size']:10s} {r['body_frac']:<5} {str(r['rgb']):16s} {r['hex']:9s} {r['mean_abs_RG']:4.1f} {r['mean_abs_RB']:4.1f}  {'GRAY!' if r['grayscale_risk'] else ''}")

print("\n========== 土星环 径向分布 ==========")
for r in results["rings"]:
    print(f"{r['file']} {r['size']} overall={r['overall_rgb']}")
    for p in r["profile"]:
        bar = "#" * int(p["lum"]/4)
        print(f"  seg{p['seg']:>2} x={p['x_range']:>10} rgb={str(p['rgb']):16s} lum={p['lum']:6.1f} {bar}")

with open("/tmp/rodio_assets/measure_result.json","w") as f:
    json.dump(results, f, indent=2)
print("\n[json] -> /tmp/rodio_assets/measure_result.json")
