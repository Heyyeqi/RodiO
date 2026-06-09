# RodiO Day Earth — Target Color Spec and Benchmark Matrix

> Visual direction: **Noon Air Earth / 正午空气蓝地球**
> Status: Approved design spec — awaiting Phase A source feasibility before any implementation
> Baseline: `d5z_b` (current production, 8K stable)
> This document does not authorize implementation. No textures, no scripts, no data downloads.

---

## 0. Relationship to Phase Plan

Two documents govern the next phase. They are not interchangeable:

| Document | Role |
|---|---|
| `global_color_grading_bmng_rdl_phase_plan.md` | Phase roadmap — goals, phase boundaries, risks, pipeline direction |
| **This document** | Visual color spec — what the target earth must look, feel, and test like |

This document is the aesthetic authority. The phase plan is the execution authority. When they conflict on aesthetic questions, this document wins. When they conflict on execution order or gating, the phase plan wins.

---

## 1. Visual Direction: Noon Air Earth / 正午空气蓝地球

The target aesthetic is a single defined visual language:

```
Noon Air Earth / 正午空气蓝地球
```

**One-line description:** A high-altitude noon-light earth — cool-toned, transparent, restrained, with layered ocean depth, warm desert, blue-white ice, low-saturation land, and a whisper of atmospheric haze.

**Composite target feel:**

```
冷调正午蓝 + 清透深海 + 克制浅海青蓝 + 低饱和陆地 + 暖沙色沙漠 + 蓝白冰原 + 轻薄大气
```

**Seven core principles (must all hold simultaneously):**

```
深海要清澈，不要黑。
浅海要发光，但不要荧光。
陆地要低饱和，不要地图绿。
沙漠要暖，但不要过曝。
冰原要蓝白有纹理，不要死白。
群岛要有浅海光晕，不要只剩小点。
大气要轻薄，不要灰雾糊图。
```

**Prohibited directions:**

```
禁止 NASA 黑蓝高对比风格。
禁止 Google Earth 原始卫星硬对比风格。
禁止游戏地图式高饱和绿蓝。
禁止复古地图黄褐色。
禁止全图灰化、脏化、暗化。
禁止牺牲真实地理识别度来追求统一色调。
```

This is not a scientific reference earth, not a GIS product, not a wallpaper. It is the presence behind an AI radio experience — *Dawn FM*, *Rituals*, high-production broadcast globe.

---

## 2. Current Baseline and Transition

- `d5z_b` is the current production Day Texture (`DAY_TEXTURE_VARIANT = 'd5z_b'`).
- It solved E1's stability problems: polar blowout, deep-ocean GIS banding, desert overexposure.
- It is not the final RodiO Earth. It is the floor, not the destination.
- **Noon Air Earth is the next destination.** But it cannot replace `d5z_b` directly.
- Any new candidate must follow the full pipeline: generate → candidates/ → region preview → Three.js on-globe acceptance → human verdict → authorized promotion only.
- Any candidate that regresses below `d5z_b` on any of the E1 guardrail dimensions (see Section 10) is a blocker.

---

## 3. Color Value Usage Rules

**All HEX values in this document are tonal reference targets, not pixel replacement values.**

- Do not replace all pixels in a region with a single HEX color.
- Do not use region fill, bucket fill, or LUT that maps one color to another uniformly.
- Implement through: HSL adjustment, curve adjustment, color approximation, local blend, gradient mapping, mask-weighted blending, soft light / screen overlay.
- All original texture must be preserved: coastlines, terrain, seafloor, glacier, desert texture, river networks, mountain ridges.
- Where a color table lists a "main color," it means the median tonal target for that zone — not the only permissible color.
- Transitions between zones must be feathered. Hard edges are failure modes.

---

## 4. Global Color Principles

### 4.1 Global Base Parameters

These are final-stage tuning parameters, not first-pass global filters. Apply after regional work is complete.

```
全图亮度：      +3% 至 +6%
全图对比度：    -3% 至 -6%
全图饱和度：    -4% 至 -8%
蓝色通道亮度：  +4% 至 +8%
绿色饱和度：    -8% 至 -15%
黄色饱和度：    -5% 至 -12%
```

Purpose:
1. Reduce the hard contrast of traditional satellite imagery.
2. Prevent oversaturation of green land and desert yellow.
3. Maintain ocean transparency.
4. Shift toward low-orbit noon light, away from flat cartographic style.

