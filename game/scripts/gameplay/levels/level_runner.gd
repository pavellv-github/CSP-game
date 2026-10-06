class_name LevelRunner
extends Node
## Plays a LevelDefinition: spawns enemy groups over time, then the boss, and reports the outcome.
## No level-specific code: everything comes from data.

signal boss_spawned(boss: Enemy)
signal level_cleared

const ENEMY_SCENE := preload("res://scenes/enemies/enemy.tscn")

var level: LevelDefinition
var player: Player
var entities: Node2D
var projectiles: Node2D
var elapsed: float = 0.0
var kills: int = 0
var boss: Enemy

var _group_timers: Array[float] = []
var _boss_spawned := false
var _finished := false
var _hp_multiplier := 1.0
var _damage_multiplier := 1.0
var _max_alive := 120
var _spawn_min := 360.0
var _spawn_max := 420.0
var _rng := RandomNumberGenerator.new()


func setup(level_definition: LevelDefinition, target: Player, entity_container: Node2D, projectile_container: Node2D) -> void:
	level = level_definition
	player = target
	entities = entity_container
	projectiles = projectile_container
	_rng.randomize()
	var config := Services.config
	var difficulty_steps := float(level.difficulty - 1)
	_hp_multiplier = config.get_float("balance.enemy_hp_multiplier", 1.0) * (1.0 + difficulty_steps * config.get_float("balance.difficulty_hp_step", 0.25))
	_damage_multiplier = config.get_float("balance.enemy_damage_multiplier", 1.0) * (1.0 + difficulty_steps * config.get_float("balance.difficulty_damage_step", 0.15))
	_max_alive = config.get_int("limits.max_alive_enemies", 120)
	_spawn_min = config.get_float("limits.spawn_distance_min", 360.0)
	_spawn_max = config.get_float("limits.spawn_distance_max", 420.0)
	_group_timers.clear()
	for group in level.enemy_groups:
		_group_timers.append(0.0)
	EventBus.enemy_killed.connect(_on_enemy_killed)


func get_remaining_time() -> float:
	return maxf(0.0, level.duration - elapsed)


func _physics_process(delta: float) -> void:
	if level == null or _finished or not player.is_alive():
		return
	elapsed += delta
	EventBus.level_time_changed.emit(elapsed, level.duration)
	if elapsed < level.duration:
		_update_groups(delta)
	elif not _boss_spawned:
		_boss_spawned = true
		if level.boss.is_empty():
			_finish()
		else:
			_spawn_boss()


func _update_groups(delta: float) -> void:
	for i in level.enemy_groups.size():
		var group := level.enemy_groups[i]
		if elapsed < float(group.get("start", 0.0)) or elapsed > float(group.get("end", level.duration)):
			continue
		_group_timers[i] -= delta
		if _group_timers[i] > 0.0:
			continue
		_group_timers[i] = float(group.get("interval", 2.0))
		for _n in int(group.get("count", 1)):
			if get_tree().get_node_count_in_group(&"enemies") >= _max_alive:
				return
			spawn_enemy(str(group.get("enemy_id", "")), _random_spawn_position())


func spawn_enemy(enemy_id: String, position: Vector2) -> Enemy:
	var definition := Content.get_enemy(enemy_id)
	if definition == null:
		return null
	var enemy: Enemy = ENEMY_SCENE.instantiate()
	enemy.global_position = position
	entities.add_child(enemy)
	enemy.setup(definition, player, _arena_rect(), _hp_multiplier, _damage_multiplier)
	enemy.projectile_requested.connect(_on_projectile_requested)
	enemy.summon_requested.connect(_on_summon_requested)
	EventBus.enemy_spawned.emit(enemy)
	return enemy


func _spawn_boss() -> void:
	# Clear the field so the boss fight is readable.
	for node in get_tree().get_nodes_in_group(&"enemies"):
		(node as Node).queue_free()
	boss = spawn_enemy(level.boss, _random_spawn_position(_spawn_min * 0.6, _spawn_min * 0.8))
	if boss == null:
		_finish()
		return
	EventBus.boss_spawned.emit(boss)
	EventBus.boss_health_changed.emit(boss.health.current, boss.health.max_health)
	boss_spawned.emit(boss)


func _on_enemy_killed(_enemy_id: String, _position: Vector2, _xp: int, _loot: String, is_boss: bool) -> void:
	kills += 1
	if is_boss and _boss_spawned:
		# Small delay so the death animation and loot are visible.
		get_tree().create_timer(1.2).timeout.connect(_finish)


func _finish() -> void:
	if _finished:
		return
	_finished = true
	level_cleared.emit()


func _on_projectile_requested(origin: Vector2, direction: Vector2, damage: float, params: Dictionary, source_id: String) -> void:
	projectiles.add_child(Projectile.create(origin, direction, damage, params, source_id, CombatEntity.Team.PLAYER))


func _on_summon_requested(enemy_id: String, count: int, origin: Vector2) -> void:
	for i in count:
		if get_tree().get_node_count_in_group(&"enemies") >= _max_alive:
			return
		spawn_enemy(enemy_id, origin + Vector2.from_angle(TAU * i / count) * 24.0)


func _random_spawn_position(min_distance: float = -1.0, max_distance: float = -1.0) -> Vector2:
	var low := _spawn_min if min_distance < 0.0 else min_distance
	var high := _spawn_max if max_distance < 0.0 else max_distance
	var arena := _arena_rect()
	var position := player.global_position
	for _attempt in 8:
		position = player.global_position + Vector2.from_angle(_rng.randf() * TAU) * _rng.randf_range(low, high)
		if arena.has_point(position):
			return position
	return position.clamp(arena.position, arena.end)


func _arena_rect() -> Rect2:
	return Rect2(Vector2(8, 8), level.map_size - Vector2(16, 16))
