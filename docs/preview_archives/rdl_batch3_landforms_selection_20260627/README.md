# RDL Batch 3 Landforms Selection Pass — 2026-06-27

Initial triage for `tile_noon_air_mapbox_m3m4_dem_landforms.jpg` across all 84 regions.

Heuristic:

- `manual review`: mean_abs_diff_rgb >= 2.4
- `candidate keep`: 0.12 <= mean_abs_diff_rgb < 2.4
- `candidate revert`: mean_abs_diff_rgb < 0.12, or known fallback with no valid landforms in bbox

- Candidate keep: 48
- Manual review: 15
- Candidate revert: 21

## Manual Review

- `south_africa` — mean_abs_diff_rgb=4.4089 (strong_delta_manual_review)
- `caspian_sea` — mean_abs_diff_rgb=4.3913 (strong_delta_manual_review)
- `red_sea` — mean_abs_diff_rgb=4.2226 (strong_delta_manual_review)
- `rio_de_la_plata` — mean_abs_diff_rgb=3.7321 (strong_delta_manual_review)
- `black_sea` — mean_abs_diff_rgb=3.5703 (strong_delta_manual_review)
- `baltic_sea` — mean_abs_diff_rgb=3.0877 (strong_delta_manual_review)
- `gulf_of_thailand` — mean_abs_diff_rgb=3.0792 (strong_delta_manual_review)
- `bohai_sea` — mean_abs_diff_rgb=2.8153 (strong_delta_manual_review)
- `mozambique_channel` — mean_abs_diff_rgb=2.7532 (strong_delta_manual_review)
- `east_africa_coast` — mean_abs_diff_rgb=2.6542 (strong_delta_manual_review)
- `persian_gulf` — mean_abs_diff_rgb=2.6406 (strong_delta_manual_review)
- `patagonia` — mean_abs_diff_rgb=2.6396 (strong_delta_manual_review)
- `mediterranean_east` — mean_abs_diff_rgb=2.5237 (strong_delta_manual_review)
- `peru_chile_coast` — mean_abs_diff_rgb=2.4857 (strong_delta_manual_review)
- `california_coast` — mean_abs_diff_rgb=2.4594 (strong_delta_manual_review)

## Candidate Keep

- `sea_of_japan` — mean_abs_diff_rgb=2.3557
- `great_barrier_reef` — mean_abs_diff_rgb=2.3221
- `mediterranean_west` — mean_abs_diff_rgb=2.2482
- `adriatic_sea` — mean_abs_diff_rgb=2.2374
- `french_guiana` — mean_abs_diff_rgb=2.1214
- `norway_fjords` — mean_abs_diff_rgb=2.0526
- `bay_of_biscay` — mean_abs_diff_rgb=2.0145
- `indonesia_west` — mean_abs_diff_rgb=1.9855
- `hainan_island` — mean_abs_diff_rgb=1.8393
- `sri_lanka` — mean_abs_diff_rgb=1.8279
- `taiwan_strait` — mean_abs_diff_rgb=1.8126
- `singapore_malacca` — mean_abs_diff_rgb=1.8092
- `madagascar` — mean_abs_diff_rgb=1.7747
- `borneo` — mean_abs_diff_rgb=1.7727
- `rio_southeast_brazil` — mean_abs_diff_rgb=1.6746
- `arabian_sea` — mean_abs_diff_rgb=1.6161
- `papua_new_guinea` — mean_abs_diff_rgb=1.5833
- `bay_of_bengal` — mean_abs_diff_rgb=1.5726
- `british_isles` — mean_abs_diff_rgb=1.3848
- `gulf_mexico_yucatan` — mean_abs_diff_rgb=1.3725
- `abc_venezuela` — mean_abs_diff_rgb=1.2976
- `alaska` — mean_abs_diff_rgb=1.2555
- `central_america_pacific` — mean_abs_diff_rgb=1.2257
- `indonesia_east` — mean_abs_diff_rgb=1.1745
- `philippines_central` — mean_abs_diff_rgb=1.1233
- `korea_yellow_sea` — mean_abs_diff_rgb=1.0735
- `japan` — mean_abs_diff_rgb=1.0546
- `brazil_coast` — mean_abs_diff_rgb=1.0207
- `east_china_sea` — mean_abs_diff_rgb=0.9335
- `caribbean_bahamas` — mean_abs_diff_rgb=0.8351
- `iceland` — mean_abs_diff_rgb=0.8218
- `taiwan` — mean_abs_diff_rgb=0.7984
- `andaman_sea` — mean_abs_diff_rgb=0.7808
- `kuril_southern` — mean_abs_diff_rgb=0.7385
- `new_zealand` — mean_abs_diff_rgb=0.6315
- `puerto_rico_vi` — mean_abs_diff_rgb=0.6189
- `falkland_islands` — mean_abs_diff_rgb=0.6094
- `nansha_spratly` — mean_abs_diff_rgb=0.5274
- `faroe_islands` — mean_abs_diff_rgb=0.4703
- `bashi_channel` — mean_abs_diff_rgb=0.4617
- `south_china_sea` — mean_abs_diff_rgb=0.3707
- `new_caledonia` — mean_abs_diff_rgb=0.3178
- `solomon_islands` — mean_abs_diff_rgb=0.2493
- `galapagos` — mean_abs_diff_rgb=0.2274
- `canary_madeira` — mean_abs_diff_rgb=0.1945
- `hawaii` — mean_abs_diff_rgb=0.1726
- `fiji_vanuatu` — mean_abs_diff_rgb=0.1386
- `eastern_caribbean` — mean_abs_diff_rgb=0.1222

## Candidate Revert

- `cape_verde` — mean_abs_diff_rgb=0.1071 (delta_too_light)
- `south_georgia` — mean_abs_diff_rgb=0.0722 (delta_too_light)
- `french_polynesia` — mean_abs_diff_rgb=0.0685 (delta_too_light)
- `samoa` — mean_abs_diff_rgb=0.0593 (delta_too_light)
- `azores` — mean_abs_diff_rgb=0.0540 (delta_too_light)
- `ryukyu` — mean_abs_diff_rgb=0.0516 (delta_too_light)
- `guam_marianas` — mean_abs_diff_rgb=0.0490 (delta_too_light)
- `christmas_island` — mean_abs_diff_rgb=0.0465 (delta_too_light)
- `palau` — mean_abs_diff_rgb=0.0359 (delta_too_light)
- `marshall_islands` — mean_abs_diff_rgb=0.0331 (delta_too_light)
- `tonga` — mean_abs_diff_rgb=0.0322 (delta_too_light)
- `maldives` — mean_abs_diff_rgb=0.0313 (delta_too_light)
- `easter_island` — mean_abs_diff_rgb=0.0254 (delta_too_light)
- `seychelles` — mean_abs_diff_rgb=0.0247 (delta_too_light)
- `kiribati_gilbert` — mean_abs_diff_rgb=0.0234 (delta_too_light)
- `ogasawara` — mean_abs_diff_rgb=0.0162 (delta_too_light)
- `micronesia` — mean_abs_diff_rgb=0.0144 (delta_too_light)
- `xisha_paracel` — mean_abs_diff_rgb=0.0087 (delta_too_light)
- `dongsha_pratas` — mean_abs_diff_rgb=0.0000 (fallback_no_landforms)
- `bermuda` — mean_abs_diff_rgb=0.0000 (fallback_no_landforms)
- `svalbard` — mean_abs_diff_rgb=0.0000 (fallback_no_landforms)