class_name ExperienceComponent
extends Node
## Enemy killed -> XP reward -> player XP -> level up. Requirements come from the data-driven XpCurve.

signal leveled_up(new_level: int)

var level: int = 1
var total_xp: int = 0
var curve: XpCurve = XpCurve.new()
## Global balance multiplier (Remote Config: balance.xp_multiplier).
var multiplier: float = 1.0


func setup(xp_curve: XpCurve, xp_multiplier: float) -> void:
	curve = xp_curve
	multiplier = xp_multiplier
	level = 1
	total_xp = 0
	_emit_progress()


func _ready() -> void:
	EventBus.enemy_killed.connect(_on_enemy_killed)


func add_xp(amount: int) -> void:
	if amount <= 0:
		return
	total_xp += maxi(1, roundi(amount * multiplier))
	while total_xp >= curve.required_xp(level + 1):
		level += 1
		leveled_up.emit(level)
		EventBus.player_leveled_up.emit(level)
	_emit_progress()


func xp_into_level() -> int:
	return total_xp - curve.required_xp(level)


func xp_for_next_level() -> int:
	return curve.required_xp(level + 1) - curve.required_xp(level)


func _on_enemy_killed(_enemy_id: String, _position: Vector2, experience_reward: int, _loot: String, _is_boss: bool) -> void:
	add_xp(experience_reward)


func _emit_progress() -> void:
	EventBus.player_xp_changed.emit(level, xp_into_level(), xp_for_next_level())
