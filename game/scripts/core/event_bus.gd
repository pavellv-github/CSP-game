extends Node
## Global event bus. Systems publish facts here instead of referencing each other:
## an Enemy does not know about Analytics, UI or Loot — they subscribe to its events.

# Game flow
signal game_state_changed(previous: int, current: int)
signal run_started(level_id: String, character_id: String)
signal run_finished(level_id: String, victory: bool, summary: Dictionary)
signal level_time_changed(elapsed: float, duration: float)

# Combat
signal enemy_spawned(enemy: Node2D)
signal enemy_killed(enemy_id: String, position: Vector2, experience_reward: int, loot_table_id: String, is_boss: bool)
signal boss_spawned(enemy: Node2D)
signal boss_health_changed(current: int, maximum: int)
signal damage_dealt(target: Node2D, amount: int, is_crit: bool, position: Vector2)
signal player_health_changed(current: int, maximum: int)
signal player_died(death_reason: String)
## Visual-only: an area effect (explosion, heal wave) happened; VFX listens to it.
signal area_effect_shown(vfx_path: String, position: Vector2, radius: float)

# Progression
signal player_xp_changed(level: int, xp_into_level: int, xp_for_next: int)
signal player_leveled_up(new_level: int)
signal upgrade_selected(upgrade_id: String, level: int)
signal meta_upgrade_purchased(upgrade_id: String, level: int)
signal character_selected(character_id: String)
signal character_unlocked(character_id: String)

# Items
signal item_obtained(item_id: String, quantity: int)
signal item_used(item_id: String)
signal item_equipped(item_id: String, equipped: bool)
signal gold_changed(total: int)

# Skills / input
signal skill_used(skill_id: String)
signal skill_cooldown_changed(skill_id: String, remaining: float, total: float)
signal interact_requested(position: Vector2)

# World (reserved for the building system, not used by the MVP)
signal building_created(building_id: String)
signal building_upgraded(building_id: String, level: int)

# Settings
signal settings_changed(settings: Dictionary)
