class_name PlayerController
extends Node
## Turns InputCommands into player actions.

var player: Player


func setup(owner_player: Player) -> void:
	player = owner_player


func apply_command(command: InputCommand) -> void:
	if player == null or not player.is_alive():
		return
	player.movement.move_input = command.move
	if command.attack:
		player.combat.manual_attack(player.movement.facing)
	if command.skill:
		player.skills.use(0)
	if command.dash:
		player.movement.try_dash()
	if command.interact:
		EventBus.interact_requested.emit(player.global_position)
