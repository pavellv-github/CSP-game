class_name Pickup
extends Node2D
## Dropped loot. Flies to the player once inside the player's pickup radius.

const COLLECT_DISTANCE := 6.0
const MAGNET_ACCELERATION := 600.0
const LIFETIME := 90.0

var item_id: String = ""
var quantity: int = 1
var player: Player
var _magnet: bool = false
var _speed: float = 0.0
var _age: float = 0.0


static func create(item: ItemDefinition, amount: int, origin: Vector2, target: Player) -> Pickup:
	var pickup := Pickup.new()
	pickup.item_id = item.id
	pickup.quantity = amount
	pickup.player = target
	pickup.global_position = origin
	var sprite := Sprite2D.new()
	if ResourceLoader.exists(item.icon):
		sprite.texture = load(item.icon)
	if item.type != ItemDefinition.TYPE_CURRENCY:
		sprite.scale = Vector2(0.75, 0.75)
	pickup.add_child(sprite)
	return pickup


func _physics_process(delta: float) -> void:
	_age += delta
	if _age > LIFETIME:
		queue_free()
		return
	if player == null or not is_instance_valid(player) or not player.is_alive():
		return
	var distance := global_position.distance_to(player.global_position)
	if not _magnet and distance <= player.stats.get_stat(Stats.PICKUP_RADIUS):
		_magnet = true
	if _magnet:
		_speed += MAGNET_ACCELERATION * delta
		global_position = global_position.move_toward(player.global_position, _speed * delta)
		if global_position.distance_to(player.global_position) <= COLLECT_DISTANCE:
			player.inventory.collect(item_id, quantity)
			AudioManager.play_sfx("pickup")
			queue_free()
