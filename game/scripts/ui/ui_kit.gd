class_name UiKit
extends RefCounted
## Shared theme and small widget factories. UI scripts only build layout and forward
## user actions to game systems; they contain no game rules.

## Style v2 (docs/decisions/2026-10-06-art-style-v2.md, target: docs/art/reference/style_target_base.png):
## warm dark rounded panels with a light rim, square dark buttons, parchment plaques with dark text.
const BG := Color("#241d18")
const PANEL := Color("#3a312af2")
const PANEL_BORDER := Color("#8f7d66")
const OUTLINE := Color("#2a1d16")
const ACCENT := Color("#f2c14e")
const TEXT := Color("#f6eddc")
const TEXT_DIM := Color("#bcab92")
const DANGER := Color("#c8513f")
const HEALTH := Color("#c8513f")
const XP := Color("#5aa0d8")
const BUTTON := Color("#4a4038")
const BUTTON_HOVER := Color("#5a4e44")
const BUTTON_PRESSED := Color("#332b25")
const BUTTON_DISABLED := Color("#2f2925")
const PARCHMENT := Color("#ecdcb4")
const PARCHMENT_TEXT := Color("#2a1d16")
const CORNER_RADIUS := 3


static var _shared_theme: Theme


## One theme instance for the whole game. Assigned to the root window and to UI roots
## under CanvasLayers (theme inheritance does not cross non-Control nodes).
static func shared_theme() -> Theme:
	if _shared_theme == null:
		_shared_theme = build_theme()
	return _shared_theme


static func build_theme() -> Theme:
	var theme := Theme.new()
	theme.default_font_size = 10
	theme.set_color("font_color", "Label", TEXT)
	theme.set_color("font_color", "Button", TEXT)
	theme.set_color("font_hover_color", "Button", ACCENT)
	theme.set_color("font_pressed_color", "Button", ACCENT)
	theme.set_color("font_disabled_color", "Button", TEXT_DIM)
	theme.set_stylebox("normal", "Button", _framed_box(BUTTON, PANEL_BORDER))
	theme.set_stylebox("hover", "Button", _framed_box(BUTTON_HOVER, ACCENT))
	theme.set_stylebox("pressed", "Button", _framed_box(BUTTON_PRESSED, ACCENT))
	theme.set_stylebox("disabled", "Button", _framed_box(BUTTON_DISABLED, Color("#4a4038")))
	theme.set_stylebox("focus", "Button", StyleBoxEmpty.new())
	theme.set_stylebox("panel", "PanelContainer", _framed_box(PANEL, PANEL_BORDER))
	theme.set_stylebox("panel", "Panel", _framed_box(PANEL, PANEL_BORDER))
	var bar_bg := _box(Color("#1c1612"), OUTLINE)
	bar_bg.set_content_margin_all(0)
	theme.set_stylebox("background", "ProgressBar", bar_bg)
	var bar_fill := _box(HEALTH, Color(0, 0, 0, 0))
	bar_fill.set_border_width_all(0)
	bar_fill.set_content_margin_all(0)
	theme.set_stylebox("fill", "ProgressBar", bar_fill)
	theme.set_color("font_color", "CheckButton", TEXT)
	theme.set_color("font_hover_color", "CheckButton", ACCENT)
	theme.set_color("font_color", "CheckBox", TEXT)
	return theme


## Rounded plate with a light rim and a dark outer edge (drawn as an offset shadow), like the
## panels and buttons of the style target.
static func _framed_box(fill: Color, border: Color) -> StyleBoxFlat:
	var box := _box(fill, border)
	box.set_corner_radius_all(CORNER_RADIUS)
	box.shadow_color = Color(OUTLINE, 0.85)
	box.shadow_size = 1
	box.shadow_offset = Vector2(0, 1)
	return box


## Parchment signboard (dark text, dark border), like the building plaques of the style target.
static func plaque_box() -> StyleBoxFlat:
	var box := _box(PARCHMENT, OUTLINE)
	box.set_corner_radius_all(2)
	box.content_margin_left = 10
	box.content_margin_right = 10
	box.content_margin_top = 3
	box.content_margin_bottom = 3
	box.shadow_color = Color(OUTLINE, 0.6)
	box.shadow_size = 1
	box.shadow_offset = Vector2(0, 2)
	return box


## Dark rounded "pill" for HUD counters (icon + number), like the resource bar of the style target.
static func pill_box() -> StyleBoxFlat:
	var box := _framed_box(Color("#2f2823e6"), Color("#6b5d4e"))
	box.content_margin_left = 4
	box.content_margin_right = 6
	box.content_margin_top = 1
	box.content_margin_bottom = 1
	return box


static func _box(fill: Color, border: Color) -> StyleBoxFlat:
	var box := StyleBoxFlat.new()
	box.bg_color = fill
	box.border_color = border
	box.set_border_width_all(1)
	box.set_content_margin_all(6)
	box.anti_aliasing = false
	return box


