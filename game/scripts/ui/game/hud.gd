class_name Hud
extends Control
## Displays game state received through EventBus; touch controls feed the InputRouter.
## Contains no game logic.

const HUD_ICON_DIR := "res://assets/ui/hud_icons/"
## Touch button caption -> icon file name in HUD_ICON_DIR (text is shown when the file is missing).
const HUD_ICONS := {"HUD_ATTACK": "attack", "HUD_SKILL": "skill", "HUD_DASH": "dash", "HUD_BAG": "bag", "HUD_USE": "use"}

var router: InputRouter

var _health_bar: ProgressBar
var _health_label: Label
var _xp_bar: ProgressBar
var _level_label: Label
var _timer_label: Label
var _gold_label: Label
var _kills_label: Label
var _boss_box: VBoxContainer
var _boss_bar: ProgressBar
var _banner: Label
var _skill_button: TouchButton
var _dash_button: TouchButton
var _kills := 0
var _health_tween: Tween
var _player: Player


func setup(input_router: InputRouter, player: Player) -> void:
	router = input_router
	_player = player
	router.joystick = $Controls/Joystick as VirtualJoystick


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_build_top_bar()
	_build_controls()
	EventBus.player_health_changed.connect(_on_health_changed)
	EventBus.player_xp_changed.connect(_on_xp_changed)
	EventBus.level_time_changed.connect(_on_time_changed)
	EventBus.gold_changed.connect(_on_gold_changed)
	EventBus.enemy_killed.connect(_on_enemy_killed)
	EventBus.boss_spawned.connect(_on_boss_spawned)
	EventBus.boss_health_changed.connect(_on_boss_health_changed)
	EventBus.skill_cooldown_changed.connect(_on_skill_cooldown)
	EventBus.player_leveled_up.connect(func(_level: int) -> void: AudioManager.play_sfx("level_up"))
	_on_gold_changed(Profile.get_gold())


func _process(_delta: float) -> void:
	if _player != null and is_instance_valid(_player):
		var movement := _player.movement
		_dash_button.set_cooldown_ratio(movement.dash_cooldown_left / movement.dash_cooldown if movement.dash_cooldown > 0.0 else 0.0)


func show_banner(text: String) -> void:
	_banner.text = text
	_banner.modulate.a = 1.0
	var tween := create_tween()
	tween.tween_interval(1.6)
	tween.tween_property(_banner, "modulate:a", 0.0, 0.4)


func _build_top_bar() -> void:
	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for side in ["left", "right"]:
		margin.add_theme_constant_override("margin_" + side, 8)
	margin.add_theme_constant_override("margin_top", 6 + int(_safe_top()))
	add_child(margin)
	var column := UiKit.vbox(3)
	column.mouse_filter = Control.MOUSE_FILTER_IGNORE
	margin.add_child(column)

	var row := UiKit.hbox(6)
	var bars := UiKit.vbox(2)
	bars.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_health_bar = UiKit.bar(UiKit.HEALTH, 8)
	_health_bar.step = 0.0
	_health_label = UiKit.label("", 8, UiKit.TEXT, HORIZONTAL_ALIGNMENT_CENTER, false)
	_health_label.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_health_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_health_bar.add_child(_health_label)
	bars.add_child(_health_bar)
	_xp_bar = UiKit.bar(UiKit.XP, 4)
	bars.add_child(_xp_bar)
	row.add_child(bars)
	var pause := UiKit.button("II", func() -> void: router.press(InputSetup.PAUSE), 24)
	pause.custom_minimum_size.x = 28
	var pause_icon := _hud_icon("pause")
	if pause_icon != null:
		pause.text = ""
		pause.icon = pause_icon
		pause.icon_alignment = HORIZONTAL_ALIGNMENT_CENTER
	row.add_child(pause)
	column.add_child(row)

	# Counters on dark pills, like the resource bar of the style target.
	var info := UiKit.hbox(4)
	info.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var level_pill := UiKit.pill(HUD_ICON_DIR + "level.png", Loc.t("HUD_LEVEL") % 1)
	var timer_pill := UiKit.pill(HUD_ICON_DIR + "timer.png", "0:00")
	var kills_pill := UiKit.pill(HUD_ICON_DIR + "kills.png", "0")
	var gold_pill := UiKit.pill(HUD_ICON_DIR + "gold.png", "0")
	_level_label = UiKit.pill_label(level_pill)
	_timer_label = UiKit.pill_label(timer_pill)
	_kills_label = UiKit.pill_label(kills_pill)
	_gold_label = UiKit.pill_label(gold_pill)
	_gold_label.add_theme_color_override("font_color", UiKit.ACCENT)
	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	spacer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for node: Control in [level_pill, timer_pill, spacer, kills_pill, gold_pill]:
		info.add_child(node)
	column.add_child(info)

	_boss_box = UiKit.vbox(1)
	_boss_box.visible = false
	_boss_box.add_child(UiKit.label(Loc.t("HUD_BOSS"), 8, UiKit.DANGER, HORIZONTAL_ALIGNMENT_CENTER))
	_boss_bar = UiKit.bar(UiKit.DANGER, 6)
	_boss_box.add_child(_boss_bar)
	column.add_child(_boss_box)

	# Full width with wrapping: translated banners can be much longer than the English ones.
	_banner = UiKit.title("")
	_banner.set_anchors_and_offsets_preset(Control.PRESET_HCENTER_WIDE)
	_banner.anchor_top = 0.3
	_banner.anchor_bottom = 0.3
	_banner.offset_left = 16
	_banner.offset_right = -16
	_banner.modulate.a = 0.0
	_banner.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_banner)


