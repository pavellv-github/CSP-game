class_name Companion
extends CharacterBody2D
## Temporary ally summoned by a skill (hunter's wolf). Chases the nearest enemy near its owner,
## bites on a cooldown, otherwise follows the owner. Not a combat target: enemies ignore it.
## Params (from skill data): sprite sheet fields, speed, attack_range, attack_cooldown,
## damage_multiplier, leash_radius.

const TARGET_GROUP := &"enemies"

var owner_body: CombatEntity
var damage: float = 10.0
var speed: float = 110.0
var attack_range: float = 14.0
var attack_cooldown: float = 0.7
var leash_radius: float = 160.0
var time_left: float = 10.0
var _cooldown_left: float = 0.0
var _dismissed := false
var _sprite: SpriteAnimator
var _sheet: SpriteSheet


static func create(summoner: CombatEntity, params: Dictionary, owner_damage: float, duration: float) -> Companion:
	var companion := Companion.new()
	companion.owner_body = summoner
	companion.global_position = summoner.global_position + Vector2(-14, 6)
	companion.damage = owner_damage * float(params.get("damage_multiplier", 0.8))
	companion.speed = float(params.get("speed", 110.0))
	companion.attack_range = float(params.get("attack_range", 14.0))
	companion.attack_cooldown = float(params.get("attack_cooldown", 0.7))
	companion.leash_radius = float(params.get("leash_radius", 160.0))
	companion.time_left = duration
	companion.collision_layer = 0
	companion.collision_mask = 1 # world only: passes through enemies and the player
	companion.motion_mode = CharacterBody2D.MOTION_MODE_FLOATING
	var shape := CollisionShape2D.new()
	var circle := CircleShape2D.new()
	circle.radius = 4.0
	shape.shape = circle
	companion.add_child(shape)
	companion._sprite = SpriteAnimator.new()
	companion.add_child(companion._sprite)
	companion._sheet = SpriteSheet.from_data(params)
	return companion


func _ready() -> void:
	_sprite.setup(_sheet)


func _physics_process(delta: float) -> void:
	if _dismissed:
		return
	time_left -= delta
	_cooldown_left = maxf(0.0, _cooldown_left - delta)
	if time_left <= 0.0 or owner_body == null or not is_instance_valid(owner_body) or not owner_body.is_alive():
		_dismiss()
		return
	var target := CombatSystem.find_nearest(get_tree(), TARGET_GROUP, owner_body.global_position, leash_radius)
	if target != null:
		var distance := global_position.distance_to(target.global_position) - target.get_radius()
		if distance <= attack_range:
			velocity = Vector2.ZERO
			if _cooldown_left <= 0.0:
				_cooldown_left = attack_cooldown
				_sprite.play_once(&"attack")
				CombatSystem.deal_damage(target, damage, 0.0, 1.0, "companion")
		else:
			velocity = global_position.direction_to(target.global_position) * speed
	elif global_position.distance_to(owner_body.global_position) > 28.0:
		velocity = global_position.direction_to(owner_body.global_position) * speed
	else:
		velocity = Vector2.ZERO
	move_and_slide()
	if absf(velocity.x) > 1.0:
		_sprite.flip_h = velocity.x < 0.0
	_sprite.play_loop(&"walk" if velocity.length() > 1.0 else &"idle")


func _dismiss() -> void:
	_dismissed = true
	_sprite.play_death()
	var tween := create_tween()
	tween.tween_interval(_sprite.duration(&"death"))
	tween.tween_property(self, "modulate:a", 0.0, 0.2)
	tween.tween_callback(queue_free)
