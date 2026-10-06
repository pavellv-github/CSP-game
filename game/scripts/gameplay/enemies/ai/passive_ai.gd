class_name PassiveAI
extends MeleeAI
## Wanders until the player comes close or it gets hit, then fights like MeleeAI.

const WANDER_SPEED_SCALE := 0.4
const WANDER_CHANGE_TIME := 2.0

var aggressive: bool = false
var _wander_direction: Vector2 = Vector2.ZERO
var _wander_time_left: float = 0.0


func physics_step(delta: float) -> void:
	if not aggressive and enemy.has_target() and enemy.distance_to_target() <= enemy.definition.aggro_radius:
		aggressive = true
	if aggressive:
		super.physics_step(delta)
		return
	_wander_time_left -= delta
	if _wander_time_left <= 0.0:
		_wander_time_left = WANDER_CHANGE_TIME * randf_range(0.6, 1.4)
		_wander_direction = Vector2.from_angle(randf() * TAU) if randf() > 0.3 else Vector2.ZERO
	enemy.velocity = _wander_direction * enemy.move_speed * WANDER_SPEED_SCALE


func on_damaged() -> void:
	aggressive = true
