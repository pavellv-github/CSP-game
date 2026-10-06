class_name GameOverOverlay
extends Overlay
## Scene "GameOver".

const State := preload("res://scripts/core/game_state_manager.gd").State


func _init() -> void:
	super(State.GAME_OVER)


func refresh() -> void:
	clear_body()
	var summary := GameManager.last_run_summary
	body.add_child(UiKit.title(Loc.t("DEFEAT_TITLE")))
	body.add_child(UiKit.label(Loc.t("DEFEAT_SUMMARY") % [
		UiKit.format_time(float(summary.get("time", 0.0))), int(summary.get("kills", 0)), int(summary.get("player_level", 1))],
		10, UiKit.TEXT, HORIZONTAL_ALIGNMENT_CENTER))
	body.add_child(UiKit.label(Loc.t("DEFEAT_KEPT"), 8, UiKit.TEXT_DIM, HORIZONTAL_ALIGNMENT_CENTER))
	body.add_child(UiKit.button(Loc.t("DEFEAT_RETRY"), func() -> void: GameManager.retry(), 34))
	body.add_child(UiKit.button(Loc.t("DEFEAT_LEVELS"), func() -> void: GameStateManager.change_state(State.LEVEL_SELECTION)))
	body.add_child(UiKit.button(Loc.t("COMMON_MAIN_MENU"), func() -> void: GameStateManager.change_state(State.MENU)))