### 4.2 Atmospheric Blue Overlay

Final unifying pass only. Must be extremely restrained.

```
叠加颜色：  #8FC4E6
混合模式：  soft light 或 screen
透明度：    4% 至 8%
最大限制：  不得超过 10%
```

Prohibited outcomes from this pass:
- Land turning grey.
- Desert turning muddy.
- Polar regions losing texture.
- A thick blue fog over the entire image.

---

## 5. Ocean System

Ocean is the primary visual foundation of RodiO Earth. It must form a continuous hierarchy:

```
深海海沟 → 深海主体 → 中深海 → 大陆架 → 近岸浅海 → 礁盘
```

No zone may directly cut to another. All transitions require gradients.

### 5.1 Deep Ocean

Applicable zones: Pacific deep basin, Atlantic deep basin, Indian Ocean deep, Southern Ocean deep, abyssal zones far from continental shelves.

Target: Clear deep blue with depth — not near-black, not grey-blue.

| Type | HEX | Use |
|---|---:|---|
| 最深海沟 | `#03243F` | Trenches, abyssal floor shadow |
| 深海主体 | `#05395F` | Large-area deep ocean base color |
| 中深海 | `#07527A` | Deep-to-mid-ocean transition |
| 受光远海 | `#126B92` | Lit ocean surface, high-altitude distant view |
| 远景雾化海面 | `#3E8DB0` | Atmospheric haze zone near horizon |

Rules:
1. Deepest zones may approach `#03243F` but must not go below that luminance.
2. Large deep-ocean area should stay between `#05395F` and `#07527A`.
3. No pure black, ink-blue, or grey-blue.
4. Seafloor texture may be preserved, but seafloor trenches must not become black cracks.

### 5.2 Continental Shelf / Mid-shallow Ocean

Applicable zones: Yellow Sea, East China Sea, northern South China Sea, Persian Gulf, Red Sea, Mediterranean coastal, outer Caribbean, Australian shelf, North Sea, Baltic.

Target: Brighter than deep ocean, cyan-blue transition, readable shelf.

| Type | HEX | Use |
|---|---:|---|
| 大陆架深蓝 | `#0A5F84` | Deep-to-shelf transition |
| 大陆架主色 | `#197FA0` | Shelf main body |
| 浅水过渡 | `#2FAAC0` | Nearshore shallow |
| 明亮浅水 | `#53C8D1` | Shallow water highlight (limited area only) |

Rules:
1. Shelf edge must have gradient — no hard cut from deep ocean to shallow.
2. Nearshore should transition from `#197FA0` to `#2FAAC0`.
3. Shallow highlights (`#53C8D1`) are local only — not spread across entire sea zones.
4. Yellow Sea and Bohai may be slightly grey, but must not look turbid or yellow-brown.
5. Mediterranean, Aegean, Caribbean may be more transparent.

---

## 6. Islands and Reefs

Islands must not be treated as land-only objects. Every island group needs a full structure:

```
岛屿核心 + 沙滩边缘 + 浅海环 + 礁盘高光 + 外海过渡
```

### 6.1 Tropical Islands — Universal Spec

Applicable zones: Maldives, Seychelles, Bahamas, Lesser Antilles, Fiji, Tonga, Samoa, French Polynesia, Cook Islands, Micronesia, Palau, Solomon Islands, Vanuatu, eastern Indonesia, southern Philippines.

Target: Small islands surrounded by a clear but restrained cyan-blue shallow halo, identifiable at earth-globe scale.

| Layer | HEX | Use |
|---|---:|---|
| 岛屿陆地核心 | `#4D7A56` to `#6E8F63` | Small island vegetation |
| 火山岛暗绿 | `#355F43` | Hawaii, Tahiti, high volcanic islands |
| 沙滩边缘 | `#D8C99D` | Narrow shoreline strip |
| 极浅水 | `#A9EFEA` | Shallowest water highlight |
| 礁盘青蓝 | `#5FD3D8` | Reef flat, coral shelf |
| 浅海主色 | `#2FAAC0` | Island perimeter shallow sea |
| 外海过渡 | `#197FA0` | Shallow-to-deep transition |
| 深海外缘 | `#07527A` | Surrounding deep ocean |

