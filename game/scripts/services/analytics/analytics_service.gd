class_name AnalyticsService
extends RefCounted
## Sends events to every available provider. Common context (session_id, level_id,
## character_id, player_level, versions) is attached to each event.
## Never put personal data into events.

var enabled: bool = true
var session_id: String = ""
var _providers: Array[AnalyticsProvider] = []
var _context: Dictionary = {}


func _init() -> void:
	session_id = "%d-%08x" % [int(Time.get_unix_time_from_system()), randi()]


func add_provider(provider: AnalyticsProvider) -> void:
	if provider.is_available():
		_providers.append(provider)


func get_providers() -> Array[AnalyticsProvider]:
	return _providers.duplicate()


func set_context(key: String, value: Variant) -> void:
	if value == null:
		_context.erase(key)
	else:
		_context[key] = value


func log_event(event_name: String, params: Dictionary = {}) -> void:
	if not enabled:
		return
	var payload := _context.duplicate()
	payload["session_id"] = session_id
	payload.merge(params, true)
	for provider in _providers:
		provider.log_event(event_name, payload)
