class_name EnemyAI
extends Node
## Base behaviour. AI is separate from enemy types: any EnemyDefinition picks one by `ai_type`.

var enemy: Enemy


func setup(owner_enemy: Enemy) -> void:
	enemy = owner_enemy


## Sets enemy.velocity and triggers attacks. Movement itself is done by Enemy.
func physics_step(_delta: float) -> void:
	enemy.velocity = Vector2.ZERO


func on_damaged() -> void:
	pass


func move_towards_target(speed_scale: float = 1.0) -> void:
	enemy.velocity = enemy.direction_to_target() * enemy.move_speed * speed_scale
