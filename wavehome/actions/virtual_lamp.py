class VirtualLampActions:
    def __init__(self, lamp_controller):
        self.lamp = lamp_controller

    def execute(self, action: dict) -> str | None:
        kind = action.get("kind")

        if kind == "virtual_lamp.toggle":
            self.lamp.lamp_on = not self.lamp.lamp_on
            if not self.lamp.lamp_on:
                self.lamp.party_mode = False
            return "virtual_lamp.toggle"

        if kind == "virtual_lamp.turn_on":
            self.lamp.lamp_on = True
            return "virtual_lamp.turn_on"

        if kind == "virtual_lamp.turn_off":
            self.lamp.lamp_on = False
            self.lamp.party_mode = False
            return "virtual_lamp.turn_off"

        if kind == "virtual_lamp.toggle_party":
            self.lamp.party_mode = not self.lamp.party_mode
            self.lamp.lamp_on = True
            self.lamp.color_active = False
            return "virtual_lamp.toggle_party"

        if kind == "virtual_lamp.brightness_step":
            direction = int(action.get("direction", 1))
            step = int(action.get("step_percent", 10))
            self.lamp.brightness = max(0, min(100, self.lamp.brightness + direction * step))
            self.lamp.lamp_on = True
            return "virtual_lamp.brightness_step"

        if kind == "virtual_lamp.brightness_set":
            value = int(action.get("percent", action.get("value", self.lamp.brightness)))
            self.lamp.brightness = max(0, min(100, value))
            self.lamp.lamp_on = True
            return "virtual_lamp.brightness_set"

        if kind == "virtual_lamp.color_set":
            rgb = action.get("rgb")

            if rgb is None:
                value = float(action.get("value", 0.0))
                value = max(-60.0, min(60.0, value))
                normalized = (value + 60.0) / 120.0
                channel = int(round(normalized * 255))
                rgb = [channel, channel, channel]

            if len(rgb) != 3:
                return None

            self.lamp.lamp_rgb = tuple(max(0, min(255, int(channel))) for channel in rgb)
            self.lamp.lamp_on = True
            self.lamp.party_mode = False
            return "virtual_lamp.color_set"

        return None
