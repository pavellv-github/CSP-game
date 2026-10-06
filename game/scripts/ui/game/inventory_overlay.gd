class_name InventoryOverlay
extends Overlay
## Lists the profile inventory; Use / Equip actions are executed by the player's InventoryComponent / Profile.

const State := preload("res://scripts/core/game_state_manager.gd").State

var player: Player


func _init() -> void:
	super(State.INVENTORY)


func refresh() -> void:
	clear_body()
	body.add_child(UiKit.title("Bag"))
	body.add_child(UiKit.label("Gold: %d" % Profile.get_gold(), 10, UiKit.ACCENT, HORIZONTAL_ALIGNMENT_CENTER))
	var entries := Profile.get_inventory()
	if entries.is_empty():
		body.add_child(UiKit.label("Empty", 10, UiKit.TEXT_DIM, HORIZONTAL_ALIGNMENT_CENTER))
	for entry in entries:
		var item := Content.get_item(str(entry["item_id"]))
		if item != null:
			body.add_child(_row(item, int(entry["quantity"]), bool(entry.get("equipped", false))))
	body.add_child(UiKit.button("Close", func() -> void: GameStateManager.change_state(State.GAMEPLAY), 30))


func _row(item: ItemDefinition, quantity: int, equipped: bool) -> Control:
	var row := UiKit.hbox(6)
	row.add_child(UiKit.icon(item.icon, 16))
	var name_label := UiKit.label("%s x%d" % [item.name, quantity] if item.stackable else item.name, 10)
	name_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(name_label)
	if item.is_usable():
		row.add_child(UiKit.button("Use", func() -> void:
			if player != null and player.inventory.use_item(item.id):
				refresh()))
	elif item.is_equippable():
		row.add_child(UiKit.button("Unequip" if equipped else "Equip", func() -> void:
			Profile.set_equipped(item.id, not equipped)
			refresh()))
	return row


func _unhandled_input(event: InputEvent) -> void:
	if visible and (event.is_action_pressed(InputSetup.INVENTORY) or event.is_action_pressed(InputSetup.PAUSE)):
		get_viewport().set_input_as_handled()
		GameStateManager.change_state(State.GAMEPLAY)
