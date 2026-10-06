class_name FirebaseAnalyticsProvider
extends AnalyticsProvider
## Bridge to a native Firebase Analytics plugin (Android/iOS).
## The plugin itself is added to the export as a separate step (see README, "Firebase").
## It is expected to expose an engine singleton with `logEvent(name, params)`.
## When the singleton is missing (desktop, editor, plugin not installed) the provider is inactive.

const SINGLETON_NAME := "FirebaseAnalytics"

var _singleton: Object


func _init() -> void:
	if Engine.has_singleton(SINGLETON_NAME):
		_singleton = Engine.get_singleton(SINGLETON_NAME)


func is_available() -> bool:
	return _singleton != null


func log_event(event_name: String, params: Dictionary) -> void:
	if _singleton != null and _singleton.has_method("logEvent"):
		_singleton.call("logEvent", event_name, params)


func set_user_property(property_name: String, value: String) -> void:
	if _singleton != null and _singleton.has_method("setUserProperty"):
		_singleton.call("setUserProperty", property_name, value)
