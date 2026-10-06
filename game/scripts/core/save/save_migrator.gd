class_name SaveMigrator
extends RefCounted
## Upgrades save data step by step: v1 -> v2 -> v3 ...
## To change the save structure: bump SaveManager.CURRENT_SAVE_VERSION and register
## a step for the previous version in `create_default()`.

var _steps: Dictionary = {}


## `step` receives the data of `from_version` and returns data of `from_version + 1`.
func register(from_version: int, step: Callable) -> void:
	_steps[from_version] = step


func migrate(data: Dictionary, target_version: int) -> Dictionary:
	var result := data.duplicate(true)
	var version := int(result.get("save_version", 0))
	if version > target_version:
		push_error("[Save] save_version %d is newer than supported %d" % [version, target_version])
		return {}
	while version < target_version:
		if not _steps.has(version):
			push_error("[Save] no migration from save_version %d" % version)
			return {}
		var step: Callable = _steps[version]
		result = step.call(result)
		version += 1
		result["save_version"] = version
	return result


static func create_default() -> SaveMigrator:
	var migrator := SaveMigrator.new()
	# v0 -> v1: saves written before versioning existed get the full v1 structure.
	migrator.register(0, func(data: Dictionary) -> Dictionary:
		var upgraded := SaveData.create_default()
		upgraded.merge(data, true)
		return upgraded)
	# Example for the next change:
	# migrator.register(1, func(data: Dictionary) -> Dictionary:
	#     data["player"]["gems"] = 0
	#     return data)
	return migrator
