class_name Projectile
extends Area2D
## Straight-flying projectile for both sides. Damage is captured at spawn, so it still works
## if the shooter dies. Params (from data): sprite, speed, lifetime, pierce, aoe_radius, aoe_vfx.

const PLAYER_LAYER := 2
const ENEMY_LAYER := 3
const TEAM_GROUPS := {CombatEntity.Team.PLAYER: &"player", CombatEntity.Team.ENEMIES: &"enemies"}

var direction: Vector2 = Vector2.RIGHT
var speed: float = 100.0
var damage: float = 1.0
var crit_chance: float = 0.0
var crit_multiplier: float = 1.5
var lifetime: float = 2.0
## Extra targets the projectile passes through before disappearing.
var pierce: int = 0
## > 0: explodes on the first hit, damaging every target of the team in this radius.
var aoe_radius: float = 0.0
var aoe_vfx: String = ""
var source_id: String = ""
var target_team: CombatEntity.Team = CombatEntity.Team.PLAYER
var _hit: Array[Node] = []


static func create(origin: Vector2, dir: Vector2, attack: float, params: Dictionary, source: String,
		hits_team: CombatEntity.Team) -> Projectile:
	var projectile := Projectile.new()
	projectile.global_position = origin
	projectile.direction = dir.normalized()
	projectile.damage = attack
	projectile.speed = float(params.get("speed", 100.0))
	projectile.lifetime = float(params.get("lifetime", 2.0))
	projectile.pierce = int(params.get("pierce", 0))
	projectile.aoe_radius = float(params.get("aoe_radius", 0.0))
	projectile.aoe_vfx = str(params.get("aoe_vfx", ""))
	projectile.source_id = source
	projectile.target_team = hits_team
	projectile.rotation = projectile.direction.angle()
	var sprite := Sprite2D.new()
	var texture_path := str(params.get("sprite", ""))
	if ResourceLoader.exists(texture_path):
		sprite.texture = load(texture_path)
	# Collisions use the feet line (like all bodies); the sprite flies at chest height.
	sprite.position = Vector2(0, -8).rotated(-projectile.rotation)
	projectile.add_child(sprite)
	var shape := CollisionShape2D.new()
	var circle := CircleShape2D.new()
	circle.radius = 3.0
	shape.shape = circle
	projectile.add_child(shape)
	projectile.collision_layer = 0
	projectile.collision_mask = 0
	projectile.set_collision_mask_value(PLAYER_LAYER if hits_team == CombatEntity.Team.PLAYER else ENEMY_LAYER, true)
	projectile.monitorable = false
	return projectile


## Fires a player-side projectile from `shooter` (spawned through its spawn_requested signal).
## `max_range` > 0 overrides the lifetime so range upgrades also extend projectiles.
static func fire_from(shooter: CombatEntity, dir: Vector2, attack: float, params: Dictionary, source: String,
		crit: float, crit_mult: float, max_range: float = 0.0) -> Projectile:
	var hits_team := CombatEntity.Team.ENEMIES if shooter.team == CombatEntity.Team.PLAYER else CombatEntity.Team.PLAYER
	var projectile := create(shooter.global_position, dir, attack, params, source, hits_team)
	projectile.crit_chance = crit
	projectile.crit_multiplier = crit_mult
	if max_range > 0.0:
		projectile.lifetime = max_range * 1.15 / maxf(1.0, projectile.speed)
	shooter.spawn_requested.emit(projectile)
	return projectile


func _ready() -> void:
	body_entered.connect(_on_body_entered)


func _physics_process(delta: float) -> void:
	global_position += direction * speed * delta
	lifetime -= delta
	if lifetime <= 0.0:
		queue_free()


func _on_body_entered(body: Node2D) -> void:
	var target := body as CombatEntity
	if target == null or target.team != target_team or not target.is_alive() or target in _hit:
		return
	if aoe_radius > 0.0:
		CombatSystem.deal_area_damage(get_tree(), TEAM_GROUPS[target_team], global_position, aoe_radius,
			damage, crit_chance, crit_multiplier, Vector2.ZERO, 360.0, source_id)
		if not aoe_vfx.is_empty():
			EventBus.area_effect_shown.emit(aoe_vfx, global_position, aoe_radius)
		queue_free()
		return
	CombatSystem.deal_damage(target, damage, crit_chance, crit_multiplier, source_id)
	_hit.append(target)
	if _hit.size() > pierce:
		queue_free()
