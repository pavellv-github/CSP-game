class_name MovementComponent
extends Node
## Moves the owning CombatEntity from a direction input, with a short invulnerable dash.

signal dashed

@export var dash_speed_multiplier: float = 3.2
@export var dash_duration: float = 0.16
@export var dash_cooldown: float = 1.1

var body: CombatEntity
var stats: StatsComponent
var move_input: Vector2 = Vector2.ZERO
var facing: Vector2 = Vector2.DOWN
var dash_cooldown_left: float = 0.0
var _dash_time_left: float = 0.0
var _dash_direction: Vector2 = Vector2.ZERO


func setup(owner_body: CombatEntity, owner_stats: StatsComponent) -> void:
	body = owner_body
	stats = owner_stats


func is_dashing() -> bool:
	return _dash_time_left > 0.0


func try_dash() -> bool:
	if dash_cooldown_left > 0.0 or is_dashing():
		return false
	_dash_direction = move_input.normalized() if move_input != Vector2.ZERO else facing
	_dash_time_left = dash_duration
	dash_cooldown_left = dash_cooldown
	if body.health != null:
		body.health.invulnerable_time = maxf(body.health.invulnerable_time, dash_duration + 0.05)
	dashed.emit()
	return true


func physics_step(delta: float) -> void:
	dash_cooldown_left = maxf(0.0, dash_cooldown_left - delta)
	var speed := stats.get_stat(Stats.SPEED)
	if is_dashing():
		_dash_time_left -= delta
		body.velocity = _dash_direction * speed * dash_speed_multiplier
	else:
		var direction := move_input.limit_length(1.0)
		if direction.length() > 0.1:
			facing = direction.normalized()
		body.velocity = direction * speed
	body.move_and_slide()
	body.clamp_to_bounds()
