class_name SaveData
extends RefCounted
## Shape of the local save (save_version 1).
##
## {
##   save_version, created_at, updated_at,
##   player:           {gold, selected_character_id, total_kills, runs_played},
##   characters:       {character_id: {unlocked}},
##   inventory:        [{item_id, quantity, equipped}],
##   upgrades:         {upgrade_id: level},          # meta upgrades only
##   buildings:        [{id, type, position, level}], # reserved
##   completed_levels: {level_id: {completions, best_time}},
##   settings:         {music_volume, sfx_volume, vibration, auto_attack, language}
## }

const CURRENT_VERSION := 1


static func create_default() -> Dictionary:
	var now := int(Time.get_unix_time_from_system())
	return {
		"save_version": CURRENT_VERSION,
		"created_at": now,
		"updated_at": now,
		"player": {
			"gold": 0,
			"selected_character_id": "",
			"total_kills": 0,
			"runs_played": 0,
		},
		"characters": {},
		"inventory": [],
		"upgrades": {},
		"buildings": [],
		"completed_levels": {},
		"settings": default_settings(),
	}


static func default_settings() -> Dictionary:
	return {
		"music_volume": 0.8,
		"sfx_volume": 1.0,
		"vibration": true,
		"auto_attack": true,
		"language": "ru",
	}
