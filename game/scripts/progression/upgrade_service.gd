class_name UpgradeService
extends RefCounted
## Rules for upgrades: which ones can be offered, what they do, how much meta levels cost.
## UI only displays the choices and forwards the player's pick here.

const RUN_SOURCE := "run_upgrades"
const META_SOURCE := "meta_upgrades"


## Picks up to `count` distinct run upgrades that are not maxed and have prerequisites met.
## `owned` maps upgrade_id -> level taken in this run.
## Skill upgrades are offered only for skills in `skill_ids` (the hero's skills).
static func roll_choices(owned: Dictionary, count: int, rng: RandomNumberGenerator,
		skill_ids: Array[String] = []) -> Array[UpgradeDefinition]:
	var pool: Array[UpgradeDefinition] = []
	for upgrade in Content.get_upgrades_by_scope(UpgradeDefinition.SCOPE_RUN):
		if not upgrade.skill_id.is_empty() and upgrade.type == UpgradeDefinition.TYPE_SKILL_MODIFIER and upgrade.skill_id not in skill_ids:
			continue
		if int(owned.get(upgrade.id, 0)) >= upgrade.max_level:
			continue
		if not _prerequisites_met(upgrade, owned):
			continue
		pool.append(upgrade)
	var choices: Array[UpgradeDefinition] = []
	while not pool.is_empty() and choices.size() < count:
		var index := rng.randi_range(0, pool.size() - 1)
		choices.append(pool[index])
		pool.remove_at(index)
	return choices


## Applies one level of `upgrade` to the player's components.
static func apply(upgrade: UpgradeDefinition, stats: StatsComponent, health: HealthComponent,
		skills: SkillComponent, source: String = RUN_SOURCE) -> void:
	match upgrade.type:
		UpgradeDefinition.TYPE_STAT:
			stats.add_modifier(source, upgrade.stat, upgrade.mode, upgrade.value)
		UpgradeDefinition.TYPE_SKILL_MODIFIER:
			if skills != null:
				for effect in upgrade.effects:
					skills.add_bonus(upgrade.skill_id, str(effect.get("param", "")), float(effect.get("value", 0.0)))
		UpgradeDefinition.TYPE_SKILL_UNLOCK:
			if skills != null:
				skills.add_skill(upgrade.skill_id)
		UpgradeDefinition.TYPE_HEAL:
			if health != null:
				health.heal(roundi(health.max_health * upgrade.value))
		_:
			push_warning("[Upgrades] unknown upgrade type '%s'" % upgrade.type)


## Applies all purchased meta upgrades (stat type) at the start of a run.
static func apply_meta_upgrades(stats: StatsComponent, levels: Dictionary) -> void:
	stats.remove_modifiers(META_SOURCE)
	for upgrade_id: String in levels:
		var upgrade := Content.get_upgrade(upgrade_id)
		if upgrade == null or upgrade.scope != UpgradeDefinition.SCOPE_META or upgrade.type != UpgradeDefinition.TYPE_STAT:
			continue
		var level := mini(int(levels[upgrade_id]), upgrade.max_level)
		if level > 0:
			stats.add_modifier(META_SOURCE, upgrade.stat, upgrade.mode, upgrade.value * level)


static func can_buy_meta(upgrade: UpgradeDefinition, levels: Dictionary, gold: int) -> bool:
	var level := int(levels.get(upgrade.id, 0))
	return level < upgrade.max_level and _prerequisites_met(upgrade, levels) and gold >= upgrade.cost_for_level(level)


## Spends gold and raises the meta upgrade level. Returns true on success.
static func buy_meta(upgrade_id: String) -> bool:
	var upgrade := Content.get_upgrade(upgrade_id)
	if upgrade == null or upgrade.scope != UpgradeDefinition.SCOPE_META:
		return false
	var levels := Profile.get_meta_upgrade_levels()
	if not can_buy_meta(upgrade, levels, Profile.get_gold()):
		return false
	var level := int(levels.get(upgrade_id, 0))
	if not Profile.spend_gold(upgrade.cost_for_level(level)):
		return false
	Profile.set_upgrade_level(upgrade_id, level + 1)
	Profile.flush()
	EventBus.meta_upgrade_purchased.emit(upgrade_id, level + 1)
	return true


static func _prerequisites_met(upgrade: UpgradeDefinition, owned: Dictionary) -> bool:
	for prerequisite in upgrade.prerequisites:
		if int(owned.get(prerequisite, 0)) <= 0:
			return false
	return true
