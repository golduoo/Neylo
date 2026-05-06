# Neylo CV 模块工程规划 v2：Detection + Tracking + Lightweight Pipeline

## 1. 项目背景

Neylo 是一个面向 **室外 11 人制足球（业余/青训级别）** 的体育数据分析项目。  
本计划覆盖 v1 阶段的 Computer Vision 子系统，目标是先稳定完成 **场上人员检测 + 连续片段内稳定跟踪 + 离线视频处理闭环**。

v2 相比原计划的主要变化：

- v1 取消 `ball` 检测与跟踪，降低早期交付风险。
- v1 tracking 目标从“整场比赛稳定 ID”调整为“连续可见片段内稳定 ID”。
- pipeline 先采用轻量 CLI + 本地文件系统，保留未来企业级扩展边界。
- detection 使用公开足球数据集训练/预训练，再用 Neylo Veo 数据微调。
- tracking 验收必须以 Neylo Veo 视频为主，公开数据只作辅助调参。

---

## 2. v1 核心目标

### 2.1 必须交付

v1 是一个面向用户的交互式视频复盘 web 应用，由四部分组成：

1. **CV 流水线（核心）**
   - Detection：单类 `player`（数据驱动决定，见 §3）
   - Tracking：连续可见片段内稳定的 `track_id`（BoT-SORT + ReID + CMC）
   - 每帧 + 每 track 的结构化数据落 Parquet + 索引

2. **Backend API（FastAPI）** — 见 `docs/requirements/api.md`
   - 上传视频、查询任务状态
   - 查询任意帧的检测结果
   - 查询某个 track_id 在整段视频中的轨迹

3. **Frontend Web UI**（Vite + React + TS + Tailwind + shadcn/ui）— 见 `docs/requirements/ui.md`
   - 上传视频
   - 拖动进度条到任一帧 → 显示该帧所有检测框
   - 点击某个框 → 选中该球员的 track
   - 播放视频时，被选中的 track 高亮跟随；其他检测框可一键隐藏

4. **CLI**（保留作为非 UI 入口）
   - `neylo run --input <video>` 执行同样的流水线，产出同样的 Parquet/索引，不依赖 UI

### 2.2 v1 成功标准

v1 不追求整场比赛、长时间离屏后的绝对身份一致。
v1 的目标是：

```text
在连续可见片段内稳定保持 track_id；
短时遮挡和相机 pan/tilt 后尽量恢复；
长时间离屏后不强制保持同一 ID；
UI 上能稳定完成"上传 → 选人 → 跟随播放"的完整闭环。
```

### 2.3 v1 不做

以下内容全部放入 Future Work：

- 多类检测（goalkeeper / referee / ball）
- 球场单应矩阵 / 鸟瞰图 / 真实世界坐标
- 速度、距离、热区
- 传球、射门、进球等事件检测
- 球队识别
- 跨场 ReID
- 直播 / 实时推流 / 边上传边推理（架构是"上传 → 离线预处理 → 前端渲染"）
- 多用户、登录、会话保存
- 移动端布局
- 模型训练（v1 用 COCO 预训练 + 后续单类微调，微调本身在 Phase 4）

---

## 3. 数据策略

### 3.1 当前数据

已有数据：

- 4 场 ANUFC vs 对手的 Veo 高光片段
- 每场约 20-30 个 clip
- 每个 clip 约 10-20 秒

限制：

- 多数是高光片段，偏禁区进攻场景。
- 中场、远景、多人密集移动、长时间连续 possession 数据不足。
- 这些数据足够做 baseline 与微调，但不足以单独证明“整场比赛 tracking 稳定”。

### 3.2 公开数据集策略（v1 锁定 Roboflow ball-player-gk-scoreboard-ref）

v1 训练数据来自一个已下载到本地的 Roboflow 数据集：

