class_name RemoteConfigService
extends RefCounted
## Config values with layered sources: bundled defaults (data/config) <- cached remote values.
## MVP: only defaults + local cache. A Firebase Remote Config provider can call
## `apply_remote()` with fetched values; the last fetched values are cached for offline play.
## Keys use dot paths: "balance.xp_multiplier", "feature_flags.auto_attack".

const CACHE_PATH := "user://remote_config_cache.json"

var _defaults: Dictionary = {}
var _overrides: Dictionary = {}


func _init(defaults: Dictionary = {}) -> void:
	_defaults = defaults.duplicate(true)


func load_cached() -> void:
	if not FileAccess.file_exists(CACHE_PATH):
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(CACHE_PATH))
	if parsed is Dictionary:
		_overrides = parsed


## Applies values fetched from a remote provider and caches them.
func apply_remote(values: Dictionary) -> void:
	_overrides = values.duplicate(true)
	var file := FileAccess.open(CACHE_PATH, FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(_overrides))


func get_value(path: String, default: Variant = null) -> Variant:
	var value: Variant = _lookup(_overrides, path)
	if value == null:
		value = _lookup(_defaults, path)
	return default if value == null else value


func get_float(path: String, default: float = 0.0) -> float:
	return float(get_value(path, default))


func get_int(path: String, default: int = 0) -> int:
	return int(get_value(path, default))


func is_feature_enabled(flag: String) -> bool:
	return bool(get_value("feature_flags." + flag, false))


func game_version() -> String:
	return str(get_value("game_version", ProjectSettings.get_setting("application/config/version", "0.0.0")))


func content_version() -> int:
	return get_int("content_version", 0)


static func _lookup(source: Dictionary, path: String) -> Variant:
	var node: Variant = source
	for key in path.split("."):
		if not node is Dictionary or not (node as Dictionary).has(key):
			return null
		node = (node as Dictionary)[key]
	return node
