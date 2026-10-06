class_name LevelCompleteOverlay
extends Overlay
## Scene "LevelComplete": rewards summary, then on to character progression / next level.

const State := preload("res://scripts/core/game_state_manager.gd").State


func _init() -> void:
	super(State.LEVEL_COMPLETE)


func refresh() -> void:
	clear_body()
	var summary := GameManager.last_run_summary
	body.add_child(UiKit.plaque(Loc.t("VICTORY_TITLE")))
	body.add_child(UiKit.label(Loc.t("VICTORY_SUMMARY") % [
		UiKit.format_time(float(summary.get("time", 0.0))), int(summary.get("kills", 0)), int(summary.get("player_level", 1))],
		10, UiKit.TEXT, HORIZONTAL_ALIGNMENT_CENTER))
	body.add_child(UiKit.label(Loc.t("VICTORY_REWARDS"), 12, UiKit.ACCENT))
	for reward in GameManager.last_rewards:
		var item := Content.get_item(str(reward["item_id"]))
		if item == null:
			continue
		var row := UiKit.hbox(6)
		row.add_child(UiKit.icon(item.icon, 16))
		var reward_label := UiKit.label(Loc.t("COMMON_ITEM_QUANTITY") % [Loc.name_of(item), int(reward["quantity"])])
		reward_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(reward_label)
		body.add_child(row)
	body.add_child(UiKit.button(Loc.t("VICTORY_TRAIN"), func() -> void: GameStateManager.change_state(State.CHARACTER_SELECTION), 30))
	body.add_child(UiKit.button(Loc.t("VICTORY_NEXT"), func() -> void: GameStateManager.change_state(State.LEVEL_SELECTION), 34))