| 字段 | 取值 |
| --- | --- |
| Slug | `ball-player-gk-scoreboard-ref` |
| 来源 | Roboflow Universe（Xiwen 已本地下载） |
| 图片量 | ~11000 |
| 源类别 | `ball`, `player`, `goalkeeper`, `scoreboard`（4 类） |
| 格式 | YOLO（Roboflow 导出） |
| License | 允许商用（Xiwen 2026-05-07 确认） |
| 域分布 | Veo 风格 + 电视转播混合 |
| 本地路径 | `data/external/ball-player-gk-scoreboard-ref/` |

**v1 类别重映射**：训练时把源类映射到单类 `player`：

| 源类 | v1 处理 |
| --- | --- |
| `player` | → `player` |
| `goalkeeper` | → `player`（合并） |
| `ball` | 丢弃（v2 用专用小目标模型 + SAHI） |
| `scoreboard` | 丢弃（v1 不关心场外元素） |

混合域（Veo + 电视）有助泛化，但电视转播部分与 Veo 之间存在 sim-to-real gap。Phase 4 后期可能需要在 Veo clip 上做 200–500 帧的人工标注做 final fine-tune。

权威细节见 `docs/requirements/data.md`。

不再依赖 SoccerNet 或其他公开集（数据足够，避免多源混合复杂化）。

### 3.3 Neylo 自有数据策略

Neylo Veo 数据用于：

- detection 微调
- tracking 调参
- 最终人工 QA
- v1 验收

原因：

- tracking 稳定性高度依赖真实部署视频的画质、压缩、Veo pan/tilt、遮挡方式和球衣相似度。

### 3.5 单类 player 决策（v1）

v1 检测器只输出单类 `player`。

历史背景：早期评估的 Veo 标签分布 (player-white=41418, ball=2110, another-player=131, Keeper=33, referee=16) 严重不均衡，goalkeeper + referee 合计 49 条实例不足以训练区分能力。这个评估之后，训练数据源切换到 Roboflow `ball-player-gk-scoreboard-ref`（11k 图片，见 §3.2），但单类策略保持不变 — 其本身已经足够 v1 的"上传 → 选人 → 跟随"交互闭环。

对应代码：`neylo.schemas.ClassName` 已收敛到 `PLAYER` 单值；`build_class_map` 简化为只查 `player` 名字（COCO 预训练时回退到 `person → player`，微调权重直接按名字匹配）。

### 3.4 数据请求

建议向公司补充：

- 1-2 场完整比赛视频，或
- 5-10 分钟连续片段，覆盖中场、防守、边线、角球、禁区混战

这会显著提升 tracking 验收可信度。

---

## 4. 技术路线总览

```text
local video
  -> ingest
  -> segment/decode
  -> detect people
  -> track people
  -> optional offline stitching
  -> export parquet + track_index.json (annotated mp4 optional)
```

v1 使用轻量实现：

- CLI 入口
- 本地文件系统
- YAML 配置
- Pydantic schema
- Parquet 输出
- 可视化 MP4

未来企业级扩展：

- Prefect orchestration
- MinIO object storage
- PostgreSQL job metadata
- Prometheus/Grafana monitoring
- Dockerized GPU worker

---

## 5. 推荐目录结构

```text
neylo/
├── AGENTS.md
├── PLAN.md
├── PLAN_v2.md
├── configs/
│   ├── pipeline.yaml
│   └── botsort.yaml
├── data/
│   ├── raw/
│   ├── frames/
│   ├── annotations/
│   ├── datasets/
│   ├── models/
│   └── outputs/
├── docs/
│   ├── requirements/
│   └── decisions/
├── env/
│   ├── environment.yml
│   └── requirements.txt
├── neylo/
│   ├── cli.py
│   ├── schemas/
│   ├── pipeline/
│   │   ├── runner.py
│   │   ├── stages.py
│   │   └── prefect_flow.py      # future
│   ├── services/
│   │   ├── detection/
│   │   └── tracking/
│   ├── storage/
│   │   ├── local.py
│   │   └── s3.py                # future
│   ├── export/
│   └── evaluation/
├── docker/
└── tests/
```

核心原则：

