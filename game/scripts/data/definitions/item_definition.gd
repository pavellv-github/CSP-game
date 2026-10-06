class_name ItemDefinition
extends ContentDefinition

const TYPE_CURRENCY := "currency"
const TYPE_CONSUMABLE := "consumable"
const TYPE_WEAPON := "weapon"
const TYPE_ARMOR := "armor"

var name: String = ""
var type: String = TYPE_CONSUMABLE
var rarity: String = "common"
var stackable: bool = true
var max_stack: int = 99
var icon: String = ""
## [{type: "heal", value} | {type: "stat", stat, mode, value}]
var effects: Array[Dictionary] = []


func _parse(d: Dictionary) -> void:
	name = str(d.get("name", id))
	type = str(d.get("type", type))
	rarity = str(d.get("rarity", rarity))
	stackable = bool(d.get("stackable", stackable))
	max_stack = int(d.get("max_stack", 1 if not stackable else max_stack))
	icon = str(d.get("icon", ""))
	effects = to_dict_array(d.get("effects", []))


func is_equippable() -> bool:
	return type == TYPE_WEAPON or type == TYPE_ARMOR


func is_usable() -> bool:
	return type == TYPE_CONSUMABLE
