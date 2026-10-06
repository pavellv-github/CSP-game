class_name CombatSystem
extends RefCounted
## Applies damage between combat entities. Independent from Player and Enemy:
## both call into it with numbers, the formulas live in DamageCalculator.

static var rng := RandomNumberGenerator.new()


## Deals one hit to `target`. Returns the damage actually applied (0 if the hit was ignored).
static func deal_damage(target: CombatEntity, attack_damage: float, crit_chance: float = 0.0,
		crit_multiplier: float = 1.5, source_id: String = "") -> int:
	if target == null or not is_instance_valid(target) or not target.is_alive():
		return 0
	var hit := DamageCalculator.resolve_hit(attack_damage, target.get_defense(), crit_chance, crit_multiplier, rng)
	var amount := target.health.apply_damage(int(hit["amount"]), source_id)
	if amount > 0:
		EventBus.damage_dealt.emit(target, amount, bool(hit["is_crit"]), target.global_position)
	return amount


## Hits every living entity of `team` within `radius` of `origin`, optionally limited to a cone.
## Returns the number of entities hit.
static func deal_area_damage(tree: SceneTree, team_group: StringName, origin: Vector2, radius: float,
		attack_damage: float, crit_chance: float, crit_multiplier: float,
		direction: Vector2 = Vector2.ZERO, arc_degrees: float = 360.0, source_id: String = "") -> int:
	var hits := 0
	var half_arc := deg_to_rad(arc_degrees) * 0.5
	for node in tree.get_nodes_in_group(team_group):
		var target := node as CombatEntity
		if target == null or not target.is_alive():
			continue
		var offset := target.global_position - origin
		if offset.length() > radius + target.get_radius():
			continue
		if arc_degrees < 360.0 and direction != Vector2.ZERO and offset.length() > target.get_radius():
			if absf(direction.angle_to(offset)) > half_arc:
				continue
		if deal_damage(target, attack_damage, crit_chance, crit_multiplier, source_id) > 0:
			hits += 1
	return hits


static func find_nearest(tree: SceneTree, team_group: StringName, origin: Vector2, max_distance: float = INF) -> CombatEntity:
	var best: CombatEntity = null
	var best_distance := max_distance
	for node in tree.get_nodes_in_group(team_group):
		var target := node as CombatEntity
		if target == null or not target.is_alive():
			continue
		var distance := origin.distance_to(target.global_position) - target.get_radius()
		if distance < best_distance:
			best_distance = distance
			best = target
	return best
