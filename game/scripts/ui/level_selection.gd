extends Screen

const State := preload("res://scripts/core/game_state_manager.gd").State


func _build() -> void:
	content.add_child(UiKit.title("Levels"))
	var character := Content.get_character(Profile.get_selected_character_id())
	if character != null:
		content.add_child(UiKit.label("Hero: %s" % character.name, 10, UiKit.TEXT_DIM, HORIZONTAL_ALIGNMENT_CENTER))
	for definition in Content.levels.get_all():
		content.add_child(_level_card(definition as LevelDefinition))
	var buttons := UiKit.hbox()
	var back := UiKit.button("Hero", func() -> void: GameStateManager.change_state(State.CHARACTER_SELECTION))
	back.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var menu := UiKit.button("Menu", func() -> void: GameStateManager.change_state(State.MENU))
	menu.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	buttons.add_child(back)
	buttons.add_child(menu)
	content.add_child(buttons)


func _level_card(level: LevelDefinition) -> Control:
	var unlocked := Profile.is_level_unlocked(level.id)
	var completed := Profile.is_level_completed(level.id)
	var row := UiKit.hbox(8)
	var info := UiKit.vbox(2)
	info.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var status := "  - cleared" if completed else ""
	info.add_child(UiKit.label(level.name + status, 12, UiKit.TEXT if unlocked else UiKit.TEXT_DIM))
	info.add_child(UiKit.label("Difficulty %d · %s · boss" % [level.difficulty, UiKit.format_time(level.duration)], 8, UiKit.TEXT_DIM))
	row.add_child(info)
	var play := UiKit.button("Play" if unlocked else "Locked", func() -> void: GameManager.start_run(level.id))
	play.disabled = not unlocked
	play.custom_minimum_size.x = 64
	row.add_child(play)
	return UiKit.panel(row, 6)
