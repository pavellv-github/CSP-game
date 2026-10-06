class_name BossAI
extends MeleeAI
## Melee behaviour plus two timed abilities from EnemyDefinition.boss:
## a radial projectile burst and summoning minions.

var _burst_left: float = 0.0
var _summon_left: float = 0.0


func setup(owner_enemy: Enemy) -> void:
	super.setup(owner_enemy)
	_burst_left = float(enemy.definition.boss.get("burst_cooldown", 5.0))
	_summon_left = float(enemy.definition.boss.get("summon_cooldown", 9.0))


func physics_step(delta: float) -> void:
	super.physics_step(delta)
	if not enemy.has_target():
		return
	var params := enemy.definition.boss
	_burst_left -= delta
	if _burst_left <= 0.0 and not enemy.definition.projectile.is_empty():
		_burst_left = float(params.get("burst_cooldown", 5.0))
		var count := int(params.get("burst_count", 8))
		var offset := randf() * TAU
		for i in count:
			enemy.projectile_requested.emit(enemy.global_position, Vector2.from_angle(offset + TAU * i / count),
				enemy.damage * 0.6, enemy.definition.projectile, enemy.definition.id)
	_summon_left -= delta
	if _summon_left <= 0.0:
		_summon_left = float(params.get("summon_cooldown", 9.0))
		var summon_id := str(params.get("summon_enemy_id", ""))
		if not summon_id.is_empty():
			enemy.summon_requested.emit(summon_id, int(params.get("summon_count", 2)), enemy.global_position)
