extends Node
## Autoload "AudioManager": music/SFX buses, volume settings, pooled SFX players.
## Sounds are referenced by ID; a missing file is silently skipped so placeholder builds work.

const MUSIC_BUS := "Music"
const SFX_BUS := "SFX"
const SFX_POOL_SIZE := 8
const SOUNDS := {
	"hit": "res://assets/audio/sfx/hit.ogg",
	"player_hurt": "res://assets/audio/sfx/player_hurt.ogg",
	"pickup": "res://assets/audio/sfx/pickup.ogg",
	"level_up": "res://assets/audio/sfx/level_up.ogg",
	"skill": "res://assets/audio/sfx/skill.ogg",
	"ui_click": "res://assets/audio/sfx/ui_click.ogg",
}

var _sfx_players: Array[AudioStreamPlayer] = []
var _music_player: AudioStreamPlayer
var _cache: Dictionary = {}
var _next_player := 0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_ensure_bus(MUSIC_BUS)
	_ensure_bus(SFX_BUS)
	_music_player = AudioStreamPlayer.new()
	_music_player.bus = MUSIC_BUS
	add_child(_music_player)
	for _i in SFX_POOL_SIZE:
		var player := AudioStreamPlayer.new()
		player.bus = SFX_BUS
		add_child(player)
		_sfx_players.append(player)
	apply_settings(Profile.get_settings())
	EventBus.settings_changed.connect(apply_settings)


func apply_settings(settings: Dictionary) -> void:
	_set_bus_volume(MUSIC_BUS, float(settings.get("music_volume", 0.8)))
	_set_bus_volume(SFX_BUS, float(settings.get("sfx_volume", 1.0)))


func play_sfx(sound_id: String) -> void:
	var stream := _get_stream(sound_id)
	if stream == null:
		return
	var player := _sfx_players[_next_player]
	_next_player = (_next_player + 1) % _sfx_players.size()
	player.stream = stream
	player.play()


func play_music(path: String) -> void:
	if not ResourceLoader.exists(path):
		return
	_music_player.stream = load(path)
	_music_player.play()


func _get_stream(sound_id: String) -> AudioStream:
	if _cache.has(sound_id):
		return _cache[sound_id]
	var path := str(SOUNDS.get(sound_id, ""))
	var stream: AudioStream = load(path) if not path.is_empty() and ResourceLoader.exists(path) else null
	_cache[sound_id] = stream
	return stream


func _ensure_bus(bus_name: String) -> void:
	if AudioServer.get_bus_index(bus_name) != -1:
		return
	AudioServer.add_bus()
	var index := AudioServer.bus_count - 1
	AudioServer.set_bus_name(index, bus_name)
	AudioServer.set_bus_send(index, "Master")


func _set_bus_volume(bus_name: String, linear: float) -> void:
	var index := AudioServer.get_bus_index(bus_name)
	if index == -1:
		return
	AudioServer.set_bus_volume_db(index, linear_to_db(clampf(linear, 0.0, 1.0)))
	AudioServer.set_bus_mute(index, linear <= 0.001)
