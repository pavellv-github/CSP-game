class_name XpCurve
extends RefCounted
## Data-driven XP requirements: {level, required_xp} rows, required_xp is the total XP to reach the level.
## Levels above the last row continue with the last step increased by `overflow_growth`.

var _required: Dictionary = {1: 0}
var _max_defined_level: int = 1
var overflow_growth: float = 1.15


func _init(rows: Array = []) -> void:
	for row: Variant in rows:
		var level: int
		var required: int
		if row is GenericDefinition:
			level = int(row.get_value("level", 0))
			required = int(row.get_value("required_xp", 0))
		elif row is Dictionary:
			level = int(row.get("level", 0))
			required = int(row.get("required_xp", 0))
		else:
			continue
		if level > 1:
			_required[level] = required
			_max_defined_level = maxi(_max_defined_level, level)


## Total XP required to reach `level`.
func required_xp(level: int) -> int:
	if level <= 1:
		return 0
	if _required.has(level):
		return int(_required[level])
	if level <= _max_defined_level:
		# Gap in data: interpolate between neighbours.
		return required_xp(level - 1)
	var last := int(_required[_max_defined_level])
	var previous := int(_required.get(_max_defined_level - 1, 0))
	var step := float(maxi(1, last - previous))
	var total := float(last)
	for _i in level - _max_defined_level:
		step *= overflow_growth
		total += step
	return roundi(total)


## Level reached with `total_xp`.
func level_for_xp(total_xp: int) -> int:
	var level := 1
	while total_xp >= required_xp(level + 1):
		level += 1
	return level
