class_name InputRouter
extends Node
## Collects input from all devices (touch controls, keyboard, gamepad) into one InputCommand
## per physics frame and hands it to the PlayerController.

signal pause_requested
signal inventory_requested

var controller: PlayerController
var joystick: VirtualJoystick
## Touch buttons write here; flags are consumed on the next physics frame.
var _pending: Dictionary = {}


func press(action: StringName) -> void:
	_pending[action] = true


func _physics_process(_delta: float) -> void:
	var command := InputCommand.new()
	var keyboard := Input.get_vector(InputSetup.MOVE_LEFT, InputSetup.MOVE_RIGHT, InputSetup.MOVE_UP, InputSetup.MOVE_DOWN)
	var touch := joystick.get_vector() if joystick != null else Vector2.ZERO
	command.move = touch if touch != Vector2.ZERO else keyboard
	command.attack = _consume(InputSetup.ATTACK) or Input.is_action_just_pressed(InputSetup.ATTACK)
	command.skill = _consume(InputSetup.SKILL) or Input.is_action_just_pressed(InputSetup.SKILL)
	command.dash = _consume(InputSetup.DASH) or Input.is_action_just_pressed(InputSetup.DASH)
	command.interact = _consume(InputSetup.INTERACT) or Input.is_action_just_pressed(InputSetup.INTERACT)
	command.inventory = _consume(InputSetup.INVENTORY) or Input.is_action_just_pressed(InputSetup.INVENTORY)
	command.pause = _consume(InputSetup.PAUSE) or Input.is_action_just_pressed(InputSetup.PAUSE)
	if controller != null:
		controller.apply_command(command)
	if command.pause:
		pause_requested.emit()
	elif command.inventory:
		inventory_requested.emit()


func _consume(action: StringName) -> bool:
	return bool(_pending.get(action, false)) and _pending.erase(action)
