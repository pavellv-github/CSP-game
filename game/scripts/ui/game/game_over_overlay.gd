class_name GameOverOverlay
extends Overlay
## Scene "GameOver".

const State := preload("res://scripts/core/game_state_manager.gd").State


func _init() -> void:
	super(State.GAME_OVER)


func refresh() -> void:
	clear_body()
	var summary := GameManager.last_run_summary
	body.add_child(UiKit.title("Defeated"))
	body.add_child(UiKit.label("Survived %s · Kills %d · Level %d" % [
		UiKit.format_time(float(summary.get("time", 0.0))), int(summary.get("kills", 0)), int(summary.get("player_level", 1))],
		10, UiKit.TEXT, HORIZONTAL_ALIGNMENT_CENTER))
	body.add_child(UiKit.label("Gold and items you picked up are kept.", 8, UiKit.TEXT_DIM, HORIZONTAL_ALIGNMENT_CENTER))
	body.add_child(UiKit.button("Retry", func() -> void: GameManager.retry(), 34))
	body.add_child(UiKit.button("Levels", func() -> void: GameStateManager.change_state(State.LEVEL_SELECTION)))
	body.add_child(UiKit.button("Main menu", func() -> void: GameStateManager.change_state(State.MENU)))
