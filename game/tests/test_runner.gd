extends Node
## Runs all unit tests, then a smoke test that plays the real game loop headless:
## Menu -> Character selection -> Level selection -> Game -> level-up -> boss -> Victory,
## then a second run that ends in Game Over.
## Usage: godot --headless --path game res://tests/test_runner.tscn   (exit code 0 = success)

const State := preload("res://scripts/core/game_state_manager.gd").State
const UNIT_DIR := "res://tests/unit"
const SMOKE_SAVE := "user://smoke_savegame.dat"
const STEP_TIMEOUT := 20.0

var _failures: Array[String] = []


func _ready() -> void:
	get_tree().root.theme = UiKit.shared_theme()
	# Scene changes free the current scene: hand that role to a placeholder so the runner survives.
	await get_tree().process_frame
	var placeholder := Node.new()
	placeholder.name = "Placeholder"
	get_tree().root.add_child(placeholder)
	get_tree().current_scene = placeholder
	_run_unit_tests()
	await _run_smoke_test()
	_cleanup_save()
	if _failures.is_empty():
		print("\nALL TESTS PASSED")
		get_tree().quit(0)
	else:
		printerr("\n%d FAILURE(S):" % _failures.size())
		for failure in _failures:
			printerr("  - " + failure)
		get_tree().quit(1)


func _run_unit_tests() -> void:
	var files := DirAccess.get_files_at(UNIT_DIR)
	for file_name in files:
		if not file_name.ends_with(".gd"):
			continue
		var script: GDScript = load(UNIT_DIR.path_join(file_name))
		var test: TestCase = script.new()
		var result := test.run_all()
		print("[unit] %s: %d passed, %d failed" % [file_name, result["passed"], result["failed"]])
		for failure in test.failures:
			_failures.append("%s: %s" % [file_name, failure])


func _run_smoke_test() -> void:
	SaveManager.save_path = SMOKE_SAVE
	SaveManager.data = SaveData.create_default()
	Profile._ensure_defaults()
	var analytics := Services.debug_analytics
	analytics.history.clear()

	_expect(GameStateManager.change_state(State.MENU), "BOOT -> MENU")
	await _wait_for_scene("MainMenu")
	_expect(GameStateManager.change_state(State.CHARACTER_SELECTION), "MENU -> CHARACTER_SELECTION")
	await _wait_for_scene("CharacterSelection")
	_expect(GameStateManager.change_state(State.LEVEL_SELECTION), "-> LEVEL_SELECTION")
	await _wait_for_scene("LevelSelection")

	# Run 1: survive, level up, kill the boss.
	GameManager.start_run("level_forest_01")
	await _wait_for_scene("Game")
	await _wait_until(func() -> bool: return GameStateManager.is_state(State.GAMEPLAY), "gameplay started")
	var game := get_tree().current_scene
	var player: Player = game.player
	player.health.setup(100000) # keep the hero alive for the smoke run
	await _frames(240)
	_expect(get_tree().get_node_count_in_group(&"enemies") > 0, "enemies spawned")

	player.experience.add_xp(20)
	await _wait_until(func() -> bool: return GameStateManager.is_state(State.UPGRADE), "level-up opens upgrade choice")
	var overlay: UpgradeOverlay = game.upgrade_overlay
	_expect(not overlay.choices.is_empty(), "upgrade choices offered")
	var damage_before := player.stats.get_stat(Stats.DAMAGE)
	overlay.upgrade_chosen.emit("upgrade_attack_01")
	await _wait_until(func() -> bool: return GameStateManager.is_state(State.GAMEPLAY), "back to gameplay after upgrade")
	_expect(player.stats.get_stat(Stats.DAMAGE) > damage_before, "upgrade applied")

	var runner: LevelRunner = game.runner
	runner.elapsed = game.level.duration
	await _wait_until(func() -> bool: return runner.boss != null, "boss spawned")
	CombatSystem.deal_damage(runner.boss, 1000000.0)
	await _wait_until(func() -> bool: return GameStateManager.is_state(State.LEVEL_COMPLETE), "victory")
	_expect(Profile.is_level_completed("level_forest_01"), "level marked completed")
	_expect(Profile.get_gold() >= 50, "level reward granted")
	_expect(FileAccess.file_exists(SMOKE_SAVE), "progress saved")

	# Run 2: die -> Game Over.
	_expect(GameStateManager.change_state(State.LEVEL_SELECTION), "LEVEL_COMPLETE -> LEVEL_SELECTION")
	await _wait_for_scene("LevelSelection")
	GameManager.start_run("level_forest_02")
	await _wait_for_scene("Game")
	await _wait_until(func() -> bool: return GameStateManager.is_state(State.GAMEPLAY), "second run started")
	game = get_tree().current_scene
	await _frames(30)
	game.player.health.apply_damage(1000000, "test")
	await _wait_until(func() -> bool: return GameStateManager.is_state(State.GAME_OVER), "game over")
	_expect(GameStateManager.change_state(State.MENU), "GAME_OVER -> MENU")
	await _wait_for_scene("MainMenu")

	await _smoke_every_hero()

	var events: Array[String] = []
	for entry in analytics.history:
		events.append(str(entry["name"]))
	for expected in ["game_started", "level_up", "upgrade_selected", "boss_killed", "game_completed", "game_failed"]:
		_expect(expected in events, "analytics event '%s' sent" % expected)
	print("[smoke] done, %d analytics events" % events.size())


