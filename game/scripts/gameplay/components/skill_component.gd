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
## Direction used when there is no target (set by the player every frame).
var facing: Vector2 = Vector2.RIGHT
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
	var attack := stats.get_stat(Stats.DAMAGE) * slot.get_param("damage_multiplier", definition.damage_multiplier) * damage_multiplier
	var origin := body.global_position
	match definition.effect:
		SkillDefinition.EFFECT_AOE_DAMAGE:
			_area_damage(origin, radius, attack, definition.id)
		SkillDefinition.EFFECT_TARGET_AOE:
			var target := CombatSystem.find_nearest(body.get_tree(), TARGET_GROUP, origin, slot.get_param("cast_range", definition.cast_range))
			if target == null:
				return false # nothing to hit: keep the skill ready
			origin = target.global_position
			_area_damage(origin, radius, attack, definition.id)
		SkillDefinition.EFFECT_VOLLEY:
			var volley_target := CombatSystem.find_nearest(body.get_tree(), TARGET_GROUP, origin, stats.get_stat(Stats.ATTACK_RANGE) * 1.5)
			var aim := origin.direction_to(volley_target.global_position) if volley_target != null else facing
			var count := maxi(1, roundi(slot.get_param("count", definition.count)))
			var spread := deg_to_rad(definition.spread_degrees)
			for i in count:
				var angle := 0.0 if count == 1 else lerpf(-spread * 0.5, spread * 0.5, float(i) / (count - 1))
				Projectile.fire_from(body, aim.rotated(angle), attack, definition.projectile, definition.id,
					stats.get_stat(Stats.CRIT_CHANCE), stats.get_stat(Stats.CRIT_MULTIPLIER), stats.get_stat(Stats.ATTACK_RANGE) * 1.3)
			radius = 0.0
		SkillDefinition.EFFECT_HEAL_WAVE:
			body.health.heal(roundi(body.health.max_health * slot.get_param("heal_ratio", definition.heal_ratio)))
			_area_damage(origin, radius, attack, definition.id)
		SkillDefinition.EFFECT_SUMMON:
			var companion := Companion.create(body, definition.companion, stats.get_stat(Stats.DAMAGE) * damage_multiplier,
				slot.get_param("duration", definition.duration))
			body.spawn_requested.emit(companion)
			radius = 0.0
		_:
			push_warning("[Skills] unknown effect '%s'" % definition.effect)
			return false
	slot.cooldown_left = slot.get_param("cooldown", definition.cooldown)
	skill_activated.emit(definition, origin, radius)
	EventBus.skill_used.emit(definition.id)
	return true


func skill_ids() -> Array[String]:
	var result: Array[String] = []
	for slot in slots:
		result.append(slot.definition.id)
	return result


func _area_damage(origin: Vector2, radius: float, attack: float, source_id: String) -> void:
	CombatSystem.deal_area_damage(body.get_tree(), TARGET_GROUP, origin, radius, attack,
		stats.get_stat(Stats.CRIT_CHANCE), stats.get_stat(Stats.CRIT_MULTIPLIER), Vector2.ZERO, 360.0, source_id)


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
