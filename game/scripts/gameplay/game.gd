extends Node2D
## Scene "Game": builds a run from the current LevelDefinition + CharacterDefinition
## and connects systems. Holds per-run state (pending level-ups, run upgrades).

const State := preload("res://scripts/core/game_state_manager.gd").State
const PLAYER_SCENE := preload("res://scenes/player/player.tscn")
const DEATH_DELAY := 0.9

var level: LevelDefinition
var character: CharacterDefinition
var player: Player
var runner: LevelRunner
var loot: LootSystem
var vfx: VfxSpawner
var hud: Hud
var router: InputRouter
var upgrade_overlay: UpgradeOverlay
var inventory_overlay: InventoryOverlay

## upgrade_id -> level taken in this run
var run_upgrades: Dictionary = {}
var pending_level_ups: int = 0
var _finished := false
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	_rng.randomize()
	level = GameManager.get_current_level()
	character = GameManager.get_current_character()
	if level == null or character == null:
		push_error("[Game] no level or character selected")
		return
	var arena := Rect2(Vector2.ZERO, level.map_size)

	var background := Sprite2D.new()
	background.centered = false
	background.texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
	if ResourceLoader.exists(level.map_tile):
		background.texture = load(level.map_tile)
	background.region_enabled = true
	background.region_rect = arena
	background.z_index = -10
	add_child(background)
	RenderingServer.set_default_clear_color(level.background)

	var pickups := Node2D.new()
	pickups.name = "Pickups"
	pickups.z_index = -1
	add_child(pickups)
	var entities := Node2D.new()
	entities.name = "Entities"
	entities.y_sort_enabled = true
	add_child(entities)
	var projectiles := Node2D.new()
	projectiles.name = "Projectiles"
	projectiles.z_index = 5
	add_child(projectiles)
	vfx = VfxSpawner.new()
	vfx.name = "Vfx"
	vfx.z_index = 6
	add_child(vfx)

	player = PLAYER_SCENE.instantiate()
	player.position = level.player_spawn()
	entities.add_child(player)
	player.setup(character, arena.grow(-8.0))
	player.camera.limit_left = 0
	player.camera.limit_top = 0
	player.camera.limit_right = int(arena.size.x)
	player.camera.limit_bottom = int(arena.size.y)
	player.camera.reset_smoothing()
	player.attack_performed.connect(func(direction: Vector2, attack_range: float) -> void:
		vfx.slash(player.global_position, direction, attack_range))
	player.skill_performed.connect(func(skill: SkillDefinition, origin: Vector2, radius: float) -> void:
		vfx.ring(origin, radius, skill.vfx)
		AudioManager.play_sfx("skill"))
	player.experience.leveled_up.connect(_on_player_leveled_up)

	runner = LevelRunner.new()
	runner.name = "LevelRunner"
	add_child(runner)
	runner.setup(level, player, entities, projectiles)
	runner.level_cleared.connect(func() -> void: _finish(true))

	loot = LootSystem.new()
	loot.name = "LootSystem"
	add_child(loot)
	loot.setup(pickups, player, Services.config.get_float("balance.loot_multiplier", 1.0))

	router = InputRouter.new()
	router.name = "InputRouter"
	add_child(router)
	router.controller = player.controller
	router.pause_requested.connect(func() -> void:
		if GameStateManager.is_state(State.GAMEPLAY):
			GameStateManager.change_state(State.PAUSED))
	router.inventory_requested.connect(func() -> void:
		if GameStateManager.is_state(State.GAMEPLAY):
			GameStateManager.change_state(State.INVENTORY))

	_build_ui()
	EventBus.player_died.connect(_on_player_died)
	EventBus.run_started.emit(level.id, character.id)
	hud.show_banner(level.name)


func _build_ui() -> void:
	var layer := CanvasLayer.new()
	layer.name = "UI"
	layer.process_mode = Node.PROCESS_MODE_ALWAYS
	add_child(layer)
	var root := Control.new()
	root.name = "Root"
	root.theme = UiKit.shared_theme()
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(root)
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	hud = Hud.new()
	hud.name = "HUD"
	root.add_child(hud)
	hud.setup(router, player)
	root.add_child(PauseOverlay.new())
	upgrade_overlay = UpgradeOverlay.new()
	upgrade_overlay.upgrade_chosen.connect(_on_upgrade_chosen)
	root.add_child(upgrade_overlay)
	inventory_overlay = InventoryOverlay.new()
	inventory_overlay.player = player
	root.add_child(inventory_overlay)
	root.add_child(LevelCompleteOverlay.new())
	root.add_child(GameOverOverlay.new())


func _on_player_leveled_up(_new_level: int) -> void:
	pending_level_ups += 1
	if GameStateManager.is_state(State.GAMEPLAY):
		_offer_upgrade.call_deferred()


func _offer_upgrade() -> void:
	if _finished or pending_level_ups <= 0:
		return
	var count := Services.config.get_int("run.upgrade_choices", 3)
	var choices := UpgradeService.roll_choices(run_upgrades, count, _rng)
	if choices.is_empty():
		pending_level_ups = 0
		return
	upgrade_overlay.set_choices(choices, run_upgrades, player.experience.level)
	if not GameStateManager.is_state(State.UPGRADE):
		GameStateManager.change_state(State.UPGRADE)


func _on_upgrade_chosen(upgrade_id: String) -> void:
	var upgrade := Content.get_upgrade(upgrade_id)
	if upgrade == null:
		return
	UpgradeService.apply(upgrade, player.stats, player.health, player.skills)
	run_upgrades[upgrade_id] = int(run_upgrades.get(upgrade_id, 0)) + 1
	EventBus.upgrade_selected.emit(upgrade_id, int(run_upgrades[upgrade_id]))
	pending_level_ups -= 1
	if pending_level_ups > 0:
		_offer_upgrade()
	else:
		GameStateManager.change_state(State.GAMEPLAY)


func _on_player_died(_reason: String) -> void:
	get_tree().create_timer(DEATH_DELAY).timeout.connect(_finish.bind(false))


func _finish(victory: bool) -> void:
	if _finished:
		return
	_finished = true
	pending_level_ups = 0
	# The outcome can arrive while an overlay is open (e.g. boss died during level-up).
	if not GameStateManager.is_state(State.GAMEPLAY):
		GameStateManager.change_state(State.GAMEPLAY)
	GameManager.finish_run(victory, {
		"kills": runner.kills,
		"time": runner.elapsed,
		"player_level": player.experience.level,
	})