- CLI 只是入口，不承载核心业务逻辑。
- detection、tracking、export 都作为 service 模块实现。
- storage 通过 adapter 抽象，v1 用 local，未来可换 MinIO/S3。
- pipeline stage 保持清晰边界，未来可以迁移到 Prefect。

---

## 6. 数据契约

所有阶段输入输出都用 Pydantic v2 定义。

### 6.1 DetectionRecord

```text
video_id
segment_id
frame_id
timestamp_ms
class_name
conf
x1
y1
x2
y2
detector_name
model_version
```

### 6.2 TrackRecord

```text
video_id
segment_id
frame_id
timestamp_ms
track_id
class_name
conf
x1
y1
x2
y2
tracker_name
source_track_id
stitched_track_id
```

说明：

- `source_track_id` 保存原始 tracker 输出。
- `stitched_track_id` 保存离线缝合后的 ID。
- 如果没有做 stitching，两者可以相同或 `stitched_track_id` 为空。

---

## 7. Detection 模块

### 7.1 类别

v1 检测器只输出单类：

- `player`

不在 v1 范围（推迟到 v2）：

- `ball`（独立小目标模型 + SAHI）
- `goalkeeper` / `referee` 等角色细分（数据驱动决策，详见 §3.5）

### 7.2 模型路线

baseline（Phase 1.3）：

- 直接用 COCO 预训练 `yolo11n.pt` 跑通 pipeline，不训练。

微调（Phase 4）：

1. 主训练源：Roboflow `ball-player-gk-scoreboard-ref`（11k 图，§3.2）
2. 训练前类别合并（player + goalkeeper → player；ball / scoreboard 丢弃）
3. 按 Roboflow 自带 train/valid/test 划分
4. 后期可选：在 Veo clip 上人工标注 200–500 帧做二次微调，缩小域差
5. 主动学习：挑选低置信度、漏检、误检样本回标

### 7.3 推理策略

优先级：

1. 普通 YOLO inference 跑通 end-to-end（Phase 1.3）
2. 微调后切换到 yolo11m / yolo11l + 高分辨率
3. SAHI 仅在 v2（ball 检测）启用

不要一开始就把 SAHI 和 TensorRT 作为 pipeline 必需项。

### 7.4 Detection 验收

初始目标：

- `player` mAP@0.5 > 0.90 在外部数据集 test split 上
- `player` mAP@0.5 > 0.85 在 Veo holdout 上（如果做了人工标注）
- 漏检和误检通过 web UI 或 CLI overlay 视频人工抽检记录

---

## 8. Tracking 模块

### 8.1 Tracking 对象

Detection 在 v1 只输出单类 `player`。

Tracking 主逻辑可以先统一视为：

```text
person_on_pitch
```

原因：

- 早期类别抖动不应该导致 track 断裂。
- 导出时仍保留每帧原始类别。

### 8.2 Primary Tracker

使用 BoT-SORT + ReID + CMC。

初始配置：

```yaml
tracker_type: botsort
with_reid: true
reid_model: osnet_x1_0_msmt17
proximity_thresh: 0.5
appearance_thresh: 0.25
gmc_method: sparseOptFlow
track_buffer: 60
match_thresh: 0.8
```

### 8.3 为什么 CMC 必须开启

Veo 会自动 pan/tilt。  
相机移动时，画面中所有 bbox 都会发生全局漂移。  
如果只用 IoU 匹配，tracker 很容易把同一个人误判为新 ID。

CMC 通过估计相邻帧的运动补偿，提升相机运动下的 ID 稳定性。

### 8.4 Offline Tracklet Stitching

v1 加分项，不阻塞 baseline。

基本流程：

1. 收集断裂 tracklets。
2. 计算每个 tracklet 的 ReID embedding 平均向量。
3. 仅在时间间隔小于 5 秒的候选之间匹配。
4. 用位置、速度和 appearance 相似度过滤。
5. 用匈牙利算法或图匹配生成 stitching mapping。
6. 保留 `source_track_id` 方便 debug。

### 8.5 Tracking 验收

在 Neylo Veo 视频上验证。

初始目标：

