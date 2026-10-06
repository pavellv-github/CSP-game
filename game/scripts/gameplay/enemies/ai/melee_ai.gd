class_name MeleeAI
extends EnemyAI
## Approaches, stops, telegraphs with a short wind-up, then strikes if the player is still close.

const WIND_UP_TIME := 0.35
const STRIKE_TOLERANCE := 6.0

var _wind_up_left: float = -1.0


func physics_step(delta: float) -> void:
	if not enemy.has_target():
		enemy.velocity = Vector2.ZERO
		return
	if _wind_up_left >= 0.0:
		enemy.velocity = Vector2.ZERO
		_wind_up_left -= delta
		if _wind_up_left < 0.0:
			enemy.sprite.modulate = Color.WHITE
			if enemy.distance_to_target() <= enemy.definition.attack_range + STRIKE_TOLERANCE:
				enemy.melee_attack()
			else:
				enemy.attack_cooldown_left = enemy.definition.attack_cooldown * 0.5
		return
	if enemy.distance_to_target() <= enemy.definition.attack_range:
		enemy.velocity = Vector2.ZERO
		if enemy.can_attack():
			_wind_up_left = WIND_UP_TIME
			enemy.sprite.modulate = Color(1.0, 0.6, 0.6)
			enemy.telegraph_attack()
	else:
		move_towards_target()
