class_name Projectile
extends Area2D
## Straight-flying projectile. Damage is captured at spawn, so it still works if the shooter dies.

const PLAYER_LAYER := 2
const ENEMY_LAYER := 3

var direction: Vector2 = Vector2.RIGHT
var speed: float = 100.0
var damage: float = 1.0
var lifetime: float = 2.0
var source_id: String = ""
var target_team: CombatEntity.Team = CombatEntity.Team.PLAYER


static func create(origin: Vector2, dir: Vector2, attack: float, params: Dictionary, source: String,
		hits_team: CombatEntity.Team) -> Projectile:
	var projectile := Projectile.new()
	projectile.global_position = origin
	projectile.direction = dir.normalized()
	projectile.damage = attack
	projectile.speed = float(params.get("speed", 100.0))
	projectile.lifetime = float(params.get("lifetime", 2.0))
	projectile.source_id = source
	projectile.target_team = hits_team
	projectile.rotation = projectile.direction.angle()
	var sprite := Sprite2D.new()
	var texture_path := str(params.get("sprite", ""))
	if ResourceLoader.exists(texture_path):
		sprite.texture = load(texture_path)
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


func _ready() -> void:
	body_entered.connect(_on_body_entered)


func _physics_process(delta: float) -> void:
	global_position += direction * speed * delta
	lifetime -= delta
	if lifetime <= 0.0:
		queue_free()


func _on_body_entered(body: Node2D) -> void:
	var target := body as CombatEntity
	if target == null or target.team != target_team or not target.is_alive():
		return
	CombatSystem.deal_damage(target, damage, 0.0, 1.0, source_id)
	queue_free()
