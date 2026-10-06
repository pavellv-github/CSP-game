class_name SkillDefinition
extends ContentDefinition
## Active skill. `effect` selects the behaviour; its parameters come from data:
## - aoe_damage: damage around the caster (radius)
## - target_aoe: damage area at the nearest enemy within cast_range (radius)
## - volley:     `count` projectiles in a fan of `spread_degrees` (projectile params)
## - heal_wave:  heal `heal_ratio` of max HP and damage enemies around (radius)
## - summon:     spawn a companion for `duration` seconds (companion params)

const EFFECT_AOE_DAMAGE := "aoe_damage"
const EFFECT_TARGET_AOE := "target_aoe"
const EFFECT_VOLLEY := "volley"
const EFFECT_HEAL_WAVE := "heal_wave"
const EFFECT_SUMMON := "summon"
const EFFECTS: Array[String] = [EFFECT_AOE_DAMAGE, EFFECT_TARGET_AOE, EFFECT_VOLLEY, EFFECT_HEAL_WAVE, EFFECT_SUMMON]

var name: String = ""
var description: String = ""
var effect: String = EFFECT_AOE_DAMAGE
var cooldown: float = 5.0
var damage_multiplier: float = 1.0
var radius: float = 48.0
var vfx: String = ""
var cast_range: float = 160.0
var count: int = 1
var spread_degrees: float = 0.0
var heal_ratio: float = 0.0
var duration: float = 0.0
var projectile: Dictionary = {}
var companion: Dictionary = {}


func _parse(d: Dictionary) -> void:
	name = str(d.get("name", id))
	description = str(d.get("description", ""))
	effect = str(d.get("effect", effect))
	cooldown = float(d.get("cooldown", cooldown))
	damage_multiplier = float(d.get("damage_multiplier", damage_multiplier))
	radius = float(d.get("radius", radius))
	vfx = str(d.get("vfx", ""))
	cast_range = float(d.get("cast_range", cast_range))
	count = int(d.get("count", count))
	spread_degrees = float(d.get("spread_degrees", spread_degrees))
	heal_ratio = float(d.get("heal_ratio", heal_ratio))
	duration = float(d.get("duration", duration))
	projectile = d.get("projectile", {})
	companion = d.get("companion", {})


func validate() -> Array[String]:
	var errors := super.validate()
	if effect not in EFFECTS:
		errors.append("%s: unknown effect '%s'" % [id, effect])
	if effect == EFFECT_VOLLEY and projectile.is_empty():
		errors.append("%s: volley requires 'projectile'" % id)
	if effect == EFFECT_SUMMON and (companion.is_empty() or duration <= 0.0):
		errors.append("%s: summon requires 'companion' and duration > 0" % id)
	if effect == EFFECT_SUMMON and not companion.is_empty():
		errors.append_array(SpriteSheet.from_data(companion).validate(id))
	return errors
