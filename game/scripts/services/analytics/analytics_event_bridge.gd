class_name AnalyticsEventBridge
extends RefCounted
## Translates EventBus facts into analytics events. Gameplay code never calls analytics directly.

var _analytics: AnalyticsService
var _run_started_at: int = 0
var _last_death_reason: String = ""


func _init(analytics: AnalyticsService) -> void:
	_analytics = analytics
	EventBus.run_started.connect(_on_run_started)
	EventBus.run_finished.connect(_on_run_finished)
	EventBus.player_died.connect(func(reason: String) -> void: _last_death_reason = reason)
	EventBus.character_selected.connect(func(id: String) -> void: _analytics.log_event("character_selected", {"character_id": id}))
	EventBus.character_unlocked.connect(func(id: String) -> void: _analytics.log_event("character_unlocked", {"character_id": id}))
	EventBus.enemy_killed.connect(_on_enemy_killed)
	EventBus.player_leveled_up.connect(_on_level_up)
	EventBus.upgrade_selected.connect(func(id: String, level: int) -> void: _analytics.log_event("upgrade_selected", {"upgrade_id": id, "upgrade_level": level}))
	EventBus.meta_upgrade_purchased.connect(func(id: String, level: int) -> void: _analytics.log_event("upgrade_selected", {"upgrade_id": id, "upgrade_level": level, "scope": "meta"}))
	EventBus.item_obtained.connect(func(id: String, quantity: int) -> void: _analytics.log_event("item_obtained", {"item_id": id, "quantity": quantity}))
	EventBus.item_used.connect(func(id: String) -> void: _analytics.log_event("item_used", {"item_id": id}))
	EventBus.building_created.connect(func(id: String) -> void: _analytics.log_event("building_created", {"building_id": id}))
	EventBus.building_upgraded.connect(func(id: String, level: int) -> void: _analytics.log_event("building_upgraded", {"building_id": id, "building_level": level}))


func _on_run_started(level_id: String, character_id: String) -> void:
	_run_started_at = Time.get_ticks_msec()
	_last_death_reason = ""
	_analytics.set_context("level_id", level_id)
	_analytics.set_context("character_id", character_id)
	_analytics.set_context("player_level", 1)
	_analytics.log_event("game_started")


func _on_run_finished(_level_id: String, victory: bool, summary: Dictionary) -> void:
	var params := {
		"duration_sec": int((Time.get_ticks_msec() - _run_started_at) / 1000.0),
		"kills": int(summary.get("kills", 0)),
	}
	if victory:
		_analytics.log_event("game_completed", params)
	else:
		params["death_reason"] = _last_death_reason
		_analytics.log_event("game_failed", params)
	_analytics.set_context("level_id", null)
	_analytics.set_context("player_level", null)


func _on_enemy_killed(enemy_id: String, _position: Vector2, _xp: int, _loot: String, is_boss: bool) -> void:
	_analytics.log_event("boss_killed" if is_boss else "enemy_killed", {"enemy_id": enemy_id})


func _on_level_up(new_level: int) -> void:
	_analytics.set_context("player_level", new_level)
	_analytics.log_event("level_up")
