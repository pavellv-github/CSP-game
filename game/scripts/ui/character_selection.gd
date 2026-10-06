extends Screen
## Character selection + character progression (meta upgrades bought with gold).

const State := preload("res://scripts/core/game_state_manager.gd").State


func _build() -> void:
	content.add_child(UiKit.title("Hero"))
	content.add_child(UiKit.label("Gold: %d" % Profile.get_gold(), 10, UiKit.ACCENT, HORIZONTAL_ALIGNMENT_CENTER))
	var selected_id := Profile.get_selected_character_id()
	for definition in Content.characters.get_all():
		content.add_child(_character_card(definition as CharacterDefinition, definition.id == selected_id))

	content.add_child(UiKit.label("Training", 12, UiKit.ACCENT))
	var levels := Profile.get_meta_upgrade_levels()
	for upgrade in Content.get_upgrades_by_scope(UpgradeDefinition.SCOPE_META):
		content.add_child(_upgrade_row(upgrade, levels))

	var buttons := UiKit.hbox()
	var back := UiKit.button("Back", func() -> void: GameStateManager.change_state(State.MENU))
	back.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var next := UiKit.button("Choose level", func() -> void: GameStateManager.change_state(State.LEVEL_SELECTION))
	next.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	buttons.add_child(back)
	buttons.add_child(next)
	content.add_child(buttons)


func _character_card(character: CharacterDefinition, selected: bool) -> Control:
	var row := UiKit.hbox(8)
	row.add_child(UiKit.sprite_icon(character.sprite, character.frames, 40))
	var info := UiKit.vbox(2)
	info.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	info.add_child(UiKit.label(character.name + ("  (selected)" if selected else ""), 12, UiKit.ACCENT if selected else UiKit.TEXT))
	info.add_child(UiKit.label(character.description, 8, UiKit.TEXT_DIM))
	var stats := StatsComponent.new()
	stats.setup(character.base_stats())
	UpgradeService.apply_meta_upgrades(stats, Profile.get_meta_upgrade_levels())
	info.add_child(UiKit.label("HP %d  DMG %d  DEF %d  SPD %d" % [
		stats.get_int(Stats.MAX_HEALTH), stats.get_int(Stats.DAMAGE), stats.get_int(Stats.DEFENSE), stats.get_int(Stats.SPEED)], 8))
	stats.free()
	row.add_child(info)
	if Profile.is_character_unlocked(character.id):
		if not selected:
			row.add_child(UiKit.button("Pick", func() -> void:
				Profile.select_character(character.id)
				Profile.flush()
				rebuild()))
	else:
		row.add_child(UiKit.label("Locked", 8, UiKit.TEXT_DIM))
	return UiKit.panel(row, 6)


func _upgrade_row(upgrade: UpgradeDefinition, levels: Dictionary) -> Control:
	var level := int(levels.get(upgrade.id, 0))
	var row := UiKit.hbox(6)
	var info := UiKit.vbox(0)
	info.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	info.add_child(UiKit.label("%s  %d/%d" % [upgrade.name, level, upgrade.max_level], 10))
	info.add_child(UiKit.label(upgrade.description, 8, UiKit.TEXT_DIM))
	row.add_child(info)
	var buy: Button
	if level >= upgrade.max_level:
		buy = UiKit.button("Max", func() -> void: pass)
		buy.disabled = true
	else:
		buy = UiKit.button("%d g" % upgrade.cost_for_level(level), func() -> void:
			if UpgradeService.buy_meta(upgrade.id):
				rebuild())
		buy.disabled = not UpgradeService.can_buy_meta(upgrade, levels, Profile.get_gold())
	buy.custom_minimum_size.x = 56
	row.add_child(buy)
	return UiKit.panel(row, 6)
