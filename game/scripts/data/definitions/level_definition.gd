class_name LevelDefinition
extends ContentDefinition
## A level is pure data: adding a level does not require new gameplay code.

var name: String = ""
var map_size: Vector2 = Vector2(960, 1280)
var map_tile: String = ""
var background: Color = Color(0.2, 0.35, 0.2)
var spawn_points: Array[Vector2] = []
var difficulty: int = 1
## Seconds until the boss appears (or the level ends if there is no boss).
var duration: float = 180.0
## [{enemy_id, start, end, interval, count}]
var enemy_groups: Array[Dictionary] = []
var available_resources: Array[String] = []
var boss: String = ""
## [{item_id, quantity}]
var rewards: Array[Dictionary] = []
var unlock_condition: Dictionary = {}


func _parse(d: Dictionary) -> void:
	name = str(d.get("name", id))
	var map: Dictionary = d.get("map", {})
	map_size = Vector2(float(map.get("width", map_size.x)), float(map.get("height", map_size.y)))
	map_tile = str(map.get("tile", ""))
	background = Color.from_string(str(d.get("background", "#335533")), background)
	spawn_points.clear()
	for point: Dictionary in to_dict_array(d.get("spawn_points", [])):
		spawn_points.append(Vector2(float(point.get("x", 0)), float(point.get("y", 0))))
	difficulty = int(d.get("difficulty", 1))
	duration = float(d.get("duration", duration))
	enemy_groups = to_dict_array(d.get("enemy_groups", []))
	available_resources = to_string_array(d.get("available_resources", []))
	boss = str(d.get("boss", ""))
	rewards = to_dict_array(d.get("rewards", []))
	unlock_condition = d.get("unlock_condition", {})


func player_spawn() -> Vector2:
	return spawn_points[0] if not spawn_points.is_empty() else map_size * 0.5


func validate() -> Array[String]:
	var errors := super.validate()
	if duration <= 0.0:
		errors.append("%s: duration must be > 0" % id)
	for group: Dictionary in enemy_groups:
		if float(group.get("interval", 0)) <= 0.0:
			errors.append("%s: enemy group '%s' needs interval > 0" % [id, group.get("enemy_id", "?")])
	return errors
