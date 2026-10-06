class_name TouchButton
extends Control
## Round on-screen action button driven by raw touch events (works while the joystick is held).
## Optionally shows a cooldown sweep.

signal pressed

@export var label: String = ""
@export var color: Color = Color(1, 1, 1)
## Optional glyph drawn instead of the text label.
@export var icon: Texture2D

var cooldown_ratio: float = 0.0
var _touch_index: int = -1


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func set_cooldown_ratio(ratio: float) -> void:
	cooldown_ratio = clampf(ratio, 0.0, 1.0)
	queue_redraw()


func _input(event: InputEvent) -> void:
	if not is_visible_in_tree() or not event is InputEventScreenTouch:
		return
	var touch := event as InputEventScreenTouch
	var center := global_position + size * 0.5
	var hit := touch.position.distance_to(center) <= size.x * 0.5 + 4.0
	if touch.pressed and hit and _touch_index == -1:
		_touch_index = touch.index
		pressed.emit()
		queue_redraw()
		get_viewport().set_input_as_handled()
	elif not touch.pressed and touch.index == _touch_index:
		_touch_index = -1
		queue_redraw()


func _draw() -> void:
	var center := size * 0.5
	var r := size.x * 0.5
	var held := _touch_index != -1
	draw_circle(center, r, Color(color, 0.45 if held else 0.28))
	draw_arc(center, r, 0.0, TAU, 32, Color(color, 0.85), 1.0)
	if cooldown_ratio > 0.0:
		var points := PackedVector2Array([center])
		var steps := 24
		for i in steps + 1:
			var angle := -PI * 0.5 + TAU * cooldown_ratio * float(i) / steps
			points.append(center + Vector2.from_angle(angle) * r)
		draw_colored_polygon(points, Color(0, 0, 0, 0.5))
	if icon != null:
		draw_texture(icon, (center - icon.get_size() * 0.5).floor())
	elif not label.is_empty():
		var font := get_theme_default_font()
		var font_size := 8
		var text_size := font.get_string_size(label, HORIZONTAL_ALIGNMENT_CENTER, -1, font_size)
		draw_string(font, center - Vector2(text_size.x * 0.5, -text_size.y * 0.3), label, HORIZONTAL_ALIGNMENT_CENTER, -1, font_size, Color.WHITE)
