extends Node
## Autoload "SceneManager": maps screen states to scenes and swaps them with a fade.
## The game scene is loaded in the background while the loading screen is visible.

const GameState := preload("res://scripts/core/game_state_manager.gd")
const GAME_SCENE := "res://scenes/game/game.tscn"
const LOADING_SCENE := "res://scenes/ui/loading_screen.tscn"
const SCREEN_SCENES := {
	GameState.State.MENU: "res://scenes/ui/main_menu.tscn",
	GameState.State.CHARACTER_SELECTION: "res://scenes/ui/character_selection.tscn",
	GameState.State.LEVEL_SELECTION: "res://scenes/ui/level_selection.tscn",
	GameState.State.SETTINGS: "res://scenes/ui/settings.tscn",
	GameState.State.LOADING: LOADING_SCENE,
}
const FADE_TIME := 0.15

var _fade_layer: CanvasLayer
var _fade_rect: ColorRect
var _loading_path: String = ""


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_fade_layer = CanvasLayer.new()
	_fade_layer.layer = 100
	add_child(_fade_layer)
	_fade_rect = ColorRect.new()
	_fade_rect.color = Color(0, 0, 0, 0)
	_fade_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fade_rect.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_fade_layer.add_child(_fade_rect)
	EventBus.game_state_changed.connect(_on_state_changed)
	set_process(false)


func _on_state_changed(_previous: int, current: int) -> void:
	if SCREEN_SCENES.has(current):
		_change_scene(SCREEN_SCENES[current])
	if current == GameState.State.LOADING:
		_start_loading(GAME_SCENE)


func _change_scene(path: String) -> void:
	var tween := create_tween()
	tween.tween_property(_fade_rect, "color:a", 1.0, FADE_TIME)
	await tween.finished
	var err := get_tree().change_scene_to_file(path)
	if err != OK:
		push_error("[SceneManager] cannot open %s: %s" % [path, error_string(err)])
	tween = create_tween()
	tween.tween_property(_fade_rect, "color:a", 0.0, FADE_TIME)


func _start_loading(path: String) -> void:
	_loading_path = path
	ResourceLoader.load_threaded_request(path)
	set_process(true)


func _process(_delta: float) -> void:
	if _loading_path.is_empty():
		set_process(false)
		return
	var status := ResourceLoader.load_threaded_get_status(_loading_path)
	match status:
		ResourceLoader.THREAD_LOAD_LOADED:
			var packed := ResourceLoader.load_threaded_get(_loading_path) as PackedScene
			_loading_path = ""
			set_process(false)
			# Let the loading screen fade in before swapping.
			await get_tree().create_timer(FADE_TIME * 2.0).timeout
			get_tree().change_scene_to_packed(packed)
			GameStateManager.change_state(GameStateManager.State.GAMEPLAY)
		ResourceLoader.THREAD_LOAD_FAILED, ResourceLoader.THREAD_LOAD_INVALID_RESOURCE:
			push_error("[SceneManager] failed to load %s" % _loading_path)
			_loading_path = ""
			set_process(false)
			GameStateManager.change_state(GameStateManager.State.MENU)
