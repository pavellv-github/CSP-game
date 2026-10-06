extends Screen

const State := preload("res://scripts/core/game_state_manager.gd").State
const BANNER := "res://assets/ui/menu/keyart_banner.png"
const BANNER_FADE := 56.0


func _ready() -> void:
	super._ready()
	_add_banner()


## Key art across the top of the screen, fading into the background behind the title.
func _add_banner() -> void:
	if not ResourceLoader.exists(BANNER):
		return
	var texture: Texture2D = load(BANNER)
	var banner := TextureRect.new()
	banner.texture = texture
	banner.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	banner.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	banner.mouse_filter = Control.MOUSE_FILTER_IGNORE
	banner.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	banner.offset_bottom = texture.get_height()
	add_child(banner)
	move_child(banner, 1) # above the background colour, below the menu content

	var gradient := Gradient.new()
	gradient.set_color(0, Color(UiKit.BG, 0.0))
	gradient.set_color(1, UiKit.BG)
	var fade_texture := GradientTexture2D.new()
	fade_texture.gradient = gradient
	fade_texture.fill_from = Vector2(0, 0)
	fade_texture.fill_to = Vector2(0, 1)
	var fade := TextureRect.new()
	fade.texture = fade_texture
	fade.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	fade.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	fade.offset_top = texture.get_height() - BANNER_FADE
	fade.offset_bottom = texture.get_height() + 1
	add_child(fade)
	move_child(fade, 2)


func _build() -> void:
	var spacer := Control.new()
	spacer.custom_minimum_size = Vector2(0, 150)
	content.add_child(spacer)
	content.add_child(UiKit.title(Loc.t("GAME_TITLE")))
	content.add_child(UiKit.label(Loc.t("COMMON_GOLD") % Profile.get_gold(), 10, UiKit.ACCENT, HORIZONTAL_ALIGNMENT_CENTER))
	var spacer2 := Control.new()
	spacer2.custom_minimum_size = Vector2(0, 40)
	content.add_child(spacer2)
	content.add_child(UiKit.button(Loc.t("MENU_PLAY"), func() -> void: GameStateManager.change_state(State.CHARACTER_SELECTION), 36))
	content.add_child(UiKit.button(Loc.t("MENU_SETTINGS"), func() -> void: GameStateManager.change_state(State.SETTINGS)))
	if OS.has_feature("pc"):
		content.add_child(UiKit.button(Loc.t("MENU_QUIT"), func() -> void:
			Profile.flush()
			get_tree().quit()))
	var version := Loc.t("MENU_VERSION") % [Services.config.game_version(), Content.content_version]
	content.add_child(UiKit.label(version, 8, UiKit.TEXT_DIM, HORIZONTAL_ALIGNMENT_CENTER))
