# Cloud Asset Sources

| 文件名 | 目标路径 | 来源名称 | 来源 URL | License / 授权 | 获取日期 | 原始尺寸 | 处理方式 | 是否通过审计 | 备注 |
|---|---|---|---|---|---|---|---|---|---|
| cloud_alpha_2048x1024.png | `pwa/assets/earth/clouds/cloud_alpha_2048x1024.png` | NASA 原始云层 / 地球观测图像素材 + CC0 处理生成版本 | `https://raw.githubusercontent.com/matteason/live-cloud-maps/main/cloud_alpha_2048x1024.png` | NASA 原始媒体内容通常不受美国版权保护 / public domain；处理生成资源按 CC0 1.0 发布 | 2026-06-01 | 2048x1024 | 生成 / 转换为 8-bit gray+alpha PNG；输出 2048x1024 alphaMap；用于 Three.js cloud alphaMap；不包含地表颜色 | 格式：通过；HTTP 200：待人工确认；视觉质量：待人工确认 | 8-bit gray+alpha，适合 alphaMap |
| cloud_alpha_4096x2048.png | `pwa/assets/earth/clouds/cloud_alpha_4096x2048.png` | NASA 原始云层 / 地球观测图像素材 + CC0 处理生成版本 | `https://raw.githubusercontent.com/matteason/live-cloud-maps/main/cloud_alpha_4096x2048.png` | NASA 原始媒体内容通常不受美国版权保护 / public domain；处理生成资源按 CC0 1.0 发布 | 2026-06-01 | 4096x2048 | 生成 / 转换为 8-bit gray+alpha PNG；输出 4096x2048 alphaMap；用于 Three.js cloud alphaMap；不包含地表颜色 | 格式：通过；HTTP 200：待人工确认；视觉质量：待人工确认 | 8-bit gray+alpha，适合 alphaMap |

## 授权依据说明

- NASA 媒体使用政策说明 NASA 图像、音频、视频及纹理类媒体内容通常不受美国版权保护，可用于网页、计算机图形模拟等用途。
- NASA 标志、徽章、logo 等不在本资源使用范围内。
- CC0 1.0 表示权利人已在法律允许范围内放弃版权及相邻权，允许复制、修改、分发和商业使用，无需请求许可。
- 本项目仍保留来源记录，以便后续审计和追溯。

## 待验收项

1. 具体来源 URL 如仍未补齐，则需后续补齐。
2. HTTP 200 验证仍需人工完成。
3. 视觉质量确认仍需人工完成。
4. 未完成上述确认前，不得进入 E1 cloudMesh 施工。
