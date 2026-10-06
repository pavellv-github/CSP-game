class_name TestCase
extends RefCounted
## Minimal test base: every method starting with "test_" is a test.

var failures: Array[String] = []
var _current: String = ""


func run_all() -> Dictionary:
	var passed := 0
	var failed := 0
	for method in get_method_list():
		var method_name := str(method["name"])
		if not method_name.begins_with("test_"):
			continue
		_current = method_name
		var before := failures.size()
		before_each()
		call(method_name)
		after_each()
		if failures.size() == before:
			passed += 1
		else:
			failed += 1
	return {"passed": passed, "failed": failed}


func before_each() -> void:
	pass


func after_each() -> void:
	pass


func assert_true(condition: bool, message: String = "") -> void:
	if not condition:
		failures.append("%s: expected true. %s" % [_current, message])


func assert_false(condition: bool, message: String = "") -> void:
	if condition:
		failures.append("%s: expected false. %s" % [_current, message])


func assert_eq(actual: Variant, expected: Variant, message: String = "") -> void:
	if actual != expected:
		failures.append("%s: expected <%s>, got <%s>. %s" % [_current, expected, actual, message])


func assert_almost(actual: float, expected: float, tolerance: float = 0.001, message: String = "") -> void:
	if absf(actual - expected) > tolerance:
		failures.append("%s: expected ~%f, got %f. %s" % [_current, expected, actual, message])
