#!/bin/bash
# run_rdl_all.sh — 生成所有 RDL 区域的 Mapbox + GEBCO 合成贴图
# 用法：
#   bash scripts/geo/run_rdl_all.sh
#   RDL_RESOURCE_STACK=1 bash scripts/geo/run_rdl_all.sh
#   RDL_RESOURCE_LEVEL=16k RDL_RESOURCE_STACK=1 bash scripts/geo/run_rdl_all.sh
#   RDL_MAX_DIM=16384 RDL_ZOOM_BIAS=1 bash scripts/geo/run_rdl_all.sh
# 已完成的区域会因为缓存直接跳过，可以随时中断再续跑

set -e
cd "$(dirname "$0")/../.."

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
RDL_RESOURCE_STACK="${RDL_RESOURCE_STACK:-0}"
RDL_RESOURCE_LEVEL="${RDL_RESOURCE_LEVEL:-}"
RDL_MAX_DIM="${RDL_MAX_DIM:-}"
RDL_ZOOM_BIAS="${RDL_ZOOM_BIAS:-}"
RDL_EXTRA_ARGS="${RDL_EXTRA_ARGS:-}"

EXTRA_ARGS=()
if [ "$RDL_RESOURCE_STACK" = "1" ]; then
    EXTRA_ARGS+=(--resource-stack)
fi
if [ -n "$RDL_RESOURCE_LEVEL" ]; then
    EXTRA_ARGS+=(--resource-stack-level "$RDL_RESOURCE_LEVEL")
fi
if [ -n "$RDL_MAX_DIM" ]; then
    EXTRA_ARGS+=(--max-dim "$RDL_MAX_DIM")
fi
if [ -n "$RDL_ZOOM_BIAS" ]; then
    EXTRA_ARGS+=(--zoom-bias "$RDL_ZOOM_BIAS")
fi
if [ -n "$RDL_EXTRA_ARGS" ]; then
    read -r -a USER_EXTRA_ARGS <<< "$RDL_EXTRA_ARGS"
    EXTRA_ARGS+=("${USER_EXTRA_ARGS[@]}")
fi

REGIONS=(
    # 第一批（原始 8 个）
    hawaii maldives ryukyu philippines_central
    south_china_sea great_barrier_reef caribbean_bahamas indonesia_east
    # 第一批（东亚）
    japan korea_yellow_sea taiwan
    # 第一批（欧洲 / 大西洋）
    mediterranean_east mediterranean_west british_isles norway_fjords
    iceland azores canary_madeira
    # 第一批（中东 / 印度洋）
    black_sea caspian_sea red_sea persian_gulf
    sri_lanka andaman_sea seychelles madagascar
    # 第一批（非洲 / 南部）
    south_africa cape_verde
    # 第一批（太平洋 / 美洲）
    new_zealand alaska galapagos gulf_mexico_yucatan
    # 第二批（东亚补充）
    bohai_sea east_china_sea sea_of_japan taiwan_strait bashi_channel
    # 第二批（东南亚补充）
    singapore_malacca borneo indonesia_west gulf_of_thailand
    # 第二批（南亚补充）
    bay_of_bengal arabian_sea
    # 第二批（欧洲补充）
    baltic_sea adriatic_sea bay_of_biscay
    # 第二批（非洲补充）
    east_africa_coast mozambique_channel
    # 第二批（太平洋岛屿补充）
    guam_marianas palau papua_new_guinea fiji_vanuatu
    samoa french_polynesia christmas_island
    # 第二批（美洲补充）
    california_coast eastern_caribbean brazil_coast french_guiana
    patagonia falkland_islands
    # 第三批（亚太 / 中国近海岛屿）
    xisha_paracel nansha_spratly dongsha_pratas ogasawara
    micronesia marshall_islands solomon_islands new_caledonia
    tonga kiribati_gilbert
    # 第三批（美洲补充）
    puerto_rico_vi abc_venezuela easter_island rio_southeast_brazil
    peru_chile_coast rio_de_la_plata south_georgia bermuda
    central_america_pacific
    # 第三批（欧洲补充）
    faroe_islands svalbard
    # 第四批（补漏）
    hainan_island kuril_southern
)

TOTAL=${#REGIONS[@]}
SUCCESS=0
FAILED=()

echo "=== RDL Mapbox 全区域生成（共 $TOTAL 个）==="
echo "开始时间: $(date)"
echo "Python: $PYTHON_BIN"
echo "额外参数: ${EXTRA_ARGS[*]:-(none)}"
echo ""

for region in "${REGIONS[@]}"; do
    echo ">>> [$region] 开始"
    if "$PYTHON_BIN" scripts/geo/rdl_mapbox_poc.py --region "$region" "${EXTRA_ARGS[@]}"; then
        echo ">>> [$region] 完成"
        SUCCESS=$((SUCCESS + 1))
    else
        echo ">>> [$region] 失败，继续下一个"
        FAILED+=("$region")
    fi
    echo ""
done

echo "=== 全部完成: $(date) ==="
echo "成功: $SUCCESS / $TOTAL"
if [ ${#FAILED[@]} -gt 0 ]; then
    echo "失败: ${FAILED[*]}"
fi
