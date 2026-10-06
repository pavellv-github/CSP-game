class_name Screen
extends Control
## Base for full-screen menus: background, safe-area margins and a scrollable content column.

var content: VBoxContainer


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var background := ColorRect.new()
	background.color = UiKit.BG
	background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(background)
	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var safe := _safe_margins()
	margin.add_theme_constant_override("margin_left", 16 + int(safe.x))
	margin.add_theme_constant_override("margin_right", 16 + int(safe.x))
	margin.add_theme_constant_override("margin_top", 16 + int(safe.y))
	margin.add_theme_constant_override("margin_bottom", 16)
	add_child(margin)
	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	margin.add_child(scroll)
	content = UiKit.vbox(8)
	content.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	content.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.add_child(content)
	_build()


## Override: fill `content`.
func _build() -> void:
	pass


## Clears and rebuilds the content (after a purchase, selection, etc.).
func rebuild() -> void:
	for child in content.get_children():
		child.queue_free()
	_build()


## Notch / status bar insets converted to viewport pixels.
func _safe_margins() -> Vector2:
	var safe_area := DisplayServer.get_display_safe_area()
	var screen := DisplayServer.screen_get_size()
	if screen.y <= 0 or safe_area.size.y <= 0:
		return Vector2.ZERO
	var scale_factor := get_viewport_rect().size.y / float(screen.y)
	return Vector2(safe_area.position.x * scale_factor, safe_area.position.y * scale_factor)
