class_name InventoryComponent
extends Node
## In-run access to the player's inventory: picking up, using consumables, equipment bonuses.
## Storage is the Profile repository; this component only applies item effects to the player.

const EQUIPMENT_SOURCE := "equipment"

var body: CombatEntity
var stats: StatsComponent


func setup(owner_body: CombatEntity, owner_stats: StatsComponent) -> void:
	body = owner_body
	stats = owner_stats
	apply_equipment()
	if not EventBus.item_equipped.is_connected(_on_item_equipped):
		EventBus.item_equipped.connect(_on_item_equipped)


func collect(item_id: String, quantity: int) -> void:
	var added := Profile.add_item(item_id, quantity)
	if added > 0:
		EventBus.item_obtained.emit(item_id, added)


func use_item(item_id: String) -> bool:
	var item := Content.get_item(item_id)
	if item == null or not item.is_usable() or Profile.item_count(item_id) <= 0:
		return false
	var applied := false
	for effect in item.effects:
		match str(effect.get("type", "")):
			"heal":
				if body.health.current < body.health.max_health:
					body.health.heal(int(effect.get("value", 0)))
					applied = true
	if not applied:
		return false
	Profile.remove_item(item_id, 1)
	EventBus.item_used.emit(item_id)
	return true


func apply_equipment() -> void:
	stats.remove_modifiers(EQUIPMENT_SOURCE)
	for item_id in Profile.get_equipped_item_ids():
		var item := Content.get_item(item_id)
		if item == null:
			continue
		for effect in item.effects:
			if str(effect.get("type", "")) == "stat":
				stats.add_modifier(EQUIPMENT_SOURCE, str(effect.get("stat", "")), str(effect.get("mode", Stats.MODE_ADD)), float(effect.get("value", 0.0)))


func _on_item_equipped(_item_id: String, _equipped: bool) -> void:
	apply_equipment()