- 10-20 秒 clip：稳定输出可视化 ID
- 1-2 分钟连续片段：短时遮挡后尽量保持 ID
- 5 分钟样本：统计平均 track length、ID switches、fragmentation

建议目标：

```text
5 分钟样本中：
- frame coverage >= 99%
- 平均 player track length >= 60-120 秒
- ID switch 人工抽检可解释、可定位
```

不要把“整场比赛同一球员永远同 ID”作为 v1 阻塞目标。

---

## 9. Pipeline 模块

### 9.1 v1 入口

两个入口，共享同一个核心库：

**CLI（先做，作为非 UI 入口长期保留）：**

```bash
neylo run --input data/raw/match_001/clip_001.mp4 --config configs/pipeline.yaml
neylo run-batch --input-dir data/raw/match_001 --config configs/pipeline.yaml
```

**Backend API（FastAPI，详见 `docs/requirements/api.md`）：**

```bash
uvicorn neylo.api.main:app --reload
# POST /api/v1/jobs           上传视频 -> { job_id }
# GET  /api/v1/jobs/{job_id}   轮询任务状态与进度
# GET  /api/v1/jobs/{id}/frames/{frame_id}
# GET  /api/v1/jobs/{id}/tracks/{track_id}
```

CLI 和 API 都最终调用同一个 pipeline 函数；区别只在调用上下文（一次性 vs 异步任务）。

### 9.2 Stage 设计

```text
ingest
segment
detect
track
export
evaluate
```

每个 stage：

- 输入输出明确
- 可单独运行
- 可重复运行
- 输出写入稳定目录
- 保存 config hash 和 model version

### 9.3 Idempotency

每个 stage 输出以以下字段标识：

```text
video_id
segment_id
stage_name
config_hash
model_version
```

失败重跑不能污染成功结果。

### 9.4 本地优先，企业级可迁移

v1 使用：

- local filesystem
- YAML
- Parquet
- JSON summary

未来替换：

- local storage -> MinIO/S3
- local run metadata -> PostgreSQL
- CLI runner -> Prefect flow
- log summary -> Prometheus/Grafana

只要现在保持 schema 和 service 边界清晰，未来企业级化工作量可控。

---

## 10. Export 模块

### 10.1 Parquet 输出

每个 processed video 或 segment 输出 Parquet。

必须包含：

```text
video_id
segment_id
frame_id
timestamp_ms
track_id
class_name
conf
x1
y1
x2
y2
source_track_id
stitched_track_id
```

### 10.2 MP4 可视化（可选）

v1 主交付是 web UI（前端实时渲染原视频 + overlay），不依赖标注 MP4。
annotated MP4 仅作为 CLI 的可选导出（`--export-video` flag），用于：

- 在没有 UI 的环境下快速人工抽检
- 写报告 / 给非技术 stakeholder 看

如果导出，必须显示：

- bbox
- track_id
- optional confidence

颜色策略：同一个 track_id 使用稳定颜色（v1 单类，不需要按类区分）。

---

## 11. Evaluation 模块

### 11.1 Detection 指标

统计：

- mAP@0.5
- recall
- false positives per minute
- missed players per sampled frame

### 11.2 Tracking 指标

统计：

- average track length
- ID switches
- fragmentation count
- IDF1/MOTA where GT exists

### 11.3 Pipeline 指标

统计：

- total runtime
- per-stage runtime
- processed FPS
- failed segments
- output completeness

### 11.4 验收层级

Milestone 1：Local Baseline

- 输入 10-20 秒 clip
- 输出 `detections.parquet` + `tracks.parquet` + `track_index.json`
- YOLO + tracking 跑通
- annotated MP4 仅在 CLI 加 flag 时导出（可选）

Milestone 2：Robust Clip Pipeline

- 输入多个高光 clips
- batch 处理
- schema/config/export 稳定
- 人工抽检 tracking ID

Milestone 3：Long Segment Tracking

- 输入 5-10 分钟连续视频
- 开启 CMC + ReID
- 尝试 offline tracklet stitching
- 输出 tracking metrics 和 QA report

