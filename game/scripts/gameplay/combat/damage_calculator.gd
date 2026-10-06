class_name DamageCalculator
extends RefCounted
## All damage formulas live here, so balance changes never touch Player/Enemy code.


## Base formula from the design: final_damage = max(1, attack_damage - target_defense)
static func calculate(attack_damage: int, target_defense: int) -> int:
	return maxi(1, attack_damage - target_defense)


static func roll_crit(crit_chance: float, rng: RandomNumberGenerator) -> bool:
	return crit_chance > 0.0 and rng.randf() < crit_chance


## Full hit resolution. Returns {"amount": int, "is_crit": bool}.
## Crit multiplies the attack before defense is subtracted.
static func resolve_hit(attack_damage: float, target_defense: float, crit_chance: float,
		crit_multiplier: float, rng: RandomNumberGenerator) -> Dictionary:
	var is_crit := roll_crit(crit_chance, rng)
	var attack := attack_damage * (crit_multiplier if is_crit else 1.0)
	return {
		"amount": calculate(roundi(attack), roundi(target_defense)),
		"is_crit": is_crit,
	}
