extends TestCase

const TEST_SAVE := "user://test_savegame.dat"

var _original_path: String
var _original_data: Dictionary


func before_each() -> void:
	_original_path = SaveManager.save_path
	_original_data = SaveManager.data
	SaveManager.save_path = TEST_SAVE
	SaveManager.data = SaveData.create_default()


func after_each() -> void:
	for path in [TEST_SAVE, TEST_SAVE.get_basename() + ".bak", TEST_SAVE + ".tmp"]:
		if FileAccess.file_exists(path):
			DirAccess.remove_absolute(ProjectSettings.globalize_path(path))
	SaveManager.save_path = _original_path
	SaveManager.data = _original_data


func test_save_roundtrip() -> void:
	Profile.add_gold(42)
	assert_true(SaveManager.save_game())
	SaveManager.data = {}
	SaveManager.load_game()
	assert_eq(Profile.get_gold(), 42)
	assert_eq(int(SaveManager.data["save_version"]), SaveManager.CURRENT_SAVE_VERSION)


func test_migration_from_unversioned_save() -> void:
	var migrated := SaveMigrator.create_default().migrate({"player": {"gold": 7}}, 1)
	assert_eq(int(migrated["save_version"]), 1)
	assert_eq(int(migrated["player"]["gold"]), 7)
	assert_true(migrated.has("settings"), "missing sections are filled")


func test_migration_chain_runs_in_order() -> void:
	var migrator := SaveMigrator.new()
	migrator.register(1, func(d: Dictionary) -> Dictionary:
		d["trace"] = "1"
		return d)
	migrator.register(2, func(d: Dictionary) -> Dictionary:
		d["trace"] += ">2"
		return d)
	var result := migrator.migrate({"save_version": 1}, 3)
	assert_eq(result["trace"], "1>2")
	assert_eq(int(result["save_version"]), 3)


func test_migration_refuses_newer_save() -> void:
	assert_true(SaveMigrator.create_default().migrate({"save_version": 99}, 1).is_empty())


func test_corrupted_save_falls_back_to_backup() -> void:
	Profile.add_gold(5)
	SaveManager.save_game()
	Profile.add_gold(5)
	SaveManager.save_game() # backup now holds gold = 5
	var file := FileAccess.open(TEST_SAVE, FileAccess.WRITE)
	file.store_string("{not json")
	file.close()
	SaveManager.load_game()
	assert_eq(Profile.get_gold(), 5)


func test_inventory_stacking_and_currency() -> void:
	assert_eq(Profile.add_item("item_health_potion", 25), 20, "max_stack is 20")
	assert_eq(Profile.item_count("item_health_potion"), 20)
	Profile.add_item("item_gold_coin", 3)
	assert_eq(Profile.get_gold(), 3)
	assert_true(Profile.remove_item("item_health_potion", 2))
	assert_eq(Profile.item_count("item_health_potion"), 18)
	assert_false(Profile.remove_item("item_health_potion", 100))


func test_level_unlock_chain() -> void:
	assert_true(Profile.is_level_unlocked("level_forest_01"))
	assert_false(Profile.is_level_unlocked("level_forest_02"))
	Profile.mark_level_completed("level_forest_01", 100.0)
	assert_true(Profile.is_level_unlocked("level_forest_02"))


func test_meta_upgrade_purchase() -> void:
	var upgrade := Content.get_upgrade("upgrade_meta_damage")
	assert_false(UpgradeService.buy_meta(upgrade.id), "no gold yet")
	Profile.add_gold(upgrade.cost_for_level(0))
	assert_true(UpgradeService.buy_meta(upgrade.id))
	assert_eq(Profile.get_upgrade_level(upgrade.id), 1)
	assert_eq(Profile.get_gold(), 0)


func test_meta_prerequisites() -> void:
	var guard := Content.get_upgrade("upgrade_meta_defense")
	Profile.add_gold(10000)
	assert_false(UpgradeService.buy_meta(guard.id), "requires Vitality first")
	assert_true(UpgradeService.buy_meta("upgrade_meta_health"))
	assert_true(UpgradeService.buy_meta(guard.id))


func test_run_upgrade_choices_skip_maxed() -> void:
	var owned := {}
	for upgrade in Content.get_upgrades_by_scope(UpgradeDefinition.SCOPE_RUN):
		owned[upgrade.id] = upgrade.max_level
	owned.erase("upgrade_attack_01")
	var choices := UpgradeService.roll_choices(owned, 3, RandomNumberGenerator.new())
	assert_eq(choices.size(), 1)
	assert_eq(choices[0].id, "upgrade_attack_01")


func test_state_transitions_table() -> void:
	var State: Dictionary = GameStateManager.State
	assert_true(State.GAMEPLAY in GameStateManager.TRANSITIONS[State.LOADING])
	assert_false(State.GAMEPLAY in GameStateManager.TRANSITIONS[State.MENU])
	for state: int in State.values():
		assert_true(GameStateManager.TRANSITIONS.has(state), "state %s has transitions" % GameStateManager.state_name(state))
