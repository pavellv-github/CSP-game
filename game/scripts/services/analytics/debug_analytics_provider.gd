class_name DebugAnalyticsProvider
extends AnalyticsProvider
## Prints events to the output in debug builds. Keeps the last events in memory for tests.

const HISTORY_SIZE := 200

var verbose: bool = false
var history: Array[Dictionary] = []


func is_available() -> bool:
	return OS.is_debug_build()


func log_event(event_name: String, params: Dictionary) -> void:
	history.append({"name": event_name, "params": params})
	if history.size() > HISTORY_SIZE:
		history.pop_front()
	if verbose:
		print("[Analytics] %s %s" % [event_name, JSON.stringify(params)])