func _build_controls() -> void:
	var controls := Control.new()
	controls.name = "Controls"
	controls.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	controls.mouse_filter = Control.MOUSE_FILTER_IGNORE
	# Touch input must stop while the game is paused (overlays handle input then).
	controls.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child(controls)

	var joystick := VirtualJoystick.new()
	joystick.name = "Joystick"
	joystick.anchor_left = 0.0
	joystick.anchor_right = 0.55
	joystick.anchor_top = 0.55
	joystick.anchor_bottom = 1.0
	controls.add_child(joystick)

	var attack := _action_button(controls, "HUD_ATTACK", 52, Vector2(-62, -78), UiKit.DANGER)
	attack.pressed.connect(func() -> void: router.press(InputSetup.ATTACK))
	_skill_button = _action_button(controls, "HUD_SKILL", 42, Vector2(-120, -58), UiKit.ACCENT)
	_skill_button.pressed.connect(func() -> void: router.press(InputSetup.SKILL))
	_dash_button = _action_button(controls, "HUD_DASH", 38, Vector2(-54, -128), UiKit.XP)
	_dash_button.pressed.connect(func() -> void: router.press(InputSetup.DASH))
	var bag := _action_button(controls, "HUD_BAG", 30, Vector2(-110, -112), UiKit.TEXT_DIM)
	bag.pressed.connect(func() -> void: router.press(InputSetup.INVENTORY))
	var interact := _action_button(controls, "HUD_USE", 30, Vector2(-150, -100), Color("#7a9a5a"))
	interact.pressed.connect(func() -> void: router.press(InputSetup.INTERACT))


func _action_button(parent: Control, text: String, diameter: float, offset_from_bottom_right: Vector2, tint: Color) -> TouchButton:
	var button := TouchButton.new()
	button.label = Loc.t(text)
	button.icon = _hud_icon(HUD_ICONS.get(text, ""))
	button.color = tint
	button.anchor_left = 1.0
	button.anchor_right = 1.0
	button.anchor_top = 1.0
	button.anchor_bottom = 1.0
	button.offset_left = offset_from_bottom_right.x - diameter * 0.5
	button.offset_top = offset_from_bottom_right.y - diameter * 0.5
	button.offset_right = offset_from_bottom_right.x + diameter * 0.5
	button.offset_bottom = offset_from_bottom_right.y + diameter * 0.5
	parent.add_child(button)
	return button


func _hud_icon(icon_name: String) -> Texture2D:
	var path := HUD_ICON_DIR + icon_name + ".png"
	return load(path) if not icon_name.is_empty() and ResourceLoader.exists(path) else null


func _on_health_changed(current: int, maximum: int) -> void:
	_health_bar.max_value = maximum
	if _health_tween != null:
		_health_tween.kill()
	_health_tween = create_tween()
	_health_tween.tween_property(_health_bar, "value", float(current), 0.2).set_ease(Tween.EASE_OUT)
	_health_label.text = "%d / %d" % [current, maximum]


func _on_xp_changed(level: int, xp_into_level: int, xp_for_next: int) -> void:
	_level_label.text = Loc.t("HUD_LEVEL") % level
	_xp_bar.max_value = maxi(1, xp_for_next)
	_xp_bar.value = xp_into_level


func _on_time_changed(elapsed: float, duration: float) -> void:
	_timer_label.text = UiKit.format_time(duration - elapsed) if elapsed < duration else Loc.t("HUD_BOSS_TIMER")


func _on_gold_changed(total: int) -> void:
	_gold_label.text = str(total)


func _on_enemy_killed(_enemy_id: String, _position: Vector2, _xp: int, _loot: String, is_boss: bool) -> void:
	_kills += 1
	_kills_label.text = str(_kills)
	if is_boss:
		_boss_box.visible = false


func _on_boss_spawned(boss: Node2D) -> void:
	_boss_box.visible = true
	var enemy := boss as Enemy
	if enemy != null:
		show_banner(Loc.t("HUD_BOSS_AWAKENS") % Loc.name_of(enemy.definition))


func _on_boss_health_changed(current: int, maximum: int) -> void:
	_boss_bar.max_value = maximum
	_boss_bar.value = current


func _on_skill_cooldown(_skill_id: String, remaining: float, total: float) -> void:
	_skill_button.set_cooldown_ratio(remaining / total if total > 0.0 else 0.0)


func _safe_top() -> float:
	var safe_area := DisplayServer.get_display_safe_area()
	var screen := DisplayServer.screen_get_size()
	if screen.y <= 0:
		return 0.0
	return safe_area.position.y * get_viewport_rect().size.y / float(screen.y)
