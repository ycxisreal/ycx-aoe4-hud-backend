"""
AoE4 HUD 后端入口。
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from analysis.engine import RuleEngine
from capture.manager import CaptureManager
from core.config import ConfigSetPayload, WsMessage
from core.state import BackendState, RuntimeContext
from recog.pipeline import RecognizePipeline
from recog.smoothing import FieldSmoother
from recog.validation import FieldValidator
from tts.speaker import TtsSpeaker
from utils.logging import setup_logging
from utils.dpi import get_system_dpi_scale
from ws.protocol import make_alert, make_data, make_pong, make_status
from ws.server import WsServer


class BackendApp:
    # 初始化后端应用
    def __init__(self) -> None:
        self.logger = logging.getLogger("backend.app")
        self.state = BackendState(state="starting")
        self.context = RuntimeContext()
        self.pipeline = RecognizePipeline()
        self.smoother = FieldSmoother(window_size=7)
        self.validator = FieldValidator()
        self.rule_engine = RuleEngine()
        self.capture_manager = CaptureManager()
        self.tts = TtsSpeaker()
        self.tts.start()
        self.ws = WsServer(state=self.state)
        self.capture_task: Optional[asyncio.Task] = None
        self.fail_count = 0
        self.last_timer_debug_ts = 0
        self.debug_frame_index = 0

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
        self._apply_dpi_scale(config)
        self.logger.info("配置 ROI 数量: %d", len(config.rois))
        if config.rois:
            self.logger.info("ROI 示例: %s", config.rois[0].dict())
        self.capture_manager.initialize(display_id=config.screen.displayId)
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
            self.logger.info("识别循环任务已创建")
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

    # OCR 路线不再加载模板集

    # 根据系统缩放修正 ROI
    def _apply_dpi_scale(self, config: ConfigSetPayload) -> None:
        scale = config.screen.dpiScale
        if not scale or scale <= 0:
            scale = get_system_dpi_scale()
            config.screen.dpiScale = scale
        if abs(scale - 1.0) < 0.01:
            return
        for roi in config.rois:
            roi.rect.x = int(round(roi.rect.x * scale))
            roi.rect.y = int(round(roi.rect.y * scale))
            roi.rect.w = int(round(roi.rect.w * scale))
            roi.rect.h = int(round(roi.rect.h * scale))
            roi.rect.x += 2
            roi.rect.y += 2
        config.screen.width = int(round(config.screen.width * scale))
        config.screen.height = int(round(config.screen.height * scale))
        self.logger.info("已应用系统缩放比例: %.2f", scale)

    # 捕获循环
    async def _capture_loop(self) -> None:
        self.logger.info("识别循环开始运行")
        while True:
            try:
                if not self.context.running or self.context.config is None:
                    await asyncio.sleep(0.2)
                    continue
                if not self.context.config.recognition.enabled:
                    self.logger.warning("识别未启用：recognition.enabled=false")
                    await asyncio.sleep(0.5)
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
            results = self.pipeline.process(frame, self.context.config.rois)
                fields = _map_fields(results)
                stable_fields = _smooth_fields(self.smoother, fields)
                quality = self.validator.validate(stable_fields)
                self.context.quality_ok = quality["ok"]
                self.context.quality_reason = quality["reason"]
                self._log_timer_invalid(results, stable_fields, ts, quality["reason"])

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
            except Exception as exc:
                self.logger.error("识别循环异常: %s", str(exc))
                await asyncio.sleep(0.5)

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

    # 记录计时器非法的识别结果（节流）
    def _log_timer_invalid(
        self, raw_fields: Dict[str, Any], stable_fields: Dict[str, Any], ts: int, reason: Optional[str]
    ) -> None:
        if reason != "timer_invalid":
            return
        if ts - self.last_timer_debug_ts < 2000:
            return
        self.last_timer_debug_ts = ts
        raw_timer = raw_fields.get("timer")
        stable_timer = stable_fields.get("timer")
        box_count = None
        if isinstance(raw_timer, dict):
            box_count = raw_timer.get("boxCount")
        self.logger.info("计时器识别异常 raw=%s stable=%s boxCount=%s", raw_timer, stable_timer, box_count)




# 字段映射到协议结构
def _map_fields(results: Dict[str, Any]) -> Dict[str, Any]:
    fields: Dict[str, Any] = {"resources": {}, "gatherers": {}}
    for kind, value in results.items():
        if kind == "timer":
            fields["timer"] = _strip_meta(value)
        elif kind == "idle":
            fields["idleVillagers"] = _strip_meta(value)
        elif kind.startswith("res_"):
            name = kind.replace("res_", "")
            fields["resources"][name] = _strip_meta(value)
        elif kind.startswith("gather_"):
            name = kind.replace("gather_", "")
            fields["gatherers"][name] = _strip_meta(value)
    return fields


# 去除识别元信息
def _strip_meta(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    return {"value": value.get("value"), "conf": value.get("conf", 0.0)}




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
