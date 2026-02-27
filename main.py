"""
AoE4 HUD 后端入口。
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from analysis.engine import RuleEngine
from capture.manager import CaptureManager
from core.config import ConfigSetPayload, WsMessage
from core.state import BackendState, RuntimeContext
from recog.pipeline import RecognizePipeline
from recog.smoothing import FieldSmoother
from recog.templates import TemplateStore
from recog.validation import FieldValidator
from tts.speaker import TtsSpeaker
from utils.logging import setup_logging
from ws.protocol import make_alert, make_data, make_pong, make_status
from ws.server import WsServer


class BackendApp:
    # 初始化后端应用
    def __init__(self) -> None:
        self.logger = logging.getLogger("backend.app")
        self.state = BackendState(state="starting")
        self.context = RuntimeContext()
        self.template_store = TemplateStore()
        self.pipeline = RecognizePipeline(self.template_store)
        self.smoother = FieldSmoother(window_size=7)
        self.validator = FieldValidator()
        self.rule_engine = RuleEngine()
        self.capture_manager = CaptureManager()
        self.tts = TtsSpeaker()
        self.tts.start()
        self.ws = WsServer(state=self.state)
        self.capture_task: Optional[asyncio.Task] = None
        self.fail_count = 0

    # 启动应用
    async def run(self) -> None:
        self.state.update("ready")
        await self.ws.start(self.handle_message)
        await self._publish_status()
        self.logger.info("后端已就绪，WS 已监听")
        await asyncio.Future()

    # 处理前端消息
    async def handle_message(self, data: Dict[str, Any], client) -> None:
        try:
            msg = WsMessage.parse(data)
        except Exception:
        self.logger.warning("WS 消息解析失败")
            return
        self.logger.info("收到 WS 消息: %s", msg.type)
        if msg.type == "CONFIG_SET":
            await self._handle_config(msg.payload)
        elif msg.type in ("START", "RECOG_START", "OCR_START"):
            await self._handle_start()
        elif msg.type in ("STOP", "RECOG_STOP", "OCR_STOP"):
            await self._handle_stop()
        elif msg.type == "PING":
            await self.ws.send(client, make_pong(msg.payload))

    # 处理配置下发
    async def _handle_config(self, payload: Dict[str, Any]) -> None:
        try:
            config = ConfigSetPayload(**payload)
        except Exception as exc:
            self.state.update("error", message="config_invalid", details={"error": str(exc)})
            await self._publish_status()
            self.logger.error("配置解析失败: %s", str(exc))
            return
        self.context.config = config
        self.logger.info("配置 ROI 数量: %d", len(config.rois))
        if config.rois:
            self.logger.info("ROI 示例: %s", config.rois[0].dict())
        self.capture_manager.initialize(display_id=config.screen.displayId)
        self._load_templates(config)
        self.pipeline.update_kind_map(self._build_kind_map(config))
        if not self.template_store.is_ready():
            self.state.update("error", message="templates_missing", details={"path": self._template_path(config)})
            await self._publish_status()
            self.logger.error("模板集缺失: %s", self._template_path(config))
            return
        if config.tts:
            self.tts.configure(rate=config.tts.rate, volume=config.tts.volume)
        self.state.update("ready")
        await self._publish_status()
        self.logger.info("配置下发完成，ROI 数量: %d", len(config.rois))

    # 处理开始识别
    async def _handle_start(self) -> None:
        if self.context.config is None:
            self.state.update("error", message="config_missing")
            await self._publish_status()
            self.logger.error("启动失败：未收到配置")
            return
        self.context.running = True
        if self.capture_task is None or self.capture_task.done():
            self.capture_task = asyncio.create_task(self._capture_loop())
        self.state.update("running")
        await self._publish_status()
        self.logger.info("识别已启动")

    # 处理停止识别
    async def _handle_stop(self) -> None:
        self.context.running = False
        self.state.update("stopped")
        await self._publish_status()
        self.logger.info("识别已停止")

    # 发布状态
    async def _publish_status(self) -> None:
        status = make_status(self.state.state, self.state.message, self.state.details)
        await self.ws.broadcast(status)

    # 加载模板集
    def _load_templates(self, config: ConfigSetPayload) -> None:
        template_config = config.templates
        if template_config and template_config.sets:
            for name, raw_path in template_config.sets.items():
                path = self._resolve_path(raw_path)
                self.template_store.load(name, path)
                self.logger.info("模板集加载: %s -> %s", name, path)
            return

        if template_config and (template_config.path or template_config.setName):
            path = self._template_path(config)
            set_name = template_config.setName if template_config and template_config.setName else "hud_normal"
            self.template_store.load(set_name, path)
            self.logger.info("模板集加载: %s -> %s", set_name, path)
            return

        default_sets = ["hud_normal", "res_bold"]
        for name in default_sets:
            path = self._resolve_path(str(Path("templates") / name))
            self.template_store.load(name, path)
            self.logger.info("模板集加载: %s -> %s", name, path)

    # 计算模板路径
    def _template_path(self, config: ConfigSetPayload) -> str:
        template_config = config.templates
        if template_config and template_config.path:
            path = Path(template_config.path)
        else:
            name = template_config.setName if template_config and template_config.setName else "hud_normal"
            path = Path("templates") / name
        return self._resolve_path(str(path))

    # 解析为绝对路径
    def _resolve_path(self, raw_path: str) -> str:
        path = Path(raw_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        return str(path)

    # 构建模板映射
    def _build_kind_map(self, config: ConfigSetPayload) -> Dict[str, str]:
        template_config = config.templates
        if template_config and template_config.kindMap:
            return template_config.kindMap
        return {
            "res_*": "res_bold",
            "default": "hud_normal",
        }

    # 捕获循环
    async def _capture_loop(self) -> None:
        while True:
            if not self.context.running or self.context.config is None:
                await asyncio.sleep(0.2)
                continue
            if not self.context.config.recognition.enabled:
                await asyncio.sleep(0.2)
                continue

            hz = max(1, self.context.config.recognition.hz)
            frame = self.capture_manager.capture()
            ts = int(asyncio.get_running_loop().time() * 1000)
            if frame is None:
                self.fail_count += 1
                if self.fail_count >= 10:
                    self.context.quality_ok = False
                    self.context.quality_reason = "capture_failed"
                    self.logger.warning("抓屏连续失败次数: %d", self.fail_count)
                await asyncio.sleep(1.0 / hz)
                continue

            self.fail_count = 0
            self._dump_debug_frames(frame, ts)
            results = self.pipeline.process(frame, self.context.config.rois)
            fields = _map_fields(results)
            stable_fields = _smooth_fields(self.smoother, fields)
            quality = self.validator.validate(stable_fields)
            self.context.quality_ok = quality["ok"]
            self.context.quality_reason = quality["reason"]

            data_payload = {
                "fields": stable_fields,
                "frameTs": ts,
                "quality": {"ok": self.context.quality_ok, "reason": self.context.quality_reason},
            }
            self.logger.info(
                "已发送识别数据，quality=%s, reason=%s",
                self.context.quality_ok,
                self.context.quality_reason,
            )
            await self.ws.broadcast(make_data(data_payload))
            await self._handle_alerts(stable_fields, ts)
            await asyncio.sleep(1.0 / hz)

    # 处理提醒事件
    async def _handle_alerts(self, fields: Dict[str, Any], ts: int) -> None:
        alerts = self.rule_engine.evaluate(fields, ts)
        for alert in alerts:
            spoken = False
            if self.context.config and self.context.config.tts and self.context.config.tts.enabled:
                self.tts.speak(alert.get("text", ""))
                spoken = True
            alert_payload = {
                "id": alert.get("id"),
                "level": alert.get("level", "info"),
                "text": alert.get("text", ""),
                "spoken": spoken,
                "cooldownMs": alert.get("cooldownMs", 0),
            }
            await self.ws.broadcast(make_alert(alert_payload))
            self.logger.info("提醒事件已发送: %s", alert_payload.get("id"))

    # 调试帧保存
    def _dump_debug_frames(self, frame, ts: int) -> None:
        if self.context.config is None or self.context.config.debug is None:
            return
        if not self.context.config.debug.saveRoiFrames:
            return
        from utils.debug_dump import dump_image

        save_dir = self.context.config.debug.saveDir or "debug"
        for roi in self.context.config.rois:
            cropped = _crop(frame, roi.rect)
            filename = f"{roi.kind}_{roi.id}_{ts}.png"
            dump_image(cropped, Path(save_dir) / filename)


# 字段映射到协议结构
def _map_fields(results: Dict[str, Any]) -> Dict[str, Any]:
    fields: Dict[str, Any] = {"resources": {}, "gatherers": {}}
    for kind, value in results.items():
        if kind == "timer":
            fields["timer"] = value
        elif kind == "idle":
            fields["idleVillagers"] = value
        elif kind.startswith("res_"):
            name = kind.replace("res_", "")
            fields["resources"][name] = value
        elif kind.startswith("gather_"):
            name = kind.replace("gather_", "")
            fields["gatherers"][name] = value
    return fields


# 稳定化字段
def _smooth_fields(smoother: FieldSmoother, fields: Dict[str, Any]) -> Dict[str, Any]:
    stable: Dict[str, Any] = {"resources": {}, "gatherers": {}}
    if "timer" in fields:
        value = fields["timer"].get("value") if fields["timer"] else None
        stable_value = smoother.push("timer", value)
        stable["timer"] = {"value": stable_value, "conf": fields["timer"].get("conf", 0.0)}

    if "idleVillagers" in fields:
        idle = fields["idleVillagers"]
        value = idle.get("value") if idle else None
        stable_value = smoother.push("idleVillagers", str(value) if value is not None else None)
        stable["idleVillagers"] = {
            "value": int(stable_value) if stable_value is not None else None,
            "conf": idle.get("conf", 0.0),
        }

    for key, item in fields.get("resources", {}).items():
        value = item.get("value") if item else None
        stable_value = smoother.push(f"resources.{key}", str(value) if value is not None else None)
        stable["resources"][key] = {
            "value": int(stable_value) if stable_value is not None else None,
            "conf": item.get("conf", 0.0),
        }

    for key, item in fields.get("gatherers", {}).items():
        value = item.get("value") if item else None
        stable_value = smoother.push(f"gatherers.{key}", str(value) if value is not None else None)
        stable["gatherers"][key] = {
            "value": int(stable_value) if stable_value is not None else None,
            "conf": item.get("conf", 0.0),
        }

    return stable


# 主程序入口
def main() -> None:
    setup_logging()
    app = BackendApp()
    asyncio.run(app.run())


if __name__ == "__main__":
    main()
