import unittest

from wavehome.workflow.engine import WorkflowEngine


class FakeActions:
    def __init__(self):
        self.executed = []

    def execute(self, action):
        self.executed.append(action)
        return action["kind"]


class WorkflowEngineTests(unittest.TestCase):
    def test_sequence_executes_after_steps(self):
        actions = FakeActions()
        engine = WorkflowEngine(
            [
                {
                    "id": "toggle",
                    "enabled": True,
                    "name": "Toggle",
                    "trigger": {
                        "kind": "sequence",
                        "steps": [
                            {"gesture": "OPEN_PALM", "hold_ms": 0},
                            {"gesture": "FIST", "hold_ms": 0},
                        ],
                        "max_total_ms": 5000,
                        "max_gap_ms": 2000,
                    },
                    "safety": {
                        "cooldown_ms": 0,
                        "confirmation": {"required": False},
                    },
                    "action": {"kind": "virtual_lamp.toggle"},
                }
            ],
            actions,
        )

        self.assertEqual(engine.update("OPEN_PALM", 0.0), "sequence_step")
        self.assertIsNone(engine.update("OPEN_PALM", 0.1))
        self.assertEqual(engine.update("FIST", 0.2), "virtual_lamp.toggle")
        self.assertEqual(len(actions.executed), 1)

    def test_sequence_resets_after_max_gap(self):
        actions = FakeActions()
        engine = WorkflowEngine(
            [
                {
                    "id": "toggle",
                    "enabled": True,
                    "name": "Toggle",
                    "trigger": {
                        "kind": "sequence",
                        "steps": [
                            {"gesture": "OPEN_PALM", "hold_ms": 0},
                            {"gesture": "FIST", "hold_ms": 0},
                        ],
                        "max_total_ms": 5000,
                        "max_gap_ms": 500,
                    },
                    "safety": {
                        "cooldown_ms": 0,
                        "confirmation": {"required": False},
                    },
                    "action": {"kind": "virtual_lamp.toggle"},
                }
            ],
            actions,
        )

        self.assertEqual(engine.update("OPEN_PALM", 0.0), "sequence_step")
        self.assertIsNone(engine.update("FIST", 1.0))
        self.assertEqual(len(actions.executed), 0)

    def test_hold_requires_hold_time(self):
        actions = FakeActions()
        engine = WorkflowEngine(
            [
                {
                    "id": "all_off",
                    "enabled": True,
                    "name": "All off",
                    "trigger": {
                        "kind": "hold",
                        "gesture": "BOTH_FISTS",
                        "hold_ms": 1000,
                    },
                    "safety": {
                        "cooldown_ms": 0,
                        "confirmation": {"required": False},
                    },
                    "action": {"kind": "virtual_lamp.turn_off"},
                }
            ],
            actions,
        )

        self.assertIsNone(engine.update("BOTH_FISTS", 0.0))
        self.assertIsNone(engine.update("BOTH_FISTS", 0.5))
        self.assertEqual(engine.update("BOTH_FISTS", 1.1), "virtual_lamp.turn_off")
        self.assertEqual(len(actions.executed), 1)

    def test_armed_hold_repeats_action(self):
        actions = FakeActions()
        engine = WorkflowEngine(
            [
                {
                    "id": "brightness_up",
                    "enabled": True,
                    "name": "Brightness up",
                    "trigger": {
                        "kind": "armed_hold",
                        "arm_gesture": "FIST",
                        "gesture": "THUMB_UP",
                        "arm_timeout_ms": 2000,
                        "hold_ms": 500,
                        "repeat_ms": 500,
                    },
                    "safety": {
                        "cooldown_ms": 0,
                        "confirmation": {"required": False},
                    },
                    "action": {
                        "kind": "virtual_lamp.brightness_step",
                        "direction": 1,
                        "step_percent": 10,
                    },
                }
            ],
            actions,
        )

        self.assertEqual(engine.update("FIST", 0.0), "armed")
        self.assertIsNone(engine.update(None, 0.1))
        self.assertEqual(engine.update("THUMB_UP", 0.2), "armed_hold_started")
        self.assertIsNone(engine.update("THUMB_UP", 0.6))
        self.assertEqual(engine.update("THUMB_UP", 0.8), "virtual_lamp.brightness_step")
        self.assertEqual(engine.update("THUMB_UP", 1.4), "virtual_lamp.brightness_step")
        self.assertEqual(len(actions.executed), 2)

    def test_confirmation_can_be_cancelled(self):
        actions = FakeActions()
        engine = WorkflowEngine(
            [
                {
                    "id": "all_off",
                    "enabled": True,
                    "name": "All off",
                    "trigger": {
                        "kind": "hold",
                        "gesture": "BOTH_FISTS",
                        "hold_ms": 0,
                    },
                    "safety": {
                        "cooldown_ms": 0,
                        "confirmation": {
                            "required": True,
                            "gesture": "TWO_THUMBS_UP",
                            "timeout_ms": 4000,
                        },
                    },
                    "action": {"kind": "virtual_lamp.turn_off"},
                }
            ],
            actions,
        )

        self.assertEqual(engine.update("BOTH_FISTS", 0.0), "pending_confirmation")
        self.assertEqual(engine.update("THUMB_DOWN", 0.5), "confirmation_cancelled")
        self.assertEqual(len(actions.executed), 0)


