class_name CombatComponent
extends Node
## Player basic attack. The type comes from CharacterDefinition.attack:
## - "melee_arc": a swing hitting enemies within range and an arc;
## - "projectile": a shot toward the target with the projectile params from data.
## With auto-attack on, attacks automatically when an enemy is in range.

signal attacked(direction: Vector2, attack_range: float, is_melee: bool)

const TARGET_GROUP := &"enemies"
const TYPE_MELEE_ARC := "melee_arc"
const TYPE_PROJECTILE := "projectile"

var body: CombatEntity
var stats: StatsComponent
var attack_type: String = TYPE_MELEE_ARC
var arc_degrees: float = 120.0
var projectile_params: Dictionary = {}
var auto_attack: bool = true
## Global balance multiplier (Remote Config: balance.player_damage_multiplier).
var damage_multiplier: float = 1.0
var cooldown_left: float = 0.0
## Delay between the start of the attack animation and the moment the projectile leaves
## (the sheet's attack hit_frame), so the shot matches the release pose.
var release_delay: float = 0.0


func setup(owner_body: CombatEntity, owner_stats: StatsComponent, character: CharacterDefinition) -> void:
	body = owner_body
	stats = owner_stats
	arc_degrees = character.attack_arc_degrees
	attack_type = character.attack_type
	projectile_params = character.attack_projectile
	var attack_anim: Dictionary = character.sheet.animations.get("attack", {})
	if int(attack_anim.get("hit_frame", -1)) > 0:
		release_delay = int(attack_anim["hit_frame"]) / maxf(1.0, float(attack_anim["fps"]))


func physics_step(delta: float) -> void:
	cooldown_left = maxf(0.0, cooldown_left - delta)
	if not auto_attack or cooldown_left > 0.0:
		return
	var target := CombatSystem.find_nearest(body.get_tree(), TARGET_GROUP, body.global_position, stats.get_stat(Stats.ATTACK_RANGE))
	if target != null:
		_attack(body.global_position.direction_to(target.global_position))


## Attack button: toward the nearest enemy nearby, otherwise where the player faces.
func manual_attack(facing: Vector2) -> bool:
	if cooldown_left > 0.0:
		return false
	var direction := facing
	var target := CombatSystem.find_nearest(body.get_tree(), TARGET_GROUP, body.global_position, stats.get_stat(Stats.ATTACK_RANGE) * 1.5)
	if target != null:
		direction = body.global_position.direction_to(target.global_position)
	_attack(direction)
	return true


func _attack(direction: Vector2) -> void:
	var attack_range := stats.get_stat(Stats.ATTACK_RANGE)
	var damage := stats.get_stat(Stats.DAMAGE) * damage_multiplier
	cooldown_left = 1.0 / maxf(0.1, stats.get_stat(Stats.ATTACK_SPEED))
	attacked.emit(direction, attack_range, attack_type != TYPE_PROJECTILE)
	if attack_type != TYPE_PROJECTILE:
		CombatSystem.deal_area_damage(body.get_tree(), TARGET_GROUP, body.global_position, attack_range,
			damage, stats.get_stat(Stats.CRIT_CHANCE), stats.get_stat(Stats.CRIT_MULTIPLIER), direction, arc_degrees, "player_attack")
		return
	if release_delay > 0.0:
		await body.get_tree().create_timer(release_delay, false).timeout
		if not is_instance_valid(body) or not body.is_alive():
			return
	Projectile.fire_from(body, direction, damage, projectile_params, "player_attack",
		stats.get_stat(Stats.CRIT_CHANCE), stats.get_stat(Stats.CRIT_MULTIPLIER), attack_range)
