class_name Player
extends CombatEntity
## The player is a set of components; this script only wires them together.
## All numbers come from CharacterDefinition + upgrades, nothing is hardcoded per character.

signal attack_performed(direction: Vector2, attack_range: float)
signal skill_performed(skill: SkillDefinition, origin: Vector2, radius: float)

const HIT_INVULNERABILITY := 0.35

var definition: CharacterDefinition

@onready var sprite: Sprite2D = $Sprite2D
@onready var camera: Camera2D = $Camera2D
@onready var movement: MovementComponent = $MovementComponent
@onready var combat: CombatComponent = $CombatComponent
@onready var experience: ExperienceComponent = $ExperienceComponent
@onready var inventory: InventoryComponent = $InventoryComponent
@onready var skills: SkillComponent = $SkillComponent
@onready var controller: PlayerController = $PlayerController

var _anim_time := 0.0
var _flash_tween: Tween


func _ready() -> void:
	health = $HealthComponent
	stats = $StatsComponent
	team = Team.PLAYER
	add_to_group(&"player")


## Must be called after the node is in the tree.
func setup(character: CharacterDefinition, arena_bounds: Rect2) -> void:
	definition = character
	bounds = arena_bounds
	var config := Services.config
	stats.setup(character.base_stats())
	UpgradeService.apply_meta_upgrades(stats, Profile.get_meta_upgrade_levels())
	inventory.setup(self, stats)
	health.setup(stats.get_int(Stats.MAX_HEALTH))
	health.hit_invulnerability = HIT_INVULNERABILITY
	stats.stats_changed.connect(_on_stats_changed)
	health.health_changed.connect(func(current: int, maximum: int) -> void: EventBus.player_health_changed.emit(current, maximum))
	health.damaged.connect(_on_damaged)
	health.died.connect(_on_died)

	movement.setup(self, stats)
	combat.setup(self, stats, character.attack_arc_degrees)
	combat.damage_multiplier = config.get_float("balance.player_damage_multiplier", 1.0)
	combat.auto_attack = bool(Profile.get_setting("auto_attack", true)) and config.is_feature_enabled("auto_attack")
	combat.attacked.connect(func(direction: Vector2, attack_range: float) -> void: attack_performed.emit(direction, attack_range))
	skills.setup(self, stats, character.skills)
	skills.damage_multiplier = combat.damage_multiplier
	skills.skill_activated.connect(func(skill: SkillDefinition, origin: Vector2, radius: float) -> void: skill_performed.emit(skill, origin, radius))
	experience.setup(Content.xp_curve, config.get_float("balance.xp_multiplier", 1.0))
	controller.setup(self)

	_apply_sprite(character.sprite, character.frames)
	EventBus.player_health_changed.emit(health.current, health.max_health)


func get_radius() -> float:
	return 5.0


func _physics_process(delta: float) -> void:
	if not is_alive() or definition == null:
		return
	movement.physics_step(delta)
	combat.physics_step(delta)
	skills.physics_step(delta)
	_animate(delta)


func _animate(delta: float) -> void:
	if absf(movement.facing.x) > 0.1:
		sprite.flip_h = movement.facing.x < 0.0
	if velocity.length() > 1.0 and sprite.hframes > 1:
		_anim_time += delta
		sprite.frame = int(_anim_time * 8.0) % sprite.hframes
	else:
		sprite.frame = 0
	sprite.modulate.a = 0.5 if movement.is_dashing() else 1.0


func _apply_sprite(path: String, frames: int) -> void:
	if ResourceLoader.exists(path):
		sprite.texture = load(path)
		sprite.hframes = maxi(1, frames)
		sprite.offset.y = -sprite.texture.get_height() * 0.5 + 2.0


func _on_stats_changed() -> void:
	var maximum := stats.get_int(Stats.MAX_HEALTH)
	if maximum != health.max_health:
		health.set_max_health(maximum)


func _on_damaged(_amount: int, _source_id: String) -> void:
	AudioManager.play_sfx("player_hurt")
	if bool(Profile.get_setting("vibration", true)):
		Input.vibrate_handheld(40)
	if _flash_tween != null:
		_flash_tween.kill()
	sprite.self_modulate = Color(1.0, 0.35, 0.35)
	_flash_tween = create_tween()
	_flash_tween.tween_property(sprite, "self_modulate", Color.WHITE, 0.25)


func _on_died(source_id: String) -> void:
	velocity = Vector2.ZERO
	EventBus.player_died.emit(source_id)
