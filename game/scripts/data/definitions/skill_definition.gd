class_name SkillDefinition
extends ContentDefinition

const EFFECT_AOE_DAMAGE := "aoe_damage"

var name: String = ""
var description: String = ""
var effect: String = EFFECT_AOE_DAMAGE
var cooldown: float = 5.0
var damage_multiplier: float = 1.0
var radius: float = 48.0
var vfx: String = ""


func _parse(d: Dictionary) -> void:
	name = str(d.get("name", id))
	description = str(d.get("description", ""))
	effect = str(d.get("effect", effect))
	cooldown = float(d.get("cooldown", cooldown))
	damage_multiplier = float(d.get("damage_multiplier", damage_multiplier))
	radius = float(d.get("radius", radius))
	vfx = str(d.get("vfx", ""))
