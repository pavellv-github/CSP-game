class_name ContentSource
extends RefCounted
## Where content comes from. MVP: bundled JSON (LocalJsonContentSource).
## Later: a Supabase-backed source that downloads published content and caches it locally,
## falling back to the last valid cached version when the server is unavailable.


## Returns {"content_version": int, "collections": {name: location}, "config": location}.
func load_manifest() -> Dictionary:
	return {}


## Returns the raw entries of a collection (Array of Dictionaries).
func load_collection(_collection: String) -> Array:
	return []


## Returns the default game config (versions, feature flags, balance).
func load_config() -> Dictionary:
	return {}


## Problems found while reading (missing files, invalid JSON).
func get_errors() -> Array[String]:
	return []
