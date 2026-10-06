extends Screen

const State := preload("res://scripts/core/game_state_manager.gd").State


func _build() -> void:
	content.alignment = BoxContainer.ALIGNMENT_CENTER
	var spacer := Control.new()
	spacer.custom_minimum_size = Vector2(0, 80)
	content.add_child(spacer)
	content.add_child(UiKit.title("Pixel Fantasy\nSurvival"))
	var hero := UiKit.sprite_icon("res://assets/sprites/characters/warrior.png", 2, 64)
	content.add_child(hero)
	content.add_child(UiKit.label("Gold: %d" % Profile.get_gold(), 10, UiKit.ACCENT, HORIZONTAL_ALIGNMENT_CENTER))
	var spacer2 := Control.new()
	spacer2.custom_minimum_size = Vector2(0, 24)
	content.add_child(spacer2)
	content.add_child(UiKit.button("Play", func() -> void: GameStateManager.change_state(State.CHARACTER_SELECTION), 36))
	content.add_child(UiKit.button("Settings", func() -> void: GameStateManager.change_state(State.SETTINGS)))
	if OS.has_feature("pc"):
		content.add_child(UiKit.button("Quit", func() -> void:
			Profile.flush()
			get_tree().quit()))
	var version := "v%s · content %d" % [Services.config.game_version(), Content.content_version]
	content.add_child(UiKit.label(version, 8, UiKit.TEXT_DIM, HORIZONTAL_ALIGNMENT_CENTER))
