class_name InputSetup
extends RefCounted
## Registers input actions in code (keyboard / gamepad defaults for desktop testing).
## Touch controls do not use actions directly: they feed InputCommand via InputRouter.

const MOVE_LEFT := &"move_left"
const MOVE_RIGHT := &"move_right"
const MOVE_UP := &"move_up"
const MOVE_DOWN := &"move_down"
const ATTACK := &"attack"
const SKILL := &"skill"
const DASH := &"dash"
const INTERACT := &"interact"
const INVENTORY := &"inventory"
const PAUSE := &"pause"

const KEYS := {
	MOVE_LEFT: [KEY_A, KEY_LEFT],
	MOVE_RIGHT: [KEY_D, KEY_RIGHT],
	MOVE_UP: [KEY_W, KEY_UP],
	MOVE_DOWN: [KEY_S, KEY_DOWN],
	ATTACK: [KEY_J, KEY_SPACE],
	SKILL: [KEY_K],
	DASH: [KEY_L, KEY_SHIFT],
	INTERACT: [KEY_E],
	INVENTORY: [KEY_I, KEY_TAB],
	PAUSE: [KEY_ESCAPE, KEY_P],
}

const JOY_BUTTONS := {
	ATTACK: JOY_BUTTON_A,
	SKILL: JOY_BUTTON_X,
	DASH: JOY_BUTTON_B,
	INTERACT: JOY_BUTTON_Y,
	INVENTORY: JOY_BUTTON_BACK,
	PAUSE: JOY_BUTTON_START,
}

const JOY_AXES := {
	MOVE_LEFT: [JOY_AXIS_LEFT_X, -1.0],
	MOVE_RIGHT: [JOY_AXIS_LEFT_X, 1.0],
	MOVE_UP: [JOY_AXIS_LEFT_Y, -1.0],
	MOVE_DOWN: [JOY_AXIS_LEFT_Y, 1.0],
}


static func ensure_actions() -> void:
	for action: StringName in KEYS:
		if not InputMap.has_action(action):
			InputMap.add_action(action, 0.2)
		for keycode: Key in KEYS[action]:
			var event := InputEventKey.new()
			event.physical_keycode = keycode
			InputMap.action_add_event(action, event)
	for action: StringName in JOY_BUTTONS:
		var event := InputEventJoypadButton.new()
		event.button_index = JOY_BUTTONS[action]
		InputMap.action_add_event(action, event)
	for action: StringName in JOY_AXES:
		var event := InputEventJoypadMotion.new()
		event.axis = JOY_AXES[action][0]
		event.axis_value = JOY_AXES[action][1]
		InputMap.action_add_event(action, event)