Rules:
1. Each tropical island should retain 1–4 pixels of cyan-blue shallow halo (scale to texture resolution).
2. Shallow halo must not be pure white or fluorescent cyan.
3. Reef highlight `#A9EFEA` max 15% of the island's surrounding shallow zone.
4. Island land must not be too dark — low-saturation green or grey-green.
5. Island edge must not be directly swallowed by deep ocean blue.
6. Dense archipelagos should show fragmented, layered cyan detail — not a single solid bright-blue mass.

### 6.2 Bahamas / Caribbean Shallows

Bahamas is the benchmark for shallow-water expression. Must avoid cheap fluorescent feel.

| Type | HEX |
|---|---:|
| 浅滩主体 | `#6ED9DE` |
| 极浅沙洲水色 | `#B7EFE8` |
| 浅海过渡 | `#36B8C8` |
| 外缘海 | `#13789A` |
| 深海 | `#06395F` |

Rules:
1. Bahamas shallows may be brighter than other regions.
2. Maximum brightness must not exceed `#B7EFE8`.
3. Shallow edge must be feathered — no hard color block.
4. Deep-shallow boundary must reflect seafloor slope gradient.
5. The full Caribbean must not be flattened to a single shade of light blue.

### 6.3 Maldives / Atolls

Target: Atolls as tiny cyan-blue jewels scattered in deep ocean — not glowing lightbulbs.

| Type | HEX |
|---|---:|
| 环礁外圈 | `#5FD3D8` |
| 环礁内湖 | `#8AE6E4` |
| 极浅高光 | `#B5F0EC` |
| 外海 | `#05395F` |

Rules:
1. Atolls: small area brightening only.
2. Deep ocean around each atoll must remain deep blue for contrast.
3. The entire Maldives zone must not become a patch of light blue.
4. Highlight points must be fine-grained, natural, distributed along real atoll geometry.
5. Atoll highlights should preserve ring structure — not become circular bright blobs.

### 6.4 Pacific High Islands

Applicable: Hawaii, Fiji, Samoa, Tonga, Tahiti, Marquesas, Solomon Islands, Vanuatu.

| Type | HEX |
|---|---:|
| 火山岛陆地 | `#355F43` |
| 山地阴影 | `#2F4B3F` |
| 低地绿 | `#5F8558` |
| 近岸浅海 | `#39B8C8` |
| 外海 | `#05436B` |

Rules:
1. Volcanic island land should be dark green — not bright green.
2. Narrow shallow ring at island edge.
3. Hawaii perimeter shallow should not be over-brightened — preserve surrounding deep-ocean feel.
4. French Polynesia and Fiji may have more visible cyan-blue reef.
5. High islands must retain mountain shadow — must not be processed into flat green dots.

### 6.5 High-Latitude Islands

Applicable: Canadian Arctic Archipelago, Svalbard, Franz Josef Land, Greenland peripheral islands, South Georgia, South Shetland Islands.

| Type | HEX |
|---|---:|
| 冰雪岛屿 | `#DDECF2` |
| 冰川阴影 | `#9CB8C8` |
| 裸岩边缘 | `#6E6A5D` |
| 冷海浅水 | `#63AFC8` |
| 极地海 | `#0A4D72` |

Rules:
1. High-latitude islands must not use tropical cyan-blue.
2. Shallow water should be cool blue or grey-blue — not fluorescent cyan.
3. Ice-covered islands must have blue-grey shadow — no pure white.
4. Bare rock edges may retain grey-brown for realism.
5. High-latitude island edges must transition through cold-sea water before hitting deep ocean.

---

## 7. Polar Regions

Polar zones must be independently controlled. Antarctica, Greenland, and Arctic sea ice are three distinct tonal systems.

### 7.1 Antarctica

Target: Vast, clean, blue-white, textured — not glaring, not dead-white.

| Type | HEX |
|---|---:|
| 冰盖暗部 | `#9CB8C8` |
| 冰盖中间调 | `#C9DEE8` |
| 冰雪主色 | `#DDECF2` |
| 冰雪亮部 | `#F2F8FA` |
| 冰裂缝阴影 | `#7FA6BA` |
| 近岸冰海 | `#63AFC8` |

Rules:
1. Antarctica main body must not use pure white `#FFFFFF`.
2. Large-area main tone should stay near `#DDECF2`.
3. Highlights `#F2F8FA` are for lit zones and ice ridge peaks only.
4. Ice texture must be preserved — brightness increase must not flatten it.
5. Crevasses, ridges, and glacier flow lines use `#9CB8C8` to `#7FA6BA` blue-grey shadow.
6. Antarctica edge meeting ocean must have a cold-blue transition — no white directly abutting deep sea.

