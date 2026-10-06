extends Node
## Autoload "GameStateManager": the single owner of the game state.
## Allowed transitions are a table, not an if/elif chain. Overlay states pause the tree.

enum State {
	BOOT,
	MENU,
	CHARACTER_SELECTION,
	LEVEL_SELECTION,
	LOADING,
	GAMEPLAY,
	PAUSED,
	LEVEL_COMPLETE,
	GAME_OVER,
	UPGRADE,
	INVENTORY,
	SETTINGS,
}

const TRANSITIONS := {
	State.BOOT: [State.MENU],
	State.MENU: [State.CHARACTER_SELECTION, State.LEVEL_SELECTION, State.SETTINGS],
	State.SETTINGS: [State.MENU],
	State.CHARACTER_SELECTION: [State.MENU, State.LEVEL_SELECTION],
	State.LEVEL_SELECTION: [State.MENU, State.CHARACTER_SELECTION, State.LOADING],
	State.LOADING: [State.GAMEPLAY, State.MENU],
	State.GAMEPLAY: [State.PAUSED, State.UPGRADE, State.INVENTORY, State.LEVEL_COMPLETE, State.GAME_OVER],
	State.PAUSED: [State.GAMEPLAY, State.MENU, State.LEVEL_SELECTION],
	State.UPGRADE: [State.GAMEPLAY, State.UPGRADE],
	State.INVENTORY: [State.GAMEPLAY],
	State.LEVEL_COMPLETE: [State.LEVEL_SELECTION, State.CHARACTER_SELECTION, State.MENU],
	State.GAME_OVER: [State.LOADING, State.LEVEL_SELECTION, State.MENU],
}

## States in which gameplay is frozen (the game scene is still loaded underneath).
const PAUSING_STATES := [State.PAUSED, State.UPGRADE, State.INVENTORY, State.LEVEL_COMPLETE, State.GAME_OVER]

var current: State = State.BOOT
var previous: State = State.BOOT


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS


func can_transition(to: State) -> bool:
	return to in TRANSITIONS.get(current, [])


func change_state(to: State) -> bool:
	if not can_transition(to):
		push_warning("[GameState] transition %s -> %s is not allowed" % [state_name(current), state_name(to)])
		return false
	previous = current
	current = to
	get_tree().paused = to in PAUSING_STATES
	EventBus.game_state_changed.emit(previous, current)
	return true


func is_state(state: State) -> bool:
	return current == state


static func state_name(state: int) -> String:
	return State.keys()[state]
