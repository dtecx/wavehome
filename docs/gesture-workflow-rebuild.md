# waveHome gesture workflow rebuild plan

## Goal

Move waveHome from hardcoded gesture actions to configurable user-defined gesture workflows.

Current prototype:
- detects hand gestures from MediaPipe landmarks
- maps them to fixed command keys
- runs hardcoded lamp actions in VirtualLampController

Target architecture:

Camera
-> hand landmarks
-> gesture primitives
-> stable gesture events
-> workflow engine
-> safety/confirmation layer
-> action adapter
-> virtual lamp / smart home device

## Rebuild phases

1. Add a gesture catalog.
2. Add normalized GestureEvent objects.
3. Add configurable rule schema.
4. Add default rules matching the current hardcoded behavior.
5. Add action adapter layer.
6. Add workflow engine.
7. Wire workflow engine into app while preserving existing behavior.
8. Add false-trigger protection.
9. Add dashboard API.
10. Add visual web dashboard for editing rules.

## Important rule

Gestures should not directly perform actions.
Gestures should produce events.
Rules should decide which actions run.
