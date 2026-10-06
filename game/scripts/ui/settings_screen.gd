extends Screen

const State := preload("res://scripts/core/game_state_manager.gd").State

var _reset_armed := false


func _build() -> void:
	content.add_child(UiKit.title(Loc.t("SETTINGS_TITLE")))
	content.add_child(_slider(Loc.t("SETTINGS_MUSIC"), "music_volume"))
	content.add_child(_slider(Loc.t("SETTINGS_SOUND"), "sfx_volume"))
	content.add_child(_toggle(Loc.t("SETTINGS_AUTO_ATTACK"), "auto_attack"))
	content.add_child(_toggle(Loc.t("SETTINGS_VIBRATION"), "vibration"))
	var reset := UiKit.button(Loc.t("SETTINGS_RESET"), func() -> void: pass)
	reset.pressed.connect(func() -> void:
		if _reset_armed:
			Profile.reset_progress()
			_reset_armed = false
			rebuild()
		else:
			_reset_armed = true
			reset.text = Loc.t("SETTINGS_RESET_CONFIRM")
			reset.add_theme_color_override("font_color", UiKit.DANGER))
	content.add_child(reset)
	content.add_child(UiKit.button(Loc.t("COMMON_BACK"), func() -> void:
		Profile.flush()
		GameStateManager.change_state(State.MENU)))


func _slider(caption: String, key: String) -> Control:
	var row := UiKit.vbox(2)
	row.add_child(UiKit.label(caption))
	var slider := HSlider.new()
	slider.min_value = 0.0
	slider.max_value = 1.0
	slider.step = 0.05
	slider.value = float(Profile.get_setting(key, 1.0))
	slider.custom_minimum_size = Vector2(0, 20)
	slider.value_changed.connect(func(value: float) -> void: Profile.set_setting(key, value))
	row.add_child(slider)
	return row


func _toggle(caption: String, key: String) -> Control:
	var toggle := CheckButton.new()
	toggle.text = caption
	toggle.button_pressed = bool(Profile.get_setting(key, true))
	toggle.toggled.connect(func(on: bool) -> void: Profile.set_setting(key, on))
	return toggle
