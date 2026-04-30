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

v1 只做三件事：

1. **Detection**  
   每帧检测：
   - `player`
   - `goalkeeper`
   - `referee`

2. **Tracking**  
   对场上人员进行跨帧关联，输出连续片段内稳定的 `track_id`。

3. **Export**  
   输出：
   - 标注视频：bbox + class + track_id
   - Parquet：每帧结构化 tracking 数据

### 2.2 v1 成功标准

v1 不追求整场比赛、长时间离屏后的绝对身份一致。  
v1 的目标是：

```text
在连续可见片段内稳定保持 track_id；
短时遮挡和相机 pan/tilt 后尽量恢复；
长时间离屏后不强制保持同一 ID。
```

### 2.3 v1 不做

以下内容全部放入 Future Work：

- ball detection / ball tracking
- 球场单应矩阵
- 鸟瞰图
- 真实世界坐标
- 速度、距离、热区
- 传球、射门、进球等事件检测
- 球队识别
- 跨场 ReID
- 实时直播处理

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

### 3.2 公开数据集策略

使用公开足球数据集增强 detection 泛化能力：

- SoccerNet
- Roboflow football/soccer datasets
- 其他公开视频标注数据

公开数据的用途：

- detection 预训练或联合训练
- 增加不同场地、光照、相机视角、球衣颜色样本
- 辅助验证检测模型泛化

公开数据不作为最终 tracking 验收依据。

### 3.3 Neylo 自有数据策略

Neylo Veo 数据用于：

- detection 微调
- tracking 调参
- 最终人工 QA
- v1 验收

原因：

- tracking 稳定性高度依赖真实部署视频的画质、压缩、Veo pan/tilt、遮挡方式和球衣相似度。

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
  -> export parquet + annotated mp4
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

v1 只检测：

- `player`
- `goalkeeper`
- `referee`

取消：

- `ball`

### 7.2 模型路线

baseline：

- YOLO11 模型直接跑通 pipeline。

训练路线：

1. 使用公开足球数据集训练或预训练。
2. 使用 Neylo Veo 数据微调。
3. 按视频划分 train/val/test，避免 frame-level leakage。
4. 主动学习：挑选低置信度、误检、漏检样本回标。

### 7.3 推理策略

优先级：

1. 普通 YOLO inference 跑通 end-to-end。
2. 再评估高分辨率推理。
3. 最后再加入 SAHI 处理远端小目标。

不要一开始就把 SAHI 和 TensorRT 作为 pipeline 必需项。

### 7.4 Detection 验收

初始目标：

- `player` mAP@0.5 > 0.90
- `goalkeeper/referee` 单独统计，但不阻塞早期 pipeline baseline
- 漏检和误检必须通过 annotated MP4 人工抽检记录

---

## 8. Tracking 模块

### 8.1 Tracking 对象

Detection 可以区分：

- `player`
- `goalkeeper`
- `referee`

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

建议先做 CLI：

```bash
neylo run --input data/raw/match_001/clip_001.mp4 --config configs/pipeline.yaml
```

批处理：

```bash
neylo run-batch --input-dir data/raw/match_001 --config configs/pipeline.yaml
```

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

### 10.2 MP4 可视化

annotated MP4 必须显示：

- bbox
- track_id
- class_name
- optional confidence

颜色策略：

- 同一个 track_id 使用稳定颜色。
- 不同类别可以使用不同边框样式或标签前缀。

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
- 输出 annotated MP4 + Parquet
- YOLO + tracking 跑通

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

### Phase 0：项目骨架

- 创建 `env/requirements.txt`
- 创建 `configs/pipeline.yaml`
- 创建 Pydantic schemas
- 创建 CLI skeleton

### Phase 1：最小闭环

- 输入单个视频
- YOLO inference
- BoT-SORT tracking
- 导出 Parquet
- 导出 annotated MP4

### Phase 2：数据与训练

- 抽帧
- 去重
- 伪标注
- CVAT 修正
- 公开数据 + Neylo 数据训练
- 模型评估

### Phase 3：tracking 稳定性

- CMC 调参
- ReID 调参
- debug visualization
- tracklet stitching prototype

### Phase 4：批处理与评估

- 多 clip batch
- 5-10 分钟连续片段
- tracking metrics
- QA report

### Phase 5：企业级扩展

- Prefect flow
- PostgreSQL run metadata
- MinIO/S3 storage adapter
- Docker GPU worker
- monitoring dashboard

---

## 13. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 当前 Neylo 数据偏高光 | 用公开数据增强 detection，向公司请求连续片段 |
| 公开数据不能代表 Veo tracking | tracking 验收以 Neylo Veo 视频为主 |
| goalkeeper/referee 类别不稳定 | tracking 内部统一 person_on_pitch，导出保留类别 |
| camera pan/tilt 导致 ID 漂移 | BoT-SORT 开启 CMC |
| 遮挡导致 track fragmentation | ReID + track_buffer + offline stitching |
| 一开始工程栈过重拖慢 CV 迭代 | 先 CLI/local filesystem，保留扩展边界 |
| 后期企业级迁移成本高 | 从第一天定义 schema/service/storage/stage 边界 |

---

## 14. 最终建议

v1 的成功不应该定义为“完整足球智能分析系统”。  
v1 应该定义为：

```text
给定一段 Neylo Veo 足球视频，
系统可以稳定检测场上人员，
在连续片段内给出可检查、可导出、可评估的 track_id，
并输出 Parquet + annotated MP4。
```

这条路线更容易完成，也更适合后续扩展到企业级 pipeline。

