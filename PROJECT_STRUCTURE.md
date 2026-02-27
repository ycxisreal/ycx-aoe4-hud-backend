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
    preprocess.py
    segment.py
    templates.py
    classifier.py
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
  templates/
    hud_normal/
      README.txt
    res_bold/
      README.txt
  doc/
    后端初步项目文档.md
    后端接口文档.md
    日志输出位置.md
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
- 语音播放（`pyttsx3`）

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
- `preprocess.py`：ROI 预处理（灰度、二值化、反色、去噪）
- `segment.py`：字符切分（连通域过滤、冒号合并）
- `templates.py`：模板集加载与归一化
- `classifier.py`：HOG 特征 + 轻量 KNN 分类
- `pipeline.py`：流水线组合（裁剪 → 预处理 → 切分 → 分类 → 解析）
- `smoothing.py`：多帧稳定化（投票）
- `validation.py`：合法性校验与质量检测

### `analysis/`

规则引擎模块，包含：
- `engine.py`：规则执行与冷却/节流
- `rules.py`：规则集合（闲置村民规则）

### `tts/`

语音播放模块，包含：
- `speaker.py`：pyttsx3 播报线程与队列

### `utils/`

通用工具模块，包含：
- `logging.py`：日志初始化
- `debug_dump.py`：调试输出与图像保存
- `dpi.py`：系统缩放读取

### `templates/`

模板资源目录，包含：
- `hud_normal/README.txt`：普通字体模板集说明
- `res_bold/README.txt`：加粗字体模板集说明

### `doc/`

文档目录，包含：
- `后端初步项目文档.md`：需求与总体设计参考
- `后端接口文档.md`：对前端的接口协议与字段说明

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
