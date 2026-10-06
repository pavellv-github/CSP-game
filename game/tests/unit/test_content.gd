extends TestCase


func test_bundled_content_is_valid() -> void:
	assert_eq(Content.errors.size(), 0, "\n  " + "\n  ".join(Content.errors))


func test_drafts_are_hidden_from_client() -> void:
	assert_eq(Content.get_character("character_mage"), null, "draft character must not be loaded")
	assert_true(Content.get_character("character_warrior") != null)


func test_drafts_are_visible_when_requested() -> void:
	var source := LocalJsonContentSource.new()
	var repository := DefinitionRepository.new("characters", func(d: Dictionary) -> ContentDefinition: return CharacterDefinition.new(d))
	repository.load_entries(source.load_collection("characters"), true)
	assert_true(repository.has_id("character_mage"))


func test_duplicate_ids_are_reported() -> void:
	var repository := DefinitionRepository.new("items", func(d: Dictionary) -> ContentDefinition: return ItemDefinition.new(d))
	var errors := repository.load_entries([{"id": "item_a"}, {"id": "item_a"}])
	assert_eq(errors.size(), 1)
	assert_eq(repository.size(), 1)


func test_mvp_scope_content_present() -> void:
	assert_true(Content.levels.size() >= 1 and Content.levels.size() <= 3, "1-3 levels")
	var regular := 0
	var bosses := 0
	for definition in Content.enemies.get_all():
		if (definition as EnemyDefinition).is_boss:
			bosses += 1
		else:
			regular += 1
	assert_true(regular >= 3 and regular <= 5, "3-5 enemy types, got %d" % regular)
	assert_true(bosses >= 1, "at least one boss")


func test_xp_curve_from_data() -> void:
	var curve := Content.xp_curve
	assert_eq(curve.required_xp(1), 0)
	assert_eq(curve.required_xp(2), 12)
	assert_eq(curve.level_for_xp(11), 1)
	assert_eq(curve.level_for_xp(12), 2)
	assert_true(curve.required_xp(25) > curve.required_xp(20), "curve continues past the last row")


func test_loot_table_roll_respects_entries() -> void:
	var table := LootTableDefinition.new({"id": "t", "rolls": 5, "entries": [{"item_id": "item_gold_coin", "weight": 1, "min": 2, "max": 2}]})
	var rng := RandomNumberGenerator.new()
	var drops := table.roll(rng)
	assert_eq(drops.size(), 5)
	assert_eq(int(drops[0]["quantity"]), 2)


func test_remote_config_overrides_defaults() -> void:
	var config := RemoteConfigService.new({"balance": {"xp_multiplier": 1.0}, "feature_flags": {"x": false}})
	assert_almost(config.get_float("balance.xp_multiplier"), 1.0)
	config._overrides = {"balance": {"xp_multiplier": 2.0}}
	assert_almost(config.get_float("balance.xp_multiplier"), 2.0)
	assert_false(config.is_feature_enabled("x"))
	assert_eq(config.get_value("missing.key", 7), 7)


func test_sprite_sheet_rows_and_legacy() -> void:
	var sheet := SpriteSheet.from_data({"sprite": "x.png", "frame_size": [32, 32], "animations": {
		"idle": {"row": 0, "frames": 4, "fps": 6}, "attack": {"row": 2, "frames": 5, "fps": 12, "hit_frame": 2}}})
	assert_eq(sheet.frame_size, Vector2i(32, 32))
	assert_eq(int(sheet.animations["attack"]["row"]), 2)
	assert_eq(int(sheet.animations["attack"]["hit_frame"]), 2)
	var legacy := SpriteSheet.from_data({"sprite": "y.png", "frames": 2})
	assert_true(legacy.has_animation("walk") and legacy.has_animation("idle"))
	assert_eq(int(legacy.animations["walk"]["frames"]), 2)


func test_all_sprite_sheets_fit_their_textures() -> void:
	for definition in Content.characters.get_all():
		assert_eq((definition as CharacterDefinition).sheet.validate(definition.id), [] as Array[String])
	for definition in Content.enemies.get_all():
		assert_eq((definition as EnemyDefinition).sheet.validate(definition.id), [] as Array[String])
