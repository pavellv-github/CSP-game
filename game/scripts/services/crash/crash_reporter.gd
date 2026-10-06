class_name CrashReporter
extends RefCounted
## Crash / non-fatal error reporting. Uses a native Firebase Crashlytics plugin when it is
## present in the export (engine singleton "FirebaseCrashlytics"); otherwise keeps errors locally.
## Native crashes and ANRs are captured by the Crashlytics SDK itself; this class forwards
## script errors (non-fatals), breadcrumbs and custom keys (game/content version, level).

const SINGLETON_NAME := "FirebaseCrashlytics"
const MAX_LOCAL_ERRORS := 50

var enabled: bool = true
var recent_errors: Array[String] = []
var _singleton: Object
var _mutex := Mutex.new()


func _init() -> void:
	if Engine.has_singleton(SINGLETON_NAME):
		_singleton = Engine.get_singleton(SINGLETON_NAME)


func is_native_available() -> bool:
	return _singleton != null


func set_custom_key(key: String, value: String) -> void:
	if _singleton != null and _singleton.has_method("setCustomKey"):
		_singleton.call("setCustomKey", key, value)


func log_breadcrumb(message: String) -> void:
	if _singleton != null and _singleton.has_method("log"):
		_singleton.call("log", message)


## May be called from any thread (Logger callbacks).
func record_non_fatal(message: String) -> void:
	if not enabled:
		return
	_mutex.lock()
	recent_errors.append(message)
	if recent_errors.size() > MAX_LOCAL_ERRORS:
		recent_errors.pop_front()
	_mutex.unlock()
	if _singleton != null and _singleton.has_method("recordException"):
		_singleton.call_deferred("recordException", message)
