class_name Stats
extends RefCounted
## Stat keys shared by data files, StatsComponent and upgrades.

const MAX_HEALTH := "max_health"
const DAMAGE := "damage"
const SPEED := "speed"
const DEFENSE := "defense"
const ATTACK_RANGE := "attack_range"
const ATTACK_SPEED := "attack_speed"
const CRIT_CHANCE := "crit_chance"
const CRIT_MULTIPLIER := "crit_multiplier"
const PICKUP_RADIUS := "pickup_radius"

const ALL: Array[String] = [
	MAX_HEALTH, DAMAGE, SPEED, DEFENSE, ATTACK_RANGE, ATTACK_SPEED, CRIT_CHANCE, CRIT_MULTIPLIER, PICKUP_RADIUS,
]

const MODE_ADD := "add"
const MODE_MULTIPLY := "multiply"
