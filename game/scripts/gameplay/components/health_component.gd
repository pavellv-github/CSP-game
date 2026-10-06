class_name HealthComponent
extends Node

signal health_changed(current: int, maximum: int)
signal damaged(amount: int, source_id: String)
signal died(source_id: String)

var max_health: int = 1
var current: int = 1
var is_dead: bool = false
## Seconds of invulnerability left (dash, hit recovery).
var invulnerable_time: float = 0.0
## Invulnerability granted after each hit (player uses it, enemies keep 0).
var hit_invulnerability: float = 0.0


func setup(maximum: int) -> void:
	max_health = maxi(1, maximum)
	current = max_health
	is_dead = false
	health_changed.emit(current, max_health)


## Changes max health; current health keeps the same missing amount (an HP upgrade heals by the bonus).
func set_max_health(maximum: int) -> void:
	var missing := max_health - current
	max_health = maxi(1, maximum)
	current = clampi(max_health - missing, 1, max_health)
	health_changed.emit(current, max_health)


func apply_damage(amount: int, source_id: String = "") -> int:
	if is_dead or amount <= 0 or invulnerable_time > 0.0:
		return 0
	var applied := mini(amount, current)
	current -= applied
	invulnerable_time = hit_invulnerability
	damaged.emit(applied, source_id)
	health_changed.emit(current, max_health)
	if current <= 0:
		is_dead = true
		died.emit(source_id)
	return applied


func heal(amount: int) -> int:
	if is_dead or amount <= 0:
		return 0
	var healed := mini(amount, max_health - current)
	current += healed
	health_changed.emit(current, max_health)
	return healed


func get_ratio() -> float:
	return float(current) / float(max_health)


func _physics_process(delta: float) -> void:
	if invulnerable_time > 0.0:
		invulnerable_time = maxf(0.0, invulnerable_time - delta)
