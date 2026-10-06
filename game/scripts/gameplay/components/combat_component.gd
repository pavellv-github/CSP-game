class_name CombatComponent
extends Node
## Player weapon: a melee swing hitting enemies within range and an arc.
## With auto-attack on, swings automatically at the nearest enemy in range.

signal attacked(direction: Vector2, attack_range: float)

const TARGET_GROUP := &"enemies"

var body: CombatEntity
var stats: StatsComponent
var arc_degrees: float = 120.0
var auto_attack: bool = true
## Global balance multiplier (Remote Config: balance.player_damage_multiplier).
var damage_multiplier: float = 1.0
var cooldown_left: float = 0.0


func setup(owner_body: CombatEntity, owner_stats: StatsComponent, arc: float) -> void:
	body = owner_body
	stats = owner_stats
	arc_degrees = arc


func physics_step(delta: float) -> void:
	cooldown_left = maxf(0.0, cooldown_left - delta)
	if not auto_attack or cooldown_left > 0.0:
		return
	var target := CombatSystem.find_nearest(body.get_tree(), TARGET_GROUP, body.global_position, stats.get_stat(Stats.ATTACK_RANGE))
	if target != null:
		_swing(body.global_position.direction_to(target.global_position))


## Attack button: swing toward the nearest enemy nearby, otherwise where the player faces.
func manual_attack(facing: Vector2) -> bool:
	if cooldown_left > 0.0:
		return false
	var direction := facing
	var target := CombatSystem.find_nearest(body.get_tree(), TARGET_GROUP, body.global_position, stats.get_stat(Stats.ATTACK_RANGE) * 1.5)
	if target != null:
		direction = body.global_position.direction_to(target.global_position)
	_swing(direction)
	return true


func _swing(direction: Vector2) -> void:
	var attack_range := stats.get_stat(Stats.ATTACK_RANGE)
	CombatSystem.deal_area_damage(body.get_tree(), TARGET_GROUP, body.global_position, attack_range,
		stats.get_stat(Stats.DAMAGE) * damage_multiplier, stats.get_stat(Stats.CRIT_CHANCE),
		stats.get_stat(Stats.CRIT_MULTIPLIER), direction, arc_degrees, "player_attack")
	cooldown_left = 1.0 / maxf(0.1, stats.get_stat(Stats.ATTACK_SPEED))
	attacked.emit(direction, attack_range)