### 7.2 Greenland

Greenland must be more topographically expressive than Antarctica.

| Type | HEX |
|---|---:|
| 冰盖中心 | `#E2EFF3` |
| 冰盖阴影 | `#A8C4D2` |
| 冰川流线 | `#8FAFC0` |
| 山地裸岩 | `#5E5C50` |
| 峡湾冷海 | `#4FA6C2` |
| 近岸浅冰海 | `#86D0D8` |

Rules:
1. Central ice cap may be brighter but must not be dead-white.
2. East and west coastal mountains must retain grey-brown bare rock and shadow.
3. Fjord zones must have cold cyan-blue water — not uniform deep blue.
4. Ice cap edge must graduate: blue-white → bare rock → sea water.
5. Greenland must not be processed as a single white patch.

### 7.3 Arctic Sea Ice and High-Latitude Ocean

Applicable: Arctic Ocean, Canadian Arctic Archipelago perimeter, Greenland Sea, Barents Sea, Southern Ocean pack ice.

| Type | HEX |
|---|---:|
| 极地海主色 | `#0A4D72` |
| 冰海过渡 | `#2F83A1` |
| 薄冰蓝 | `#A8DCE4` |
| 海冰白 | `#E6F2F5` |
| 冰缝阴影 | `#6A9DB4` |

Rules:
1. Sea ice must be thinner and more fragmented in appearance than land ice.
2. Pack ice must not be large-area pure white.
3. Ice leads must retain blue-grey lines.
4. Sea ice must have transparency against the water — not white paint.

---

## 8. Land Vegetation

### 8.1 Temperate Forest and Plains

Applicable: Central Europe, eastern China, Japan, Korean Peninsula, eastern USA, southern Canada, western Russia.

| Type | HEX |
|---|---:|
| 深森林 | `#244A3A` |
| 普通森林 | `#426D4D` |
| 平原绿 | `#6E8F63` |
| 浅绿农田 | `#8FA77A` |
| 城市灰绿混合 | `#7C8376` |

Rules:
1. Overall land green saturation lowered.
2. No bright green, no fluorescent green.
3. Farmland and plains may be slightly brighter but must trend grey-green.
4. Urban clusters must not become obvious grey-white patches — blend naturally with surrounding terrain.
5. Japan, Europe, eastern China may be marginally greener but must not exceed `#8FA77A` in brightness.

### 8.2 Tropical Rainforest

Applicable: Amazon, Congo Basin, Southeast Asia, Papua New Guinea, Borneo.

| Type | HEX |
|---|---:|
| 雨林暗部 | `#1F3F32` |
| 雨林主色 | `#2F5A3E` |
| 湿润绿 | `#4F7651` |
| 雾化绿 | `#6F8C68` |

Rules:
1. Rainforest must be darker and denser than temperate forest.
2. No bright green — target deep olive-green.
3. Amazon must not be a flat uniform green — river network texture must be preserved.
4. Southeast Asian island rainforest may be slightly brighter but must retain terrain shadow.

### 8.3 Grassland and Savanna

Applicable: East Africa, South American Pampas, Mongolian steppe, parts of Central Asia, northern Australia.

| Type | HEX |
|---|---:|
| 干草黄绿 | `#9A966B` |
| 草原主色 | `#8A8F61` |
| 稀树草原 | `#A3916E` |
| 湿润草地 | `#7D8F61` |

Rules:
1. Grassland should sit between green and sand.
2. Must not trend toward desert yellow.
3. East Africa may be warmer; Central Asian steppe may be greyer.

---

## 9. Desert and Dryland

### 9.1 Sahara and Arabian Peninsula

Target: Warm sand — detailed, not glaring.

| Type | HEX |
|---|---:|
| 沙漠阴影 | `#8D6D4F` |
| 沙漠主色 | `#C49B6F` |
| 受光沙地 | `#D8BC91` |
| 沙丘高光 | `#E6D0A8` |
| 岩石暗部 | `#6F5A45` |

