class_name GenericDefinition
extends ContentDefinition
## Content that has no typed accessor yet (buildings, skill tree nodes, XP curve rows).
## Fields are read from `raw`.


func get_value(key: String, default: Variant = null) -> Variant:
	return raw.get(key, default)
