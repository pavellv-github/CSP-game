extends Node
## Autoload "GameManager": run lifecycle (start / finish / retry), rewards, app lifecycle.

const State := preload("res://scripts/core/game_state_manager.gd").State

## Current (or last) run: {level_id, character_id}
var current_level_id: String = ""
var current_character_id: String = ""
## Rewards granted at the end of the last run: [{item_id, quantity}]
var last_rewards: Array[Dictionary] = []
var last_run_summary: Dictionary = {}


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	InputSetup.ensure_actions()
	get_tree().set_auto_accept_quit(false)
	get_tree().set_quit_on_go_back(false)


func boot() -> void:
	GameStateManager.change_state(State.MENU)


func start_run(level_id: String) -> void:
	if not Profile.is_level_unlocked(level_id):
		push_warning("[GameManager] level %s is locked" % level_id)
		return
	current_level_id = level_id
	current_character_id = Profile.get_selected_character_id()
	GameStateManager.change_state(State.LOADING)


func retry() -> void:
	start_run(current_level_id)


func get_current_level() -> LevelDefinition:
	return Content.get_level(current_level_id)


func get_current_character() -> CharacterDefinition:
	return Content.get_character(current_character_id)


## Called by the game scene when the run ends. `summary`: {kills, time, player_level, gold_collected}
func finish_run(victory: bool, summary: Dictionary) -> void:
	last_run_summary = summary
	last_rewards.clear()
	Profile.record_run(int(summary.get("kills", 0)))
	if victory:
		var level := get_current_level()
		for reward: Dictionary in level.rewards:
			var item_id := str(reward.get("item_id", ""))
			var quantity := int(reward.get("quantity", 1))
			Profile.add_item(item_id, quantity)
			EventBus.item_obtained.emit(item_id, quantity)
			last_rewards.append({"item_id": item_id, "quantity": quantity})
		Profile.mark_level_completed(level.id, float(summary.get("time", 0.0)))
	Profile.flush()
	EventBus.run_finished.emit(current_level_id, victory, summary)
	GameStateManager.change_state(State.LEVEL_COMPLETE if victory else State.GAME_OVER)


## The level that follows `level_id` in content order, or "" if none.
func next_level_id(level_id: String) -> String:
	var ids := Content.levels.ids()
	var index := ids.find(level_id)
	return ids[index + 1] if index >= 0 and index + 1 < ids.size() else ""


func _notification(what: int) -> void:
	match what:
		NOTIFICATION_APPLICATION_PAUSED, NOTIFICATION_APPLICATION_FOCUS_OUT:
			if GameStateManager.is_state(State.GAMEPLAY):
				GameStateManager.change_state(State.PAUSED)
			Profile.flush()
		NOTIFICATION_WM_CLOSE_REQUEST:
			Profile.flush()
			get_tree().quit()
		NOTIFICATION_WM_GO_BACK_REQUEST:
			_on_back_requested()


## Android back button / Escape outside gameplay.
func _on_back_requested() -> void:
	match GameStateManager.current:
		State.GAMEPLAY:
			GameStateManager.change_state(State.PAUSED)
		State.PAUSED, State.INVENTORY:
			GameStateManager.change_state(State.GAMEPLAY)
		State.SETTINGS, State.CHARACTER_SELECTION:
			GameStateManager.change_state(State.MENU)
		State.LEVEL_SELECTION:
			GameStateManager.change_state(State.CHARACTER_SELECTION)
		State.MENU:
			Profile.flush()
			get_tree().quit()