Rules:
1. Sahara and Arabia must not broadly exceed `#D8BC91`.
2. `#E6D0A8` is for dune crest highlights and localized bright zones only.
3. Mountains, dry riverbeds, rocky zones must retain shadow from `#8D6D4F` to `#6F5A45`.
4. Egypt and the Arabian Peninsula are the highest overexposure risk — highlights must be suppressed.
5. Desert must not trend yellow-green or white.

### 9.2 Central Asia / Iranian Plateau / Tibetan Plateau Edge

| Type | HEX |
|---|---:|
| 高原灰褐 | `#A3916E` |
| 干旱土色 | `#9B8062` |
| 山地阴影 | `#5F5A4E` |
| 盐湖浅色 | `#D7D2BF` |
| 雪线 | `#D8E0DE` |

Rules:
1. Plateau must not be golden-yellow like desert.
2. Should trend grey-brown, earth-tone, rock-color.
3. Tibetan Plateau must retain cold feeling — must not be over-warmed.
4. Salt lakes and dry lake beds may be light but not pure white.

### 9.3 Australian Outback

| Type | HEX |
|---|---:|
| 红褐土 | `#A96F4F` |
| 干旱橙褐 | `#B9825A` |
| 浅土色 | `#C9A276` |
| 灌木灰绿 | `#8A8A65` |

Rules:
1. Australian interior may be redder than Sahara.
2. Must not become a uniform orange block.
3. Eastern coast must retain green; interior gradually transitions to red-brown.

---

## 10. Mountains and Plateaus

### 10.1 Himalayas and Tibetan Plateau

| Type | HEX |
|---|---:|
| 高原冷土色 | `#A3916E` |
| 山体灰褐 | `#7A6E5A` |
| 阴影灰 | `#4C4F45` |
| 雪线蓝白 | `#D8E0DE` |
| 高山雪亮部 | `#F0F5F4` |

Rules:
1. Himalayas must have a defined snowline.
2. Tibetan Plateau must not trend yellow — should be cool grey-brown.
3. Mountain shadow must not be crushed to black.
4. Snowline must not be a uniform white coating — must follow real ridge distribution.

### 10.2 Alps / Rockies / Andes

| Type | HEX |
|---|---:|
| 山地森林 | `#355F43` |
| 岩石灰褐 | `#746B5B` |
| 高山阴影 | `#4B5149` |
| 雪峰 | `#E4ECEC` |
| 雪峰高光 | `#F4F8F8` |

Rules:
1. Mountain ranges must preserve three-dimensional relief.
2. Snow peaks should appear only at high elevation.
3. Andes western face may trend dry-brown; eastern face may transition to green.

---

## 11. Special Sea Regions

### 11.1 Mediterranean

Target: Deep blue and transparent — some nearshore cyan, but must not look tropical.

| Type | HEX |
|---|---:|
| 地中海深水 | `#06446B` |
| 地中海主色 | `#0A638A` |
| 爱琴海浅水 | `#35AFC3` |
| 近岸高光 | `#7AD9DD` |

Rules:
1. Aegean island perimeters may have visible shallow water.
2. Mediterranean main body must be deeper than the Caribbean.
3. North African nearshore must not be over-brightened.

### 11.2 Red Sea

| Type | HEX |
|---|---:|
| 红海深水 | `#064B72` |
| 红海主色 | `#0B7192` |
| 珊瑚礁浅水 | `#4FCBD0` |
| 近岸礁盘 | `#95E7E2` |

Rules:
1. Warm desert flanks the Red Sea — water must create a cool-warm contrast.
2. Reef zones may be brighter but must hug the coastline.
3. Do not shallow-out the entire Red Sea.

### 11.3 Yellow Sea / Bohai / East China Sea

| Type | HEX |
|---|---:|
| 渤海浅水 | `#5E9FB0` |
| 黄海主色 | `#3A8EA5` |
| 东海过渡 | `#197FA0` |
| 外海深蓝 | `#07527A` |

Rules:
1. Yellow Sea and Bohai may carry slight grey-blue to suggest sediment — must not turn yellow-brown.
2. East China Sea must be bluer and more transparent than Yellow Sea.
3. Sea of Japan must be distinctly deeper, approaching `#05395F` to `#07527A`.
4. Taiwan Strait and northern South China Sea should show shallow cyan-blue transition.

### 11.4 Caribbean Sea

| Type | HEX |
|---|---:|
| 加勒比深水 | `#06466F` |
| 加勒比主色 | `#0E789B` |
| 浅海 | `#36B8C8` |
| 礁盘 | `#6ED9DE` |
| 极浅水 | `#B7EFE8` |

