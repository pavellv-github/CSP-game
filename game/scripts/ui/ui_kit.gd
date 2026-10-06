class_name UiKit
extends RefCounted
## Shared theme and small widget factories. UI scripts only build layout and forward
## user actions to game systems; they contain no game rules.

const BG := Color(0.0784, 0.0667, 0.098)
const PANEL := Color(0.14, 0.12, 0.18, 0.96)
const PANEL_BORDER := Color(0.42, 0.36, 0.5)
const ACCENT := Color(0.95, 0.76, 0.3)
const TEXT := Color(0.94, 0.92, 0.96)
const TEXT_DIM := Color(0.65, 0.62, 0.72)
const DANGER := Color(0.85, 0.3, 0.35)
const HEALTH := Color(0.85, 0.27, 0.32)
const XP := Color(0.3, 0.7, 0.99)


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
	theme.set_stylebox("normal", "Button", _box(Color(0.22, 0.19, 0.28), PANEL_BORDER))
	theme.set_stylebox("hover", "Button", _box(Color(0.28, 0.24, 0.36), ACCENT))
	theme.set_stylebox("pressed", "Button", _box(Color(0.16, 0.14, 0.2), ACCENT))
	theme.set_stylebox("disabled", "Button", _box(Color(0.16, 0.15, 0.19), Color(0.28, 0.26, 0.32)))
	theme.set_stylebox("focus", "Button", StyleBoxEmpty.new())
	theme.set_stylebox("panel", "PanelContainer", _box(PANEL, PANEL_BORDER))
	theme.set_stylebox("panel", "Panel", _box(PANEL, PANEL_BORDER))
	var bar_bg := _box(Color(0.1, 0.08, 0.12), Color(0.05, 0.04, 0.06))
	bar_bg.set_content_margin_all(0)
	theme.set_stylebox("background", "ProgressBar", bar_bg)
	var bar_fill := _box(HEALTH, Color(0, 0, 0, 0))
	bar_fill.set_border_width_all(0)
	bar_fill.set_content_margin_all(0)
	theme.set_stylebox("fill", "ProgressBar", bar_fill)
	theme.set_color("font_color", "CheckButton", TEXT)
	return theme


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
	node.add_theme_color_override("font_outline_color", Color(0.1, 0.06, 0.12))
	node.add_theme_constant_override("outline_size", 4)
	return node


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


## Sprite sheet first frame as an icon.
static func sprite_icon(path: String, frames: int, size: float = 32.0) -> TextureRect:
	var node := TextureRect.new()
	if ResourceLoader.exists(path):
		var atlas := AtlasTexture.new()
		var texture: Texture2D = load(path)
		atlas.atlas = texture
		atlas.region = Rect2(0, 0, texture.get_width() / maxi(1, frames), texture.get_height())
		node.texture = atlas
	node.custom_minimum_size = Vector2(size, size)
	node.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	node.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	return node


static func format_time(seconds: float) -> String:
	var total := maxi(0, int(ceil(seconds)))
	return "%d:%02d" % [total / 60, total % 60]
