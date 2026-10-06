class_name RangedAI
extends EnemyAI
## Keeps its distance and shoots projectiles when the player is in range.

const PREFERRED_RANGE_RATIO := 0.75
const RETREAT_RANGE_RATIO := 0.45


func physics_step(_delta: float) -> void:
	if not enemy.has_target():
		enemy.velocity = Vector2.ZERO
		return
	var attack_range := enemy.definition.attack_range
	var distance := enemy.distance_to_target()
	if distance > attack_range * PREFERRED_RANGE_RATIO:
		move_towards_target()
	elif distance < attack_range * RETREAT_RANGE_RATIO:
		move_towards_target(-0.8)
	else:
		enemy.velocity = Vector2.ZERO
	if distance <= attack_range and enemy.can_attack():
		enemy.shoot(enemy.direction_to_target())
