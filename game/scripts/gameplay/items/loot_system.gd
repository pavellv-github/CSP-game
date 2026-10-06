class_name LootSystem
extends Node
## Enemy killed -> roll its loot table -> spawn pickups. Knows nothing about enemies themselves.

var container: Node2D
var player: Player
var quantity_multiplier: float = 1.0
var _rng := RandomNumberGenerator.new()


func setup(pickup_container: Node2D, target_player: Player, multiplier: float) -> void:
	container = pickup_container
	player = target_player
	quantity_multiplier = multiplier
	_rng.randomize()
	EventBus.enemy_killed.connect(_on_enemy_killed)


func _on_enemy_killed(_enemy_id: String, position: Vector2, _xp: int, loot_table_id: String, _is_boss: bool) -> void:
	var table := Content.get_loot_table(loot_table_id)
	if table == null:
		return
	for drop in table.roll(_rng, quantity_multiplier):
		var item := Content.get_item(str(drop["item_id"]))
		if item == null:
			continue
		var offset := Vector2(_rng.randf_range(-8, 8), _rng.randf_range(-8, 8))
		container.add_child(Pickup.create(item, int(drop["quantity"]), position + offset, player))