---

## 12. 推荐实现顺序

> 当前实施进度的"实时状态"在 `docs/progress.md`，下面是计划侧的权威清单。

### Phase 0：项目骨架

- 创建 `env/requirements.txt`
- 创建 `configs/pipeline.yaml`
- 创建 Pydantic schemas
- 创建 CLI skeleton

### Phase 1：CLI 最小闭环（核心 CV 流水线）

- 输入单个视频
- YOLO inference（v1 单类 player）
- BoT-SORT tracking
- 导出 Parquet（detections + tracks）
- 导出 track_index.json，供后续 API 查询使用
- annotated MP4 改为可选导出（CLI 通过 flag 启用，UI 直接渲染原视频 + overlay，不依赖标注 MP4）

### Phase 2：Backend API（FastAPI）

- `neylo/api/` 下建立 FastAPI app
- 端点：`POST /api/v1/jobs`、`GET /api/v1/jobs/{id}`、`GET /api/v1/jobs/{id}/frames/{frame_id}`、`GET /api/v1/jobs/{id}/tracks/{track_id}`、`GET /api/v1/jobs/{id}/video`
- 单进程 background task：上传后异步跑 Phase 1 流水线，写入 `outputs/<job_id>/`
- 模型在 startup 时加载并复用
- 见 `docs/requirements/api.md`

### Phase 3：Frontend Web UI（Vite + React + TS + Tailwind + shadcn/ui）

- `web/` 独立子目录，独立 `package.json`
- 状态机：idle → uploading → processing → ready
- 关键交互：scrub → 拉取该帧检测；点击 bbox → 选中 track；play → overlay 跟随当前帧
- 使用 `requestVideoFrameCallback` 做帧级同步
- 见 `docs/requirements/ui.md`

### Phase 4：数据与训练

- 抽帧
- 去重
- 伪标注
- CVAT 修正
- 单类 player 微调（公开数据 + Neylo 数据）
- 模型评估
- 微调权重替换 `configs/pipeline.yaml` 中 `detection.model_path`，`build_class_map` 自动识别

### Phase 5：Tracking 稳定性

- CMC 调参
- ReID 调参
- debug visualization
- tracklet stitching prototype

### Phase 6：批处理与评估

- 多 clip batch
- 5-10 分钟连续片段
- tracking metrics
- QA report

### Phase 7：企业级扩展

- Prefect flow
- PostgreSQL run metadata
- MinIO/S3 storage adapter
- Docker GPU worker
- WebSocket 进度推送替代轮询
- 多用户 / 鉴权 / 鉴权后端
- monitoring dashboard

---

## 13. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 当前 Neylo 数据未标注且偏高光 | 用 Roboflow 11k 数据集训练 detection（§3.2），向公司请求连续片段 |
| 公开数据与 Veo 域差 | 训练集已混合 Veo + 电视转播；后期可在 Veo 上人工标 200–500 帧二次微调 |
| 单类 player 限制信息粒度 | 已接受为 v1 决策（§3.5）；UI 通过点选满足"跟人"需求，不依赖角色分类 |
| camera pan/tilt 导致 ID 漂移 | BoT-SORT 开启 CMC |
| 遮挡导致 track fragmentation | ReID + track_buffer + offline stitching |
| 一开始工程栈过重拖慢 CV 迭代 | 先 CLI/local filesystem，保留扩展边界 |
| 后期企业级迁移成本高 | 从第一天定义 schema/service/storage/stage 边界 |

---

## 14. 最终建议

v1 的成功不应该定义为"完整足球智能分析系统"。
v1 应该定义为：

```text
给定一段 Neylo Veo 足球视频，
用户可以在浏览器里上传、播放、点击任意一个球员，
看到该球员的检测框跟随播放，
其他球员的检测框可隐藏；
系统在后台稳定输出 Parquet + track_index 供查询。
CLI 作为非 UI 入口产出同样的工件。
```

这条路线最直接对应用户感知到的"产品价值"，也最容易后续扩展到企业级 pipeline 和多用户系统。

