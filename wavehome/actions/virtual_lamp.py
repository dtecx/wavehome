class VirtualLampActions:
    def __init__(self, lamp_controller):
        self.lamp = lamp_controller

    def execute(self, action: dict) -> str | None:
        kind = action.get("kind")

        if kind == "virtual_lamp.toggle":
            self.lamp.lamp_on = not self.lamp.lamp_on
            if not self.lamp.lamp_on:
                self.lamp.party_mode = False
            return "toggle"

        if kind == "virtual_lamp.turn_on":
            self.lamp.lamp_on = True
            return "turn_on"

        if kind == "virtual_lamp.turn_off":
            self.lamp.lamp_on = False
            self.lamp.party_mode = False
            return "turn_off"

        if kind == "virtual_lamp.toggle_party":
            self.lamp.party_mode = not self.lamp.party_mode
            self.lamp.lamp_on = True
            self.lamp.color_active = False
            return "party_toggled"

        if kind == "virtual_lamp.brightness_step":
            direction = int(action.get("direction", 1))
            step = int(action.get("step_percent", 10))
            self.lamp.brightness = max(0, min(100, self.lamp.brightness + direction * step))
            self.lamp.lamp_on = True
            return "brightness_changed"

        return None
