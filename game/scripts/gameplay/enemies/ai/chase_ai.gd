class_name ChaseAI
extends EnemyAI
## Runs straight at the player and bites on contact.


func physics_step(_delta: float) -> void:
	if not enemy.has_target():
		enemy.velocity = Vector2.ZERO
		return
	move_towards_target()
	if enemy.distance_to_target() <= enemy.definition.attack_range and enemy.can_attack():
		enemy.melee_attack()
