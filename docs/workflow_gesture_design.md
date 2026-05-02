# waveHome workflow gesture design

## Goal

The project should not hardcode smart-home gestures in Python. The app should detect a small vocabulary of stable gestures, then the workflow engine should combine them into configurable rules.

A user should be able to build:

```text
WHEN gesture / sequence / hold / motion / value control
WITH timing and safety blocks
DO lamp / workflow / future smart-home action
```

## Recommended gesture vocabulary

### Wake / command mode

Use these gestures to intentionally start control mode:

- `BOTH_OPEN_PALMS` held for 1s: safest wake gesture.
- `OPEN_PALM` held for 1.8s: one-hand fallback.
- `FIST -> OPEN_PALM`: alternative wake sequence.
- `BOTH_OPEN_PALMS -> FIST`: stronger wake sequence for noisy environments.

### Confirmation / cancellation

Use these for actions that should not happen accidentally:

- `TWO_THUMBS_UP`: confirm dangerous/global actions.
- `THUMB_DOWN`: cancel confirmation or cancel current workflow.
- `BOTH_FISTS` held: request all-off, but do not execute without confirmation.
- `OPEN_PALM` held: pause/stop current gesture sequence.

### Toggle / on-off controls

Good choices:

- `OPEN_PALM -> FIST -> OPEN_PALM`: toggle lamp.
- `FIST -> POINT`: turn selected device on.
- `FIST -> THUMB_DOWN`: turn selected device off.
- `BOTH_FISTS -> TWO_THUMBS_UP`: all off with confirmation.

### Continuous controls

Good choices:

- `THUMB_UP` repeat hold: brightness up.
- `THUMB_DOWN` repeat hold: brightness down.
- `SWIPE_UP`: brightness up one step.
- `SWIPE_DOWN`: brightness down one step.
- `PEACE` rotation: color/temperature value.
- `PINCH` distance in the future: precise dimming.

### Scene controls

Good choices:

- `THREE`: scene 1.
- `FOUR`: scene 2.
- `HORNS`: party/special mode.
- `SWIPE_LEFT`: previous scene/device.
- `SWIPE_RIGHT`: next scene/device.

## False-trigger protection model

Use multiple layers. No single layer is enough.

### 1. Stable gesture filter

Before a gesture enters the workflow engine, require it to be stable for a minimum time.

Recommended defaults:

- static gestures: 250-400ms stable
- wake gestures: 800-1800ms stable
- destructive gestures: 1000-2000ms stable
- motion gestures: cooldown after detection

### 2. Command mode

Most normal actions should require command mode.

Example:

```text
BOTH_OPEN_PALMS held 1s
-> command mode active for 10-12s
-> normal rules can execute
-> command mode expires automatically
```

This prevents random hand movement from controlling the lamp.

### 3. Cooldowns

Every rule should have a cooldown unless it is a continuous value control.

Recommended defaults:

- toggle: 1500ms
- scene change: 1000ms
- swipe brightness: 700ms
- all-off: 5000ms
- party mode: 3000ms

### 4. Confirmation

Dangerous/global actions should create a pending confirmation instead of executing immediately.

Example:

```text
BOTH_FISTS held 1800ms
-> pending all-off confirmation for 4000ms
-> TWO_THUMBS_UP executes
-> THUMB_DOWN cancels
-> timeout cancels
```

### 5. Gesture-specific allowed context

Some gestures should only mean something inside a context:

- `THUMB_UP`: confirm only when pending confirmation exists.
- `THUMB_UP`: brightness up only when command mode is active.
- `PEACE`: color control only when command mode is active.
- `BOTH_FISTS`: all-off only after command mode.

### 6. Visual feedback

The dashboard/runtime overlay should show:

- detected gesture
- stable gesture
- command mode active/expired
- next expected sequence gesture
- pending confirmation
- cancelled/timed-out state

This is important because gesture systems feel broken if the user cannot see what the engine is waiting for.