Rules:
1. Caribbean is permitted to be more transparent and bright than other regions.
2. Cuba, Bahamas, Yucatan perimeter should show visible shallow-water zones.
3. Deep trench zones must preserve deep-blue contrast.

---

## 12. Global Benchmark Matrix

All twelve regions below are active benchmarks. Each must pass acceptance before phase promotion. Japan is one of twelve — it is the method-validation region from prior RDL work, not the primary target.

| Region | Key Challenge | Primary Color Spec Sections |
|---|---|---|
| **Japan / East China Sea** | Coastline precision, shallow-sea clarity, land-ocean contrast, Sea of Japan depth | §5.2 (shelf), §11.3 (Yellow/East Sea), §8.1 (temperate land) |
| **Mediterranean** | Deep-blue with shallow transition, Aegean islands, North Africa coast | §11.1, §6 (islands) |
| **Caribbean / Bahamas** | Coral-reef transparency, atoll hierarchy, island legibility, deep trench contrast | §6.2, §6.1, §11.4 |
| **Red Sea / Arabian Peninsula** | Desert-ocean contrast, warm-cool boundary, nearshore reef | §11.2, §9.1 |
| **Indian Ocean (central)** | Deep-ocean calm, no GIS banding, expanse character | §5.1 |
| **Pacific Islands (Polynesia)** | Isolated atoll legibility, deep-Pacific depth, turquoise reef contrast | §6.3, §6.4, §5.1 |
| **Sahara / Egypt / Arabia** | Desert luminosity, highlight control, dune texture, Nile delta contrast | §9.1 |
| **Greenland / Arctic** | Polar brightness, fjord structure, bare rock, ice-margin transition | §7.2, §7.3, §6.5 |
| **Antarctica** | Polar blowout control, texture preservation, cold-white tone, ocean transition | §7.1 |
| **Southeast Asia / Indonesia** | Dense archipelago, shallow reef, tropical atmosphere, turbid river mouths | §6.1, §8.2, §5.2 |
| **Europe / Middle East wide** | Multi-zone harmony, land-sea balance, global tone anchor | §8.1, §9.2, §11.1 |
| **South Pacific (Tahiti, Fiji, Tonga)** | Deep-blue contrast, island jewel effect, high-island terrain | §6.4, §5.1 |

### Per-region acceptance crops

For each benchmark region the following crops are required at visual acceptance (Phase F):
- Standard globe player view at closest visible angle.
- 4 time modes: morning / noon / afternoon / sunset.
- Before-and-after comparison against `d5z_b` baseline.

---

## 13. Execution Pipeline (Future — Not Yet Authorized)

The following is the intended pipeline order when implementation is authorized. Recording it here does not authorize execution.

**Do not execute any of these steps until Phase A source selection is closed and each subsequent phase is explicitly authorized.**

```
Step 1: Asset audit
  Confirm input source: BMNG variant selected, GEBCO/GSHHG/DEM evaluated.
  Input: Phase A output document.

Step 2: Generate global preview
  Run Python color grading script with Noon Air Earth parameters.
  Output: full 8K candidate to pwa/assets/earth/candidates/

Step 3: Key-region before/after crops
  12 benchmark regions × standard player angle.
  Do not commit output yet.

Step 4: Human review
  Evaluate against this spec section by section.
  Issue verdicts per region. Conditional pass allows max 2 Partial (ocean or polar only).

Step 5: Three.js on-globe local acceptance
  Load candidate via DAY_TEXTURE_VARIANT override.
  Screenshot all 12 regions × 4 time modes.
  Verify UI readability against player overlay.

Step 6: Authorization decision
  If full pass or conditional pass: proceed to production promotion.
  If fail: identify specific failure modes, determine correction scope.

Step 7: Production promotion (only after authorization)
  Copy to pwa/assets/earth/production/
  Update DAY_TEXTURE_VARIANT
  Commit, push, deploy.
```

**Region priority order for grading passes:**

```
第一优先级：海洋整体色阶
第二优先级：浅海、群岛、礁盘
第三优先级：冰原与极地
第四优先级：沙漠与高原
第五优先级：森林与平原
第六优先级：全局空气蓝和最终统一
```

**Execution sequence within a grading run:**

