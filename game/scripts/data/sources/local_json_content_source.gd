class_name LocalJsonContentSource
extends ContentSource
## Reads content bundled with the build from res://data (or any folder with the same layout).

const DEFAULT_MANIFEST := "res://data/manifest.json"

var manifest_path: String
var _manifest: Dictionary = {}
var _errors: Array[String] = []


func _init(path: String = DEFAULT_MANIFEST) -> void:
	manifest_path = path


func load_manifest() -> Dictionary:
	if _manifest.is_empty():
		var parsed: Variant = _read_json(manifest_path)
		_manifest = parsed if parsed is Dictionary else {}
	return _manifest


func load_collection(collection: String) -> Array:
	var collections: Dictionary = load_manifest().get("collections", {})
	if not collections.has(collection):
		_errors.append("manifest has no collection '%s'" % collection)
		return []
	var parsed: Variant = _read_json(str(collections[collection]))
	if parsed is Dictionary:
		return parsed.get("items", [])
	return []


func load_config() -> Dictionary:
	var path := str(load_manifest().get("config", ""))
	if path.is_empty():
		return {}
	var parsed: Variant = _read_json(path)
	return parsed if parsed is Dictionary else {}


func get_errors() -> Array[String]:
	return _errors.duplicate()


func _read_json(path: String) -> Variant:
	if not FileAccess.file_exists(path):
		_errors.append("file not found: %s" % path)
		return null
	var text := FileAccess.get_file_as_string(path)
	var json := JSON.new()
	if json.parse(text) != OK:
		_errors.append("%s:%d: %s" % [path, json.get_error_line(), json.get_error_message()])
		return null
	return json.data
