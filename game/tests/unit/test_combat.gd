extends TestCase


func test_damage_formula_subtracts_defense() -> void:
	assert_eq(DamageCalculator.calculate(20, 5), 15)


func test_damage_is_at_least_one() -> void:
	assert_eq(DamageCalculator.calculate(3, 50), 1)
	assert_eq(DamageCalculator.calculate(0, 0), 1)


func test_crit_multiplies_attack_before_defense() -> void:
	var rng := RandomNumberGenerator.new()
	var hit := DamageCalculator.resolve_hit(20.0, 10.0, 1.0, 2.0, rng)
	assert_true(bool(hit["is_crit"]))
	assert_eq(int(hit["amount"]), 30)


func test_no_crit_with_zero_chance() -> void:
	var rng := RandomNumberGenerator.new()
	for _i in 50:
		assert_false(bool(DamageCalculator.resolve_hit(10.0, 0.0, 0.0, 2.0, rng)["is_crit"]))


func test_health_component_dies_once() -> void:
	var health := HealthComponent.new()
	health.setup(10)
	var deaths := [0]
	health.died.connect(func(_source: String) -> void: deaths[0] += 1)
	assert_eq(health.apply_damage(7), 7)
	assert_eq(health.apply_damage(7), 3)
	assert_eq(health.apply_damage(7), 0)
	assert_true(health.is_dead)
	assert_eq(deaths[0], 1)
	health.free()


func test_invulnerability_blocks_damage() -> void:
	var health := HealthComponent.new()
	health.setup(10)
	health.invulnerable_time = 1.0
	assert_eq(health.apply_damage(5), 0)
	assert_eq(health.current, 10)
	health.free()


func test_max_health_increase_keeps_missing_amount() -> void:
	var health := HealthComponent.new()
	health.setup(100)
	health.apply_damage(30)
	health.set_max_health(125)
	assert_eq(health.current, 95)
	health.free()


func test_stats_modifiers_add_then_multiply() -> void:
	var stats := StatsComponent.new()
	stats.setup({Stats.DAMAGE: 20.0})
	stats.add_modifier("a", Stats.DAMAGE, Stats.MODE_ADD, 5.0)
	stats.add_modifier("b", Stats.DAMAGE, Stats.MODE_MULTIPLY, 0.2)
	assert_almost(stats.get_stat(Stats.DAMAGE), 30.0)
	stats.remove_modifiers("b")
	assert_almost(stats.get_stat(Stats.DAMAGE), 25.0)
	stats.free()
