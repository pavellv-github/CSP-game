class_name CombatEntity
extends CharacterBody2D
## Anything that can take part in combat (player, enemies). CombatSystem talks to this
## interface and does not care about the concrete entity type.

enum Team { PLAYER, ENEMIES }

var team: Team = Team.ENEMIES
var health: HealthComponent
var stats: StatsComponent
## Arena bounds; the entity is kept inside them.
var bounds: Rect2 = Rect2()


func is_alive() -> bool:
	return health != null and not health.is_dead


func get_defense() -> float:
	return stats.get_stat(Stats.DEFENSE) if stats != null else 0.0


## Collision radius used for range checks.
func get_radius() -> float:
	return 6.0


func clamp_to_bounds() -> void:
	if bounds.has_area():
		global_position = global_position.clamp(bounds.position, bounds.end)
