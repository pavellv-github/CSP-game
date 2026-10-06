class_name CharacterDefinition
extends ContentDefinition

var name: String = ""
var description: String = ""
var sprite: String = ""
var frames: int = 1
## Animation layout of `sprite` (frame_size + animations from data).
var sheet: SpriteSheet
## Menu art: full-height portrait and round class emblem (optional).
var portrait: String = ""
var class_icon: String = ""
var base_health: int = 100
var base_damage: int = 10
var base_speed: float = 80.0
var base_defense: int = 0
var attack_range: float = 32.0
var attack_speed: float = 1.0
var attack_arc_degrees: float = 120.0
var crit_chance: float = 0.0
var crit_multiplier: float = 1.5
var pickup_radius: float = 40.0
var skills: Array[String] = []
var unlock_condition: Dictionary = {}


func _parse(d: Dictionary) -> void:
	name = str(d.get("name", id))
	description = str(d.get("description", ""))
	sprite = str(d.get("sprite", ""))
	frames = int(d.get("frames", 1))
	sheet = SpriteSheet.from_data(d)
	portrait = str(d.get("portrait", ""))
	class_icon = str(d.get("class_icon", ""))
	base_health = int(d.get("base_health", base_health))
	base_damage = int(d.get("base_damage", base_damage))
	base_speed = float(d.get("base_speed", base_speed))
	base_defense = int(d.get("base_defense", base_defense))
	attack_range = float(d.get("attack_range", attack_range))
	attack_speed = float(d.get("attack_speed", attack_speed))
	attack_arc_degrees = float(d.get("attack_arc_degrees", attack_arc_degrees))
	crit_chance = float(d.get("crit_chance", crit_chance))
	crit_multiplier = float(d.get("crit_multiplier", crit_multiplier))
	pickup_radius = float(d.get("pickup_radius", pickup_radius))
	skills = to_string_array(d.get("skills", []))
	unlock_condition = d.get("unlock_condition", {})


## Stats in the format consumed by StatsComponent.
func base_stats() -> Dictionary:
	return {
		Stats.MAX_HEALTH: float(base_health),
		Stats.DAMAGE: float(base_damage),
		Stats.SPEED: base_speed,
		Stats.DEFENSE: float(base_defense),
		Stats.ATTACK_RANGE: attack_range,
		Stats.ATTACK_SPEED: attack_speed,
		Stats.CRIT_CHANCE: crit_chance,
		Stats.CRIT_MULTIPLIER: crit_multiplier,
		Stats.PICKUP_RADIUS: pickup_radius,
	}


func validate() -> Array[String]:
	var errors := super.validate()
	if base_health <= 0:
		errors.append("%s: base_health must be > 0" % id)
	if attack_speed <= 0.0:
		errors.append("%s: attack_speed must be > 0" % id)
	errors.append_array(sheet.validate(id))
	for path in [portrait, class_icon]:
		if not path.is_empty() and not ResourceLoader.exists(path):
			errors.append("%s: missing asset '%s'" % [id, path])
	return errors
