class_name Overlay
extends Control
## Modal panel shown on top of the game while the game state equals `state`.
## Runs while the tree is paused.

var state: int = -1
var body: VBoxContainer


func _init(shown_in_state: int) -> void:
	state = shown_in_state


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	var dim := ColorRect.new()
	dim.color = Color(0, 0, 0, 0.6)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(dim)
	var center := CenterContainer.new()
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(center)
	body = UiKit.vbox(8)
	body.custom_minimum_size = Vector2(260, 0)
	center.add_child(UiKit.panel(body, 12))
	visible = false
	EventBus.game_state_changed.connect(_on_state_changed)


func _on_state_changed(_previous: int, current: int) -> void:
	var should_show := current == state
	if should_show:
		refresh()
	visible = should_show


## Override: rebuild `body` contents each time the overlay opens.
func refresh() -> void:
	pass


func clear_body() -> void:
	for child in body.get_children():
		body.remove_child(child)
		child.queue_free()