static func label(text: String, font_size: int = 10, color: Color = TEXT, align: HorizontalAlignment = HORIZONTAL_ALIGNMENT_LEFT,
		wrap: bool = true) -> Label:
	var node := Label.new()
	node.text = text
	node.horizontal_alignment = align
	node.add_theme_font_size_override("font_size", font_size)
	node.add_theme_color_override("font_color", color)
	node.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART if wrap else TextServer.AUTOWRAP_OFF
	return node


static func title(text: String) -> Label:
	var node := label(text, 18, ACCENT, HORIZONTAL_ALIGNMENT_CENTER)
	node.add_theme_color_override("font_outline_color", OUTLINE)
	node.add_theme_constant_override("outline_size", 4)
	return node


## Screen / dialog heading on a parchment plaque, centered.
static func plaque(text: String, font_size: int = 14) -> PanelContainer:
	var node := PanelContainer.new()
	node.add_theme_stylebox_override("panel", plaque_box())
	node.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	var caption := label(text, font_size, PARCHMENT_TEXT, HORIZONTAL_ALIGNMENT_CENTER, false)
	node.add_child(caption)
	return node


## HUD counter: icon + value on a dark pill. Returns the pill; the value label is its last child.
static func pill(icon_path: String, value: String) -> PanelContainer:
	var node := PanelContainer.new()
	node.add_theme_stylebox_override("panel", pill_box())
	node.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var row := hbox(3)
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	if ResourceLoader.exists(icon_path):
		row.add_child(icon(icon_path, 16))
	var value_label := label(value, 9, TEXT, HORIZONTAL_ALIGNMENT_LEFT, false)
	value_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	row.add_child(value_label)
	node.add_child(row)
	return node


static func pill_label(pill_node: PanelContainer) -> Label:
	var row := pill_node.get_child(0)
	return row.get_child(row.get_child_count() - 1) as Label


static func button(text: String, on_pressed: Callable, min_height: float = 28.0) -> Button:
	var node := Button.new()
	node.text = text
	node.custom_minimum_size = Vector2(0, min_height)
	node.pressed.connect(func() -> void:
		AudioManager.play_sfx("ui_click")
		on_pressed.call())
	return node


static func bar(fill_color: Color, height: float = 6.0) -> ProgressBar:
	var node := ProgressBar.new()
	node.show_percentage = false
	node.custom_minimum_size = Vector2(0, height)
	var fill := StyleBoxFlat.new()
	fill.bg_color = fill_color
	node.add_theme_stylebox_override("fill", fill)
	return node


static func vbox(separation: int = 6) -> VBoxContainer:
	var node := VBoxContainer.new()
	node.add_theme_constant_override("separation", separation)
	return node


static func hbox(separation: int = 6) -> HBoxContainer:
	var node := HBoxContainer.new()
	node.add_theme_constant_override("separation", separation)
	return node


static func panel(content: Control, padding: int = 8) -> PanelContainer:
	var node := PanelContainer.new()
	var margin := MarginContainer.new()
	for side in ["left", "right", "top", "bottom"]:
		margin.add_theme_constant_override("margin_" + side, padding)
	margin.add_child(content)
	node.add_child(margin)
	return node


static func icon(path: String, size: float = 16.0) -> TextureRect:
	var node := TextureRect.new()
	if ResourceLoader.exists(path):
		node.texture = load(path)
	node.custom_minimum_size = Vector2(size, size)
	node.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	node.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	return node


## First idle frame of a sprite sheet as an icon.
static func sprite_icon(sheet: SpriteSheet, size: float = 32.0) -> TextureRect:
	var node := TextureRect.new()
	if ResourceLoader.exists(sheet.texture_path):
		var texture: Texture2D = load(sheet.texture_path)
		var frame_size := sheet.resolve_frame_size(texture)
		var row := int(sheet.animations.get("idle", {"row": 0})["row"])
		var atlas := AtlasTexture.new()
		atlas.atlas = texture
		atlas.region = Rect2(0, row * frame_size.y, frame_size.x, frame_size.y)
		node.texture = atlas
	node.custom_minimum_size = Vector2(size, size)
	node.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	node.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	return node


## Menu illustration (portrait, banner) shown at its native pixel size.
static func illustration(path: String, min_size: Vector2 = Vector2.ZERO) -> TextureRect:
	var node := TextureRect.new()
	if ResourceLoader.exists(path):
		node.texture = load(path)
	node.custom_minimum_size = min_size if min_size != Vector2.ZERO or node.texture == null else node.texture.get_size()
	node.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	node.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	node.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return node


static func format_time(seconds: float) -> String:
	var total := maxi(0, int(ceil(seconds)))
	return "%d:%02d" % [total / 60, total % 60]
