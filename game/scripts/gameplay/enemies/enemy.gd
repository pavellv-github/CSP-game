class_name Enemy
extends CombatEntity
## Generic enemy body. Stats come from EnemyDefinition, behaviour from a pluggable EnemyAI.

signal summon_requested(enemy_id: String, count: int, origin: Vector2)
signal projectile_requested(origin: Vector2, direction: Vector2, damage: float, projectile: Dictionary, source_id: String)

var definition: EnemyDefinition
var target: CombatEntity
var ai: EnemyAI
var damage: float = 0.0
var move_speed: float = 0.0
var attack_cooldown_left: float = 0.0

@onready var sprite: SpriteAnimator = $Sprite
@onready var collision: CollisionShape2D = $CollisionShape2D

var _flash_tween: Tween


func _ready() -> void:
	health = $HealthComponent
	stats = $StatsComponent
	team = Team.ENEMIES


## `hp_multiplier` / `damage_multiplier` combine Remote Config balance and level difficulty.
func setup(enemy: EnemyDefinition, player: CombatEntity, arena_bounds: Rect2, hp_multiplier: float, damage_multiplier: float) -> void:
	definition = enemy
	target = player
	bounds = arena_bounds
	damage = enemy.damage * damage_multiplier
	move_speed = enemy.speed
	stats.setup({Stats.DEFENSE: float(enemy.defense), Stats.SPEED: enemy.speed})
	health.setup(maxi(1, roundi(enemy.health * hp_multiplier)))
	health.damaged.connect(_on_damaged)
	health.died.connect(_on_died)
	(collision.shape as CircleShape2D).radius = enemy.collision_radius
	sprite.setup(enemy.sheet)
	GroundShadow.attach(self, enemy.collision_radius * 2.6)
	ai = AiFactory.create(enemy.ai_type)
	ai.name = "AI"
	add_child(ai)
	ai.setup(self)
	add_to_group(&"enemies")
	if enemy.is_boss:
		health.health_changed.connect(func(current: int, maximum: int) -> void: EventBus.boss_health_changed.emit(current, maximum))


func get_radius() -> float:
	return definition.collision_radius if definition != null else 5.0


func has_target() -> bool:
	return target != null and is_instance_valid(target) and target.is_alive()


## Distance between the edges of the two bodies.
func distance_to_target() -> float:
	if not has_target():
		return INF
	return global_position.distance_to(target.global_position) - get_radius() - target.get_radius()


func direction_to_target() -> Vector2:
	return global_position.direction_to(target.global_position) if has_target() else Vector2.ZERO


func can_attack() -> bool:
	return attack_cooldown_left <= 0.0 and has_target()


## Starts the attack animation ahead of the blow (used by AIs with a wind-up).
func telegraph_attack() -> void:
	sprite.play_once(&"attack")


func melee_attack() -> void:
	attack_cooldown_left = definition.attack_cooldown
	if sprite.animation != &"attack":
		sprite.play_once(&"attack")
	CombatSystem.deal_damage(target, damage, 0.0, 1.0, definition.id)


func shoot(direction: Vector2) -> void:
	attack_cooldown_left = definition.attack_cooldown
	sprite.play_once(&"attack")
	projectile_requested.emit(global_position, direction, damage, definition.projectile, definition.id)


func _physics_process(delta: float) -> void:
	if not is_alive() or ai == null:
		return
	attack_cooldown_left = maxf(0.0, attack_cooldown_left - delta)
	ai.physics_step(delta)
	move_and_slide()
	clamp_to_bounds()
	if absf(velocity.x) > 1.0:
		sprite.flip_h = velocity.x < 0.0
	sprite.play_loop(&"walk" if velocity.length() > 1.0 else &"idle")


func _on_damaged(_amount: int, _source_id: String) -> void:
	ai.on_damaged()
	sprite.play_once(&"hurt")
	if _flash_tween != null:
		_flash_tween.kill()
	sprite.self_modulate = Color(3, 3, 3)
	_flash_tween = create_tween()
	_flash_tween.tween_property(sprite, "self_modulate", Color.WHITE, 0.12)


func _on_died(_source_id: String) -> void:
	remove_from_group(&"enemies")
	collision.set_deferred("disabled", true)
	velocity = Vector2.ZERO
	EventBus.enemy_killed.emit(definition.id, global_position, definition.experience_reward, definition.loot_table, definition.is_boss)
	sprite.play_death()
	var tween := create_tween()
	tween.tween_interval(sprite.duration(&"death"))
	tween.tween_property(self, "modulate:a", 0.0, 0.25)
	tween.tween_callback(queue_free)
