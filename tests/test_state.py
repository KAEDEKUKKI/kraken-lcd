import unittest
from monitor.state import StateMachine, SystemState


class TestStateMachine(unittest.TestCase):
    def test_initial_state_is_idle(self):
        sm = StateMachine()
        self.assertEqual(sm.state, SystemState.IDLE)

    def test_transitions_and_hysteresis(self):
        sm = StateMachine()
        # 待機低負載維持 IDLE
        self.assertEqual(
            sm.update({"usage": 30.0, "temp": 50.0}, {"usage": 20.0, "temp": 45.0}),
            SystemState.IDLE,
        )
        # 進入 GAMING (usage >= 50)
        self.assertEqual(
            sm.update({"usage": 52.0, "temp": 58.0}, {"usage": 10.0, "temp": 45.0}),
            SystemState.GAMING,
        )
        # 遲滯區間：usage 降到 46% (未低於 45%)，應維持 GAMING 不閃爍
        self.assertEqual(
            sm.update({"usage": 46.0, "temp": 58.0}, {"usage": 10.0, "temp": 45.0}),
            SystemState.GAMING,
        )
        # 低於退回門檻 (< 45% 且 < 60°C) 才回到 IDLE
        self.assertEqual(
            sm.update({"usage": 44.0, "temp": 59.0}, {"usage": 20.0, "temp": 50.0}),
            SystemState.IDLE,
        )
        # 高溫直接進入 OVERHEAT (temp >= 80°C)
        self.assertEqual(
            sm.update({"usage": 60.0, "temp": 81.0}, {"usage": 50.0, "temp": 70.0}),
            SystemState.OVERHEAT,
        )
        # 遲滯區間：溫度降到 76°C (未低於 75°C)，維持 OVERHEAT
        self.assertEqual(
            sm.update({"usage": 60.0, "temp": 76.0}, {"usage": 50.0, "temp": 70.0}),
            SystemState.OVERHEAT,
        )
        # 溫度降到 74°C 且使用率 < 85%，降級回 GAMING
        self.assertEqual(
            sm.update({"usage": 60.0, "temp": 74.0}, {"usage": 50.0, "temp": 68.0}),
            SystemState.GAMING,
        )

    def test_handles_none_sensor_values(self):
        sm = StateMachine()
        self.assertEqual(
            sm.update({"usage": None, "temp": None}, {}),
            SystemState.IDLE,
        )


if __name__ == "__main__":
    unittest.main()
