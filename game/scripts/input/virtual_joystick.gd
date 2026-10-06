class_name VirtualJoystick
extends Control
## Floating joystick: appears where the finger touches inside this control's rect.
## Uses raw touch events so it works together with other touch buttons (multitouch).

@export var radius: float = 26.0
@export var dead_zone: float = 0.15

var _touch_index: int = -1
var _origin: Vector2 = Vector2.ZERO
var _knob: Vector2 = Vector2.ZERO
var _rest_position: Vector2 = Vector2.ZERO


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_rest_position = Vector2(size.x * 0.5, size.y - radius - 24.0)
	resized.connect(func() -> void: _rest_position = Vector2(size.x * 0.5, size.y - radius - 24.0))


func get_vector() -> Vector2:
	if _touch_index == -1:
		return Vector2.ZERO
	var vector := _knob / radius
	return Vector2.ZERO if vector.length() < dead_zone else vector.limit_length(1.0)


func release() -> void:
	_touch_index = -1
	_knob = Vector2.ZERO
	queue_redraw()


func _input(event: InputEvent) -> void:
	if not is_visible_in_tree():
		return
	if event is InputEventScreenTouch:
		var touch := event as InputEventScreenTouch
		if touch.pressed and _touch_index == -1 and get_global_rect().has_point(touch.position):
			_touch_index = touch.index
			_origin = touch.position - global_position
			_knob = Vector2.ZERO
			queue_redraw()
			get_viewport().set_input_as_handled()
		elif not touch.pressed and touch.index == _touch_index:
			release()
	elif event is InputEventScreenDrag:
		var drag := event as InputEventScreenDrag
		if drag.index == _touch_index:
			_knob = (drag.position - global_position - _origin).limit_length(radius)
			queue_redraw()
			get_viewport().set_input_as_handled()


func _draw() -> void:
	var center := _origin if _touch_index != -1 else _rest_position
	var alpha := 0.55 if _touch_index != -1 else 0.25
	draw_circle(center, radius, Color(1, 1, 1, alpha * 0.35))
	draw_arc(center, radius, 0.0, TAU, 32, Color(1, 1, 1, alpha), 1.0)
	draw_circle(center + _knob, radius * 0.42, Color(1, 1, 1, alpha + 0.2))
