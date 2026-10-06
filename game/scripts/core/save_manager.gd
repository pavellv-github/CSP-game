extends Node
## Autoload "SaveManager": local, versioned storage for player data (user://savegame.dat).
## Writes are atomic (temp file + rename) and the previous save is kept as a backup.
## Gameplay never talks to SaveManager directly — it goes through Profile (ProfileRepository).

signal loaded
signal saved

const SAVE_PATH := "user://savegame.dat"
const CURRENT_SAVE_VERSION := SaveData.CURRENT_VERSION

var save_path: String = SAVE_PATH
var data: Dictionary = {}
var migrator := SaveMigrator.create_default()


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	load_game()


func load_game() -> void:
	var loaded_data := _read(save_path)
	if loaded_data.is_empty():
		loaded_data = _read(_backup_path())
		if not loaded_data.is_empty():
			push_warning("[Save] main save unreadable, restored from backup")
	if loaded_data.is_empty():
		data = SaveData.create_default()
	else:
		var migrated := migrator.migrate(loaded_data, CURRENT_SAVE_VERSION)
		if migrated.is_empty():
			push_error("[Save] migration failed, starting a fresh profile (old file kept as backup)")
			_copy(save_path, _backup_path())
			data = SaveData.create_default()
		else:
			data = migrated
	_fill_missing_keys()
	loaded.emit()


func save_game() -> bool:
	data["save_version"] = CURRENT_SAVE_VERSION
	data["updated_at"] = int(Time.get_unix_time_from_system())
	var tmp_path := save_path + ".tmp"
	var file := FileAccess.open(tmp_path, FileAccess.WRITE)
	if file == null:
		push_error("[Save] cannot write %s: %s" % [tmp_path, error_string(FileAccess.get_open_error())])
		return false
	file.store_string(JSON.stringify(data, "\t"))
	file.close()
	if FileAccess.file_exists(save_path):
		_copy(save_path, _backup_path())
	var err := DirAccess.rename_absolute(ProjectSettings.globalize_path(tmp_path), ProjectSettings.globalize_path(save_path))
	if err != OK:
		push_error("[Save] cannot replace save: %s" % error_string(err))
		return false
	saved.emit()
	return true


func reset() -> void:
	data = SaveData.create_default()
	save_game()


func _read(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	return parsed if parsed is Dictionary else {}


func _fill_missing_keys() -> void:
	var defaults := SaveData.create_default()
	data.merge(defaults, false)
	(data["player"] as Dictionary).merge(defaults["player"], false)
	(data["settings"] as Dictionary).merge(defaults["settings"], false)


func _backup_path() -> String:
	return save_path.get_basename() + ".bak"


func _copy(from_path: String, to_path: String) -> void:
	DirAccess.copy_absolute(ProjectSettings.globalize_path(from_path), ProjectSettings.globalize_path(to_path))
