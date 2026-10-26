"""
系統負載與溫度驅動的人物表情狀態機 (含防閃爍遲滯緩衝 Hysteresis)
"""

from enum import Enum
import config


class SystemState(str, Enum):
    IDLE = "idle"
    GAMING = "gaming"
    OVERHEAT = "overheat"


def _safe_float(val) -> float:
    if val is None:
        return 0.0
    try:
        return max(0.0, float(val))
    except (TypeError, ValueError):
        return 0.0


class StateMachine:
    """根據 CPU 與 GPU 使用率及溫度決定當前應顯示的人物表情狀態。"""

    def __init__(
        self,
        initial_state: SystemState = SystemState.IDLE,
        thresholds: dict | None = None,
    ):
        self.state = SystemState(initial_state)
        self.thresholds = thresholds or config.STATE_THRESHOLDS

    def update(self, cpu_info: dict | None, gpu_info: dict | None) -> SystemState:
        cpu_info = cpu_info or {}
        gpu_info = gpu_info or {}

        max_usage = max(
            _safe_float(cpu_info.get("usage")),
            _safe_float(gpu_info.get("usage")),
        )
        max_temp = max(
            _safe_float(cpu_info.get("temp")),
            _safe_float(gpu_info.get("temp")),
        )

        t = self.thresholds

        # 1. 優先檢查是否達到高溫／極限負載警戒 (OVERHEAT)
        if (
            max_temp >= t["overheat_enter_temp"]
            or max_usage >= t["overheat_enter_usage"]
        ):
            self.state = SystemState.OVERHEAT
            return self.state

        # 2. 若目前處於 OVERHEAT，檢查是否低於降級門檻
        if self.state == SystemState.OVERHEAT:
            if (
                max_temp < t["overheat_exit_temp"]
                and max_usage < t["overheat_exit_usage"]
            ):
                # 降級後再看應落在 GAMING 或直接回 IDLE
                if (
                    max_usage < t["gaming_exit_usage"]
                    and max_temp < t["gaming_exit_temp"]
                ):
                    self.state = SystemState.IDLE
                else:
                    self.state = SystemState.GAMING
            return self.state

        # 3. 若目前處於 IDLE，檢查是否升級至 GAMING
        if self.state == SystemState.IDLE:
            if (
                max_usage >= t["gaming_enter_usage"]
                or max_temp >= t["gaming_enter_temp"]
            ):
                self.state = SystemState.GAMING
            return self.state

        # 4. 若目前處於 GAMING，檢查是否低於退回 IDLE 門檻
        if self.state == SystemState.GAMING:
            if (
                max_usage < t["gaming_exit_usage"]
                and max_temp < t["gaming_exit_temp"]
            ):
                self.state = SystemState.IDLE
            return self.state

        return self.state