```
1. 先锁定深海色阶
2. 再单独增强浅海与群岛
3. 再修正冰原，避免过曝
4. 再压低沙漠高光
5. 再降低陆地绿色饱和度
6. 最后加极轻空气蓝统一画面
```

**What not to do:**
```
不要一开始就全局调色。
不要一次性用单一 LUT 覆盖所有区域。
不要通过整体增加饱和度来增强浅海。
不要通过整体提高亮度来处理冰原。
```

---

## 14. Failure Modes Catalogue

These are the defined failure states. Any candidate with any of these must not be promoted.

**Ocean failure modes:**
- Deep ocean approaching black: `#000000` to `#021830` range — hard fail.
- Shallow ocean fluorescent or cyber-blue — hard fail.
- Archipelago perimeter painted as large solid bright-blue mass — hard fail.
- Deep and shallow ocean hard-cut without gradient — hard fail.
- Turbid seas (Yellow Sea, Bohai, Bengal Bay, Amazon delta) over-treated as tropical clear water — hard fail.

**Polar failure modes:**
- Antarctica or Greenland as pure dead-white — hard fail.
- Polar texture, crevasses, or glacier flow lines erased by brightness lift — hard fail.
- Greenland processed as a single white patch — hard fail.
- High-latitude islands using tropical cyan-blue — hard fail.

**Desert failure modes:**
- Sahara or Arabia as a large pale-yellow or white-yellow mass — hard fail.
- Desert overexposure (widespread zones above `#E6D0A8`) — hard fail.

**Land failure modes:**
- Any region (China eastern coast, Japan, Europe) showing map-app-style saturated green — hard fail.
- Tropical rainforest (Amazon, Congo, Southeast Asia) in bright fresh green — hard fail.
- Urban zones appearing as obvious grey-white blobs — hard fail.

**Global failure modes:**
- Thick blue filter over the entire image — hard fail.
- Any regional treatment that destroys real geographic identifiability — hard fail.
- Hard color-block seams at regional correction boundaries — hard fail.
- Global color harmony broken by patch accumulation — hard fail.
- UI (player text, controls, album art) no longer readable against earth background — hard fail.

---

## 15. d5z_b Baseline Floor (E1 Guardrail, Inherited)

Any BMNG / RDL / Global Color Grading candidate must meet or exceed `d5z_b` across all six dimensions. Regression on any dimension is a blocker — not a Partial:

1. **Default load stability:** HTTP 200, correct variant confirmed, 8192×4096 resolved.
2. **UI readability:** Player text, controls, and album art remain legible against any globe region at standard player view.
3. **Standard player view overall impression (lon=10, lat=20, all time modes):** must not be worse than `d5z_b`.
4. **Global coverage completeness:** No missing regions, no rendering voids.
5. **Multi time-mode stability (morning / noon / afternoon / sunset):** No blowout, no grey-flatten, no color shift.
6. **No regression in E1 protected regions:** Japan, Mediterranean, Caribbean, Pacific Islands passed E1 clean — any detectable regression is a hard fail.

---

## 16. Verification Checklist

Before any candidate is considered for promotion, verify all items:

```
[ ] 深海是否仍然清澈蓝色，而不是黑蓝。
[ ] 浅海是否有青蓝层次，而不是荧光色块。
[ ] 热带群岛是否能在地球视角下被识别。
[ ] 马尔代夫、巴哈马、斐济是否有细碎礁盘高光。
[ ] 高纬群岛是否使用冷蓝灰，而不是热带青蓝。
[ ] 南极是否保留冰盖纹理，避免死白。
[ ] 格陵兰是否保留峡湾、裸岩和冰川流线。
[ ] 撒哈拉、阿拉伯半岛是否压住过曝。
[ ] 青藏高原是否偏冷灰褐，而不是沙漠黄。
[ ] 中国东部、日本、欧洲是否避免鲜绿。
[ ] 亚马逊、刚果、东南亚是否偏深橄榄绿。
[ ] 黄海、渤海是否略灰蓝但不发黄。
[ ] 日本海、南海、加勒比、地中海是否有区域差异。
[ ] 最终全图是否清透、明亮、统一，但不失真实地理识别度。
[ ] 全部 12 个 benchmark 区域的 before/after 对比已完成。
[ ] 全部 4 个 time modes 在标准播放器视角下稳定。
[ ] UI 可读性通过标准播放器视角验证。
[ ] d5z_b 6 项 baseline 指标均未回退。
```
