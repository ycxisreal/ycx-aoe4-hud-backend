# 项目结构说明

本文件用于描述当前后端工程的目录与职责分工。后续如有新增模块或结构调整，需要同步更新。

## 目录结构

```
aoe4-hud/
  main.py
  requirements.txt
  core/
    __init__.py
    config.py
    state.py
  ws/
    __init__.py
    protocol.py
    server.py
  capture/
    __init__.py
    dxcam_provider.py
    mss_provider.py
    manager.py
  recog/
    __init__.py
    ocr.py
    pipeline.py
    smoothing.py
    validation.py
  analysis/
    __init__.py
    engine.py
    rules.py
  tts/
    __init__.py
    speaker.py
  utils/
    __init__.py
    logging.py
    debug_dump.py
    dpi.py
  tools/
    rule_verify.py
  doc/
    后端初步项目文档.md
    后端接口文档.md
    日志输出位置.md
    打包发布说明.md
```

## 模块说明

### `main.py`

后端入口与应用编排，包含：
- 初始化日志与组件（配置、模板、流水线、规则引擎、TTS）
- 启动 WebSocket 服务端
- 处理前端消息（CONFIG_SET/START/STOP/PING）
- 识别主循环：抓屏 → 识别 → 稳定化 → 校验 → 推送数据/提醒

### `requirements.txt`

依赖清单，包含：
- 图像处理与矩阵计算（`opencv-python`、`numpy`）
- 屏幕捕获（`dxcam`、`mss`）
- 通信（`websockets`）
- 配置模型（`pydantic`）
- 语音播放（`edge-tts`）
- 打包工具（`pyinstaller`）

### `core/`

核心配置与运行状态，包含：
- `config.py`：前端下发配置的数据模型与消息解析
- `state.py`：后端运行状态与上下文（运行标记、质量状态等）

### `ws/`

WebSocket 通信模块，包含：
- `protocol.py`：统一消息结构封装（`BACKEND_STATUS`、`DATA`、`ALERT_EVENT`、`PONG`）
- `server.py`：WebSocket 服务端（连接管理、消息收发、广播）

### `capture/`

屏幕捕获封装，包含：
- `dxcam_provider.py`：dxcam 捕获实现
- `mss_provider.py`：mss 捕获实现（降级）
- `manager.py`：捕获管理器（优先 dxcam，失败降级 mss）

### `recog/`

识别流水线核心模块，包含：
- `ocr.py`：Tesseract OCR 识别
- `pipeline.py`：流水线组合（裁剪 → OCR → 解析）
- `smoothing.py`：多帧稳定化（投票）
- `validation.py`：合法性校验与质量检测

### `analysis/`

规则引擎模块，包含：
- `engine.py`：规则执行与冷却/节流
- `rules.py`：规则集合（闲置、资源结构、时间窗与时间点提醒）

### `tts/`

语音播放模块，包含：
- `speaker.py`：edge-tts 播报线程与队列（含 Windows MCI 播放）

### `utils/`

通用工具模块，包含：
- `logging.py`：日志初始化
- `debug_dump.py`：调试输出与图像保存
- `dpi.py`：系统缩放读取

### `tools/`

工具脚本目录，包含：
- `rule_verify.py`：规则验证工具（离线验证规则触发与冷却）

### `doc/`

文档目录，包含：
- `后端初步项目文档.md`：需求与总体设计参考
- `后端接口文档.md`：对前端的接口协议与字段说明
- `打包发布说明.md`：打包命令、发布清单与目标机检查项

## TODO

### 识别精度与鲁棒性
- 优化字符粘连拆分策略（垂直投影、二次切分）
- 针对不同 UI Scale 提供更多模板集与自动选择
- 对 ROI 质量做更细粒度的异常检测（黑屏、偏移、光照变化）

### 调试与可观测
- 增加 ROI 调试帧落盘开关与命名规则
- 记录识别失败原因与统计指标

### 通信与控制
- 增加 CONFIG_SET 返回的详细错误码
- 增加识别暂停/恢复的更细粒度控制

### TTS
- 增加语音队列长度限制与丢弃策略

### 测试与样例
- 提供样例配置与模拟数据回放

## 项目难点

- 全屏抓取稳定性：不同显卡与游戏显示模式下，`dxcam` 可能失败，需要在不中断流程的前提下自动降级到 `mss`。
- ROI 与 DPI 对齐：前端坐标需要结合系统缩放进行修正，否则 OCR 会出现系统性偏移。
- 实时性与稳定性平衡：识别链路必须控制延迟，同时避免短时识别抖动引发规则误触发。
- 规则状态管理：规则同时涉及时间窗、持续触发、冷却、累加冷却与复位条件，状态机设计复杂且容易相互干扰。
- 时间轴提醒鲁棒性：计时器可能跳值或短时识别失败，既要防重复播报，也要在新对局开始后正确复位。

## 项目亮点

- 模块边界清晰：抓屏、识别、校验、规则、语音、通信解耦，便于独立迭代与排障。
- 协议统一：前后端消息结构一致，支持状态、数据、告警、心跳完整链路。
- 规则引擎能力完整：支持 `holdFor`、时间窗、基础冷却、累加冷却、一次性提醒，能覆盖中后期策略提醒场景。
- 语音链路可观测：从规则命中到语音完成均有关键日志，便于快速定位“命中未播报”问题。
- 兼容性考虑到位：TTS 从 `pyttsx3` 切换到 `edge-tts`，并对旧参数格式保持兼容，降低前端改造成本。
