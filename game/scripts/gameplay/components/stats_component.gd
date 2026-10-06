class_name StatsComponent
extends Node
## Base stats + modifiers grouped by source ("meta", "equipment", "run_upgrades").
## value = (base + sum(add)) * (1 + sum(multiply))

signal stats_changed

var _base: Dictionary = {}
## source -> Array of {stat, mode, value}
var _modifiers: Dictionary = {}
var _cache: Dictionary = {}


func setup(base_stats: Dictionary) -> void:
	_base = base_stats.duplicate()
	_modifiers.clear()
	_invalidate()


func get_stat(stat: String) -> float:
	if _cache.has(stat):
		return _cache[stat]
	var added := 0.0
	var multiplied := 0.0
	for source: String in _modifiers:
		for modifier: Dictionary in _modifiers[source]:
			if modifier["stat"] != stat:
				continue
			if modifier["mode"] == Stats.MODE_MULTIPLY:
				multiplied += float(modifier["value"])
			else:
				added += float(modifier["value"])
	var value := (float(_base.get(stat, 0.0)) + added) * maxf(0.0, 1.0 + multiplied)
	_cache[stat] = value
	return value


func get_int(stat: String) -> int:
	return roundi(get_stat(stat))


func get_base(stat: String) -> float:
	return float(_base.get(stat, 0.0))


func add_modifier(source: String, stat: String, mode: String, value: float) -> void:
	if not _modifiers.has(source):
		_modifiers[source] = []
	(_modifiers[source] as Array).append({"stat": stat, "mode": mode, "value": value})
	_invalidate()


func remove_modifiers(source: String) -> void:
	if _modifiers.erase(source):
		_invalidate()


func _invalidate() -> void:
	_cache.clear()
	stats_changed.emit()
