class_name CrashLogger
extends Logger
## Engine logger (Godot 4.5+) that forwards script/engine errors to CrashReporter as non-fatals.

var _reporter: CrashReporter


func _init(reporter: CrashReporter) -> void:
	_reporter = reporter


func _log_error(function: String, file: String, line: int, code: String, rationale: String,
		_editor_notify: bool, error_type: int, _script_backtraces: Array[ScriptBacktrace]) -> void:
	if error_type == Logger.ERROR_TYPE_WARNING:
		return
	var message := rationale if not rationale.is_empty() else code
	_reporter.record_non_fatal("%s (%s:%d in %s)" % [message, file, line, function])


func _log_message(_message: String, _error: bool) -> void:
	pass
