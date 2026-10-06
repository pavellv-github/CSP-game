extends Node
## Autoload "Profile": player data repository (gold, inventory, meta upgrades, progress, settings).
## Gameplay and UI use this API only; storage is SaveManager today and can be backed by
## cloud save later without touching callers.

const AUTOSAVE_INTERVAL := 30.0

var _dirty := false
var _autosave_timer: Timer


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_ensure_defaults()
	_autosave_timer = Timer.new()
	_autosave_timer.wait_time = AUTOSAVE_INTERVAL
	_autosave_timer.timeout.connect(flush)
	add_child(_autosave_timer)
	_autosave_timer.start()


## Writes pending changes to storage.
func flush() -> void:
	if _dirty:
		_dirty = false
		SaveManager.save_game()


func mark_dirty() -> void:
	_dirty = true


func reset_progress() -> void:
	SaveManager.reset()
	_ensure_defaults()
	EventBus.gold_changed.emit(get_gold())
	EventBus.settings_changed.emit(get_settings())


# --- Gold -------------------------------------------------------------------

func get_gold() -> int:
	return int(_player().get("gold", 0))


func add_gold(amount: int) -> void:
	if amount <= 0:
		return
	_player()["gold"] = get_gold() + amount
	mark_dirty()
	EventBus.gold_changed.emit(get_gold())


func spend_gold(amount: int) -> bool:
	if amount < 0 or get_gold() < amount:
		return false
	_player()["gold"] = get_gold() - amount
	mark_dirty()
	EventBus.gold_changed.emit(get_gold())
	return true


# --- Inventory --------------------------------------------------------------

## Returns copies of [{item_id, quantity, equipped}].
func get_inventory() -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	for entry: Dictionary in _inventory():
		result.append(entry.duplicate())
	return result


func item_count(item_id: String) -> int:
	var total := 0
	for entry: Dictionary in _inventory():
		if entry.get("item_id") == item_id:
			total += int(entry.get("quantity", 0))
	return total


## Adds items respecting stack rules. Currency goes to gold. Returns quantity actually added.
func add_item(item_id: String, quantity: int) -> int:
	var item := Content.get_item(item_id)
	if item == null or quantity <= 0:
		return 0
	if item.type == ItemDefinition.TYPE_CURRENCY:
		add_gold(quantity)
		return quantity
	var added := 0
	if item.stackable:
		var entry := _find_entry(item_id)
		if entry.is_empty():
			entry = {"item_id": item_id, "quantity": 0, "equipped": false}
			_inventory().append(entry)
		var before := int(entry["quantity"])
		entry["quantity"] = mini(item.max_stack, before + quantity)
		added = int(entry["quantity"]) - before
	else:
		for _i in quantity:
			_inventory().append({"item_id": item_id, "quantity": 1, "equipped": false})
		added = quantity
	if added > 0:
		mark_dirty()
	return added


func remove_item(item_id: String, quantity: int = 1) -> bool:
	if item_count(item_id) < quantity:
		return false
	var remaining := quantity
	var inventory := _inventory()
	for i in range(inventory.size() - 1, -1, -1):
		var entry: Dictionary = inventory[i]
		if entry.get("item_id") != item_id:
			continue
		var take := mini(remaining, int(entry["quantity"]))
		entry["quantity"] = int(entry["quantity"]) - take
		remaining -= take
		if int(entry["quantity"]) <= 0:
			inventory.remove_at(i)
		if remaining == 0:
			break
	mark_dirty()
	return true


## Equips one item of the given type slot, unequipping the previous one in that slot.
func set_equipped(item_id: String, equipped: bool) -> void:
	var item := Content.get_item(item_id)
	if item == null or not item.is_equippable():
		return
	for entry: Dictionary in _inventory():
		var other := Content.get_item(str(entry.get("item_id")))
		if other != null and other.type == item.type:
			entry["equipped"] = false
	if equipped:
		var entry := _find_entry(item_id)
		if not entry.is_empty():
			entry["equipped"] = true
	mark_dirty()
	EventBus.item_equipped.emit(item_id, equipped)


func get_equipped_item_ids() -> Array[String]:
	var result: Array[String] = []
	for entry: Dictionary in _inventory():
		if bool(entry.get("equipped", false)):
			result.append(str(entry.get("item_id")))
	return result


