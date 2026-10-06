extends Node
## Autoload "Content": the single entry point to game content.
## Gameplay code asks for definitions by ID: Content.get_character("character_warrior").

var characters := DefinitionRepository.new("characters", func(d: Dictionary) -> ContentDefinition: return CharacterDefinition.new(d))
var enemies := DefinitionRepository.new("enemies", func(d: Dictionary) -> ContentDefinition: return EnemyDefinition.new(d))
var items := DefinitionRepository.new("items", func(d: Dictionary) -> ContentDefinition: return ItemDefinition.new(d))
var loot_tables := DefinitionRepository.new("loot_tables", func(d: Dictionary) -> ContentDefinition: return LootTableDefinition.new(d))
var levels := DefinitionRepository.new("levels", func(d: Dictionary) -> ContentDefinition: return LevelDefinition.new(d))
var skills := DefinitionRepository.new("skills", func(d: Dictionary) -> ContentDefinition: return SkillDefinition.new(d))
var skill_nodes := DefinitionRepository.new("skill_nodes", func(d: Dictionary) -> ContentDefinition: return GenericDefinition.new(d))
var upgrades := DefinitionRepository.new("upgrades", func(d: Dictionary) -> ContentDefinition: return UpgradeDefinition.new(d))
var xp_rows := DefinitionRepository.new("xp_curve", func(d: Dictionary) -> ContentDefinition: return GenericDefinition.new(d))
var buildings := DefinitionRepository.new("buildings", func(d: Dictionary) -> ContentDefinition: return GenericDefinition.new(d))

var xp_curve := XpCurve.new()
## Default config bundled with the build. Runtime overrides live in Services.config.
var config: Dictionary = {}
var content_version: int = 0
## Problems found during the last load (schema + reference integrity).
var errors: Array[String] = []


func _ready() -> void:
	load_from(LocalJsonContentSource.new())
	if not errors.is_empty():
		for problem in errors:
			push_error("[Content] %s" % problem)


func load_from(source: ContentSource, include_unpublished: bool = false) -> Array[String]:
	errors.clear()
	var manifest := source.load_manifest()
	content_version = int(manifest.get("content_version", 0))
	config = source.load_config()
	for repository in _repositories():
		errors.append_array(repository.load_entries(source.load_collection(repository.collection), include_unpublished))
	xp_curve = XpCurve.new(xp_rows.get_all())
	errors.append_array(source.get_errors())
	errors.append_array(validate_references())
	return errors


## Cross-collection checks: every referenced ID must exist.
func validate_references() -> Array[String]:
	var problems: Array[String] = []
	for definition in characters.get_all():
		var character := definition as CharacterDefinition
		for skill_id in character.skills:
			if not skills.has_id(skill_id):
				problems.append("characters: %s references missing skill '%s'" % [character.id, skill_id])
	for definition in enemies.get_all():
		var enemy := definition as EnemyDefinition
		if not enemy.loot_table.is_empty() and not loot_tables.has_id(enemy.loot_table):
			problems.append("enemies: %s references missing loot table '%s'" % [enemy.id, enemy.loot_table])
		var summon := str(enemy.boss.get("summon_enemy_id", ""))
		if not summon.is_empty() and not enemies.has_id(summon):
			problems.append("enemies: %s summons missing enemy '%s'" % [enemy.id, summon])
	for definition in loot_tables.get_all():
		var table := definition as LootTableDefinition
		for entry in table.entries:
			var item_id := str(entry.get("item_id", ""))
			if not item_id.is_empty() and not items.has_id(item_id):
				problems.append("loot_tables: %s references missing item '%s'" % [table.id, item_id])
	for definition in levels.get_all():
		var level := definition as LevelDefinition
		for group in level.enemy_groups:
			var enemy_id := str(group.get("enemy_id", ""))
			if not enemies.has_id(enemy_id):
				problems.append("levels: %s references missing enemy '%s'" % [level.id, enemy_id])
		if not level.boss.is_empty() and not enemies.has_id(level.boss):
			problems.append("levels: %s references missing boss '%s'" % [level.id, level.boss])
		for reward in level.rewards:
			if not items.has_id(str(reward.get("item_id", ""))):
				problems.append("levels: %s rewards missing item '%s'" % [level.id, reward.get("item_id", "")])
	for definition in upgrades.get_all():
		var upgrade := definition as UpgradeDefinition
		if not upgrade.skill_id.is_empty() and not skills.has_id(upgrade.skill_id):
			problems.append("upgrades: %s references missing skill '%s'" % [upgrade.id, upgrade.skill_id])
		for prerequisite in upgrade.prerequisites:
			if not upgrades.has_id(prerequisite):
				problems.append("upgrades: %s requires missing upgrade '%s'" % [upgrade.id, prerequisite])
	return problems


func get_character(id: String) -> CharacterDefinition:
	return characters.get_by_id(id) as CharacterDefinition


func get_enemy(id: String) -> EnemyDefinition:
	return enemies.get_by_id(id) as EnemyDefinition


func get_item(id: String) -> ItemDefinition:
	return items.get_by_id(id) as ItemDefinition


func get_loot_table(id: String) -> LootTableDefinition:
	return loot_tables.get_by_id(id) as LootTableDefinition


func get_level(id: String) -> LevelDefinition:
	return levels.get_by_id(id) as LevelDefinition


func get_skill(id: String) -> SkillDefinition:
	return skills.get_by_id(id) as SkillDefinition


func get_upgrade(id: String) -> UpgradeDefinition:
	return upgrades.get_by_id(id) as UpgradeDefinition


func get_upgrades_by_scope(scope: String) -> Array[UpgradeDefinition]:
	var result: Array[UpgradeDefinition] = []
	for definition in upgrades.get_all():
		var upgrade := definition as UpgradeDefinition
		if upgrade.scope == scope:
			result.append(upgrade)
	return result


func _repositories() -> Array[DefinitionRepository]:
	return [characters, enemies, items, loot_tables, levels, skills, skill_nodes, upgrades, xp_rows, buildings]
