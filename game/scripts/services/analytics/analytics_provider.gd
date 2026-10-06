class_name AnalyticsProvider
extends RefCounted
## Backend for analytics events (Firebase, debug log, ...).


func is_available() -> bool:
	return true


func log_event(_event_name: String, _params: Dictionary) -> void:
	pass


func set_user_property(_property_name: String, _value: String) -> void:
	pass
