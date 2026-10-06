class_name EnemyDefinition
extends ContentDefinition

var name: String = ""
var sprite: String = ""
var frames: int = 1
## Animation layout of `sprite` (frame_size + animations from data).
var sheet: SpriteSheet
var health: int = 10
var damage: int = 5
var defense: int = 0
var speed: float = 40.0
var attack_range: float = 12.0
var attack_cooldown: float = 1.0
var experience_reward: int = 1
var loot_table: String = ""
## Behaviour is decoupled from the enemy type: any enemy can reuse any AI.
var ai_type: String = "chase"
var aggro_radius: float = 80.0
var collision_radius: float = 5.0
var is_boss: bool = false
## Optional: {sprite, speed, lifetime}
var projectile: Dictionary = {}
## Optional boss parameters: {burst_cooldown, burst_count, summon_cooldown, summon_enemy_id, summon_count}
var boss: Dictionary = {}


func _parse(d: Dictionary) -> void:
	name = str(d.get("name", id))
	sprite = str(d.get("sprite", ""))
	frames = int(d.get("frames", 1))
	sheet = SpriteSheet.from_data(d)
	health = int(d.get("health", health))
	damage = int(d.get("damage", damage))
	defense = int(d.get("defense", defense))
	speed = float(d.get("speed", speed))
	attack_range = float(d.get("attack_range", attack_range))
	attack_cooldown = float(d.get("attack_cooldown", attack_cooldown))
	experience_reward = int(d.get("experience_reward", experience_reward))
	loot_table = str(d.get("loot_table", ""))
	ai_type = str(d.get("ai_type", ai_type))
	aggro_radius = float(d.get("aggro_radius", aggro_radius))
	collision_radius = float(d.get("collision_radius", collision_radius))
	is_boss = bool(d.get("is_boss", false))
	projectile = d.get("projectile", {})
	boss = d.get("boss", {})


func validate() -> Array[String]:
	var errors := super.validate()
	if health <= 0:
		errors.append("%s: health must be > 0" % id)
	errors.append_array(sheet.validate(id))
	if ai_type == "ranged" and projectile.is_empty():
		errors.append("%s: ranged AI requires 'projectile'" % id)
	return errors
