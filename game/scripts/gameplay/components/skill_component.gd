class_name SkillComponent
extends Node
## Active skills of the player. Skill behaviour comes from SkillDefinition data;
## run upgrades add per-skill modifiers (radius, cooldown, damage_multiplier).

signal skill_activated(skill: SkillDefinition, origin: Vector2, radius: float)

const TARGET_GROUP := &"enemies"


class SkillSlot:
	var definition: SkillDefinition
	var cooldown_left: float = 0.0
	## param -> summed multiplier bonus, e.g. {"radius": 0.2, "cooldown": -0.1}
	var bonuses: Dictionary = {}

	func get_param(param: String, base: float) -> float:
		return base * maxf(0.1, 1.0 + float(bonuses.get(param, 0.0)))


var body: CombatEntity
var stats: StatsComponent
var damage_multiplier: float = 1.0
var slots: Array[SkillSlot] = []


func setup(owner_body: CombatEntity, owner_stats: StatsComponent, skill_ids: Array[String]) -> void:
	body = owner_body
	stats = owner_stats
	slots.clear()
	for skill_id in skill_ids:
		var definition := Content.get_skill(skill_id)
		if definition != null:
			var slot := SkillSlot.new()
			slot.definition = definition
			slots.append(slot)


func has_skill(skill_id: String) -> bool:
	return _find(skill_id) != null


func add_skill(skill_id: String) -> void:
	if has_skill(skill_id):
		return
	var definition := Content.get_skill(skill_id)
	if definition != null:
		var slot := SkillSlot.new()
		slot.definition = definition
		slots.append(slot)


func add_bonus(skill_id: String, param: String, value: float) -> void:
	var slot := _find(skill_id)
	if slot != null:
		slot.bonuses[param] = float(slot.bonuses.get(param, 0.0)) + value


func use(index: int = 0) -> bool:
	if index < 0 or index >= slots.size():
		return false
	var slot := slots[index]
	if slot.cooldown_left > 0.0:
		return false
	var definition := slot.definition
	var radius := slot.get_param("radius", definition.radius)
	match definition.effect:
		SkillDefinition.EFFECT_AOE_DAMAGE:
			var attack := stats.get_stat(Stats.DAMAGE) * slot.get_param("damage_multiplier", definition.damage_multiplier) * damage_multiplier
			CombatSystem.deal_area_damage(body.get_tree(), TARGET_GROUP, body.global_position, radius, attack,
				stats.get_stat(Stats.CRIT_CHANCE), stats.get_stat(Stats.CRIT_MULTIPLIER), Vector2.ZERO, 360.0, definition.id)
		_:
			push_warning("[Skills] unknown effect '%s'" % definition.effect)
			return false
	slot.cooldown_left = slot.get_param("cooldown", definition.cooldown)
	skill_activated.emit(definition, body.global_position, radius)
	EventBus.skill_used.emit(definition.id)
	return true


func physics_step(delta: float) -> void:
	for slot in slots:
		if slot.cooldown_left <= 0.0:
			continue
		slot.cooldown_left = maxf(0.0, slot.cooldown_left - delta)
		EventBus.skill_cooldown_changed.emit(slot.definition.id, slot.cooldown_left, slot.get_param("cooldown", slot.definition.cooldown))


func _find(skill_id: String) -> SkillSlot:
	for slot in slots:
		if slot.definition.id == skill_id:
			return slot
	return null