if __name__ == "__main__":
    unittest.main()


class CommandModeWorkflowTests(unittest.TestCase):
    def test_rule_requires_command_mode(self):
        actions = FakeActions()
        engine = WorkflowEngine(
            [
                {
                    "id": "toggle",
                    "enabled": True,
                    "name": "Toggle",
                    "trigger": {
                        "kind": "hold",
                        "gesture": "FIST",
                        "hold_ms": 0,
                    },
                    "safety": {
                        "command_mode": {"required": True},
                        "cooldown_ms": 0,
                        "confirmation": {"required": False},
                    },
                    "action": {"kind": "virtual_lamp.toggle"},
                }
            ],
            actions,
        )

        self.assertIsNone(engine.update("FIST", 0.0))
        self.assertEqual(len(actions.executed), 0)

    def test_enter_command_mode_allows_protected_rule(self):
        actions = FakeActions()
        engine = WorkflowEngine(
            [
                {
                    "id": "wake",
                    "enabled": True,
                    "name": "Wake",
                    "trigger": {
                        "kind": "hold",
                        "gesture": "OPEN_PALM",
                        "hold_ms": 0,
                    },
                    "safety": {
                        "cooldown_ms": 0,
                        "confirmation": {"required": False},
                    },
                    "action": {
                        "kind": "workflow.enter_command_mode",
                        "duration_ms": 3000,
                    },
                },
                {
                    "id": "toggle",
                    "enabled": True,
                    "name": "Toggle",
                    "trigger": {
                        "kind": "hold",
                        "gesture": "FIST",
                        "hold_ms": 0,
                    },
                    "safety": {
                        "command_mode": {"required": True},
                        "cooldown_ms": 0,
                        "confirmation": {"required": False},
                    },
                    "action": {"kind": "virtual_lamp.toggle"},
                },
            ],
            actions,
        )

        self.assertEqual(engine.update("OPEN_PALM", 0.0), "command_mode_entered")
        self.assertEqual(engine.update("FIST", 1.0), "virtual_lamp.toggle")
        self.assertEqual(len(actions.executed), 1)

    def test_command_mode_expires(self):
        actions = FakeActions()
        engine = WorkflowEngine(
            [
                {
                    "id": "wake",
                    "enabled": True,
                    "name": "Wake",
                    "trigger": {
                        "kind": "hold",
                        "gesture": "OPEN_PALM",
                        "hold_ms": 0,
                    },
                    "safety": {
                        "cooldown_ms": 0,
                        "confirmation": {"required": False},
                    },
                    "action": {
                        "kind": "workflow.enter_command_mode",
                        "duration_ms": 1000,
                    },
                },
                {
                    "id": "toggle",
                    "enabled": True,
                    "name": "Toggle",
                    "trigger": {
                        "kind": "hold",
                        "gesture": "FIST",
                        "hold_ms": 0,
                    },
                    "safety": {
                        "command_mode": {"required": True},
                        "cooldown_ms": 0,
                        "confirmation": {"required": False},
                    },
                    "action": {"kind": "virtual_lamp.toggle"},
                },
            ],
            actions,
        )

        self.assertEqual(engine.update("OPEN_PALM", 0.0), "command_mode_entered")
        self.assertIsNone(engine.update("FIST", 2.0))
        self.assertEqual(len(actions.executed), 0)


def test_repeat_hold_waits_then_repeats():
    class Adapter:
        def __init__(self):
            self.calls = 0

        def execute(self, action):
            self.calls += 1
            return action["kind"]

    rules = [
        {
            "id": "repeat_brightness",
            "name": "Repeat brightness",
            "enabled": True,
            "trigger": {
                "kind": "repeat_hold",
                "gesture": "THUMB_UP",
                "hold_ms": 1000,
                "repeat_ms": 500,
            },
            "action": {
                "kind": "virtual_lamp.brightness_step",
                "direction": 1,
                "step_percent": 10,
            },
        }
    ]

    adapter = Adapter()
    engine = WorkflowEngine(rules, adapter)

    assert engine.update("THUMB_UP", 0.0) == "repeat_hold_started"
    assert engine.update("THUMB_UP", 0.5) is None
    assert engine.update("THUMB_UP", 1.0) == "virtual_lamp.brightness_step"
    assert engine.update("THUMB_UP", 1.2) is None
    assert engine.update("THUMB_UP", 1.5) == "virtual_lamp.brightness_step"
    assert adapter.calls == 2