## Every hero: start a run, attack and use the skill next to an enemy; checks the attack and
## skill actually produce their effect (projectile, companion, healing, damage).
func _smoke_every_hero() -> void:
	for definition in Content.characters.get_all():
		var character := definition as CharacterDefinition
		Profile.select_character(character.id)
		_expect(GameStateManager.change_state(State.LEVEL_SELECTION), "%s: -> LEVEL_SELECTION" % character.id)
		await _wait_for_scene("LevelSelection")
		GameManager.start_run("level_forest_01")
		await _wait_for_scene("Game")
		await _wait_until(func() -> bool: return GameStateManager.is_state(State.GAMEPLAY), "%s run started" % character.id)
		var game := get_tree().current_scene
		var player: Player = game.player
		_expect(player.definition.id == character.id, "%s is the played hero" % character.id)
		player.health.setup(100000)
		var enemy: Enemy = game.runner.spawn_enemy("enemy_slime", player.global_position + Vector2(30, 0))
		enemy.health.setup(100000)
		var enemy_health := enemy.health.current
		player.combat.cooldown_left = 0.0
		player.combat.manual_attack(Vector2.RIGHT)
		await _frames(int(player.combat.release_delay * 60.0) + 2) # projectile leaves on the hit frame
		if character.attack_type == "projectile":
			_expect(game.get_node("Projectiles").get_child_count() > 0, "%s fires a projectile" % character.id)
		player.health.apply_damage(30)
		player.health.invulnerable_time = 0.0
		var health_before := player.health.current
		_expect(player.skills.use(0), "%s uses the skill" % character.id)
		await _frames(45)
		var skill := Content.get_skill(character.skills[0])
		match skill.effect:
			SkillDefinition.EFFECT_SUMMON:
				var companions := game.get_node("Entities").get_children().filter(func(n: Node) -> bool: return n is Companion)
				_expect(not companions.is_empty(), "%s summons a companion" % character.id)
			SkillDefinition.EFFECT_HEAL_WAVE:
				_expect(player.health.current > health_before, "%s heals" % character.id)
		_expect(enemy.health.current < enemy_health, "%s damages the enemy" % character.id)
		GameStateManager.change_state(State.PAUSED)
		_expect(GameStateManager.change_state(State.MENU), "%s: leave run" % character.id)
		await _wait_for_scene("MainMenu")
		GameStateManager.change_state(State.CHARACTER_SELECTION)
		await _wait_for_scene("CharacterSelection")
	Profile.select_character("character_warrior")


func _wait_for_scene(scene_name: String) -> void:
	await _wait_until(func() -> bool:
		var scene := get_tree().current_scene
		return scene != null and scene.name == scene_name, "scene %s" % scene_name)


func _wait_until(condition: Callable, what: String) -> void:
	var waited := 0.0
	while not condition.call():
		await get_tree().process_frame
		waited += get_process_delta_time()
		if waited > STEP_TIMEOUT:
			_failures.append("[smoke] timeout waiting for: " + what)
			return
	print("[smoke] ok: " + what)


func _frames(count: int) -> void:
	for _i in count:
		await get_tree().physics_frame


func _expect(condition: bool, what: String) -> void:
	if not condition:
		_failures.append("[smoke] " + what)


func _cleanup_save() -> void:
	for path in [SMOKE_SAVE, SMOKE_SAVE.get_basename() + ".bak"]:
		if FileAccess.file_exists(path):
			DirAccess.remove_absolute(ProjectSettings.globalize_path(path))
