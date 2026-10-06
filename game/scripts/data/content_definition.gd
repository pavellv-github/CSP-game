class_name ContentDefinition
extends RefCounted
## Base class for every piece of game content (character, enemy, item, ...).
## Content is described by data (JSON now, Supabase later) and never hardcoded in gameplay.

const STATUS_DRAFT := "draft"
const STATUS_PUBLISHED := "published"
const STATUS_ARCHIVED := "archived"

## Stable ID. Never changes after the content is published.
var id: String = ""
var status: String = STATUS_PUBLISHED
## Source dictionary, kept for fields that do not have a typed accessor yet.
var raw: Dictionary = {}


func _init(data: Dictionary = {}) -> void:
	raw = data
	id = str(data.get("id", ""))
	status = str(data.get("status", STATUS_PUBLISHED))
	_parse(data)


## Override in subclasses to read typed fields.
func _parse(_data: Dictionary) -> void:
	pass


## Override in subclasses to check field values. Returns human readable problems.
func validate() -> Array[String]:
	var errors: Array[String] = []
	if id.is_empty():
		errors.append("missing id")
	if status not in [STATUS_DRAFT, STATUS_PUBLISHED, STATUS_ARCHIVED]:
		errors.append("%s: unknown status '%s'" % [id, status])
	return errors


func is_published() -> bool:
	return status == STATUS_PUBLISHED


static func to_string_array(value: Variant) -> Array[String]:
	var result: Array[String] = []
	if value is Array:
		for entry: Variant in value:
			result.append(str(entry))
	return result


static func to_dict_array(value: Variant) -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	if value is Array:
		for entry: Variant in value:
			if entry is Dictionary:
				result.append(entry)
	return result