# --- Characters -------------------------------------------------------------

func is_character_unlocked(character_id: String) -> bool:
	var character := Content.get_character(character_id)
	if character == null:
		return false
	var state: Dictionary = _characters().get(character_id, {})
	if bool(state.get("unlocked", false)):
		return true
	return _is_condition_met(character.unlock_condition)


func unlock_character(character_id: String) -> void:
	_characters()[character_id] = {"unlocked": true}
	mark_dirty()
	EventBus.character_unlocked.emit(character_id)


func get_selected_character_id() -> String:
	var selected := str(_player().get("selected_character_id", ""))
	if selected.is_empty() or Content.get_character(selected) == null:
		selected = str(Services.config.get_value("run.default_character_id", "character_warrior"))
	return selected


func select_character(character_id: String) -> void:
	if not is_character_unlocked(character_id):
		return
	_player()["selected_character_id"] = character_id
	mark_dirty()
	EventBus.character_selected.emit(character_id)


# --- Levels -----------------------------------------------------------------

func is_level_unlocked(level_id: String) -> bool:
	var level := Content.get_level(level_id)
	return level != null and _is_condition_met(level.unlock_condition)


func is_level_completed(level_id: String) -> bool:
	return _completed_levels().has(level_id)


func mark_level_completed(level_id: String, time_seconds: float) -> void:
	var record: Dictionary = _completed_levels().get(level_id, {"completions": 0, "best_time": 0.0})
	record["completions"] = int(record.get("completions", 0)) + 1
	var best := float(record.get("best_time", 0.0))
	record["best_time"] = time_seconds if best <= 0.0 else minf(best, time_seconds)
	_completed_levels()[level_id] = record
	mark_dirty()
	_unlock_characters_by_conditions()


# --- Meta upgrades ----------------------------------------------------------

func get_upgrade_level(upgrade_id: String) -> int:
	return int(_upgrades().get(upgrade_id, 0))


func get_meta_upgrade_levels() -> Dictionary:
	return _upgrades().duplicate()


func set_upgrade_level(upgrade_id: String, level: int) -> void:
	_upgrades()[upgrade_id] = level
	mark_dirty()


# --- Stats ------------------------------------------------------------------

func record_run(kills: int) -> void:
	_player()["total_kills"] = int(_player().get("total_kills", 0)) + kills
	_player()["runs_played"] = int(_player().get("runs_played", 0)) + 1
	mark_dirty()


# --- Settings ---------------------------------------------------------------

func get_settings() -> Dictionary:
	return (SaveManager.data["settings"] as Dictionary).duplicate()


func get_setting(key: String, default: Variant = null) -> Variant:
	return (SaveManager.data["settings"] as Dictionary).get(key, default)


func set_setting(key: String, value: Variant) -> void:
	(SaveManager.data["settings"] as Dictionary)[key] = value
	mark_dirty()
	EventBus.settings_changed.emit(get_settings())


# --- Internals --------------------------------------------------------------

func _is_condition_met(condition: Dictionary) -> bool:
	match str(condition.get("type", "default")):
		"default":
			return true
		"level_completed":
			return is_level_completed(str(condition.get("level_id", "")))
		_:
			return false


func _unlock_characters_by_conditions() -> void:
	for definition in Content.characters.get_all():
		var state: Dictionary = _characters().get(definition.id, {})
		if not bool(state.get("unlocked", false)) and is_character_unlocked(definition.id):
			unlock_character(definition.id)


func _ensure_defaults() -> void:
	for definition in Content.characters.get_all():
		var character := definition as CharacterDefinition
		if str(character.unlock_condition.get("type", "default")) == "default" and not _characters().has(character.id):
			_characters()[character.id] = {"unlocked": true}


func _find_entry(item_id: String) -> Dictionary:
	for entry: Dictionary in _inventory():
		if entry.get("item_id") == item_id:
			return entry
	return {}


func _player() -> Dictionary:
	return SaveManager.data["player"]


func _inventory() -> Array:
	return SaveManager.data["inventory"]


func _characters() -> Dictionary:
	return SaveManager.data["characters"]


func _upgrades() -> Dictionary:
	return SaveManager.data["upgrades"]


func _completed_levels() -> Dictionary:
	return SaveManager.data["completed_levels"]
