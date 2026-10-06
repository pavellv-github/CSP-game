extends Screen
## Character selection + character progression (meta upgrades bought with gold).

const State := preload("res://scripts/core/game_state_manager.gd").State


func _build() -> void:
	content.add_child(UiKit.title(Loc.t("HERO_TITLE")))
	content.add_child(UiKit.label(Loc.t("COMMON_GOLD") % Profile.get_gold(), 10, UiKit.ACCENT, HORIZONTAL_ALIGNMENT_CENTER))
	var selected_id := Profile.get_selected_character_id()
	for definition in Content.characters.get_all():
		content.add_child(_character_card(definition as CharacterDefinition, definition.id == selected_id))

	content.add_child(UiKit.label(Loc.t("HERO_TRAINING"), 12, UiKit.ACCENT))
	var levels := Profile.get_meta_upgrade_levels()
	for upgrade in Content.get_upgrades_by_scope(UpgradeDefinition.SCOPE_META):
		content.add_child(_upgrade_row(upgrade, levels))

	var buttons := UiKit.hbox()
	var back := UiKit.button(Loc.t("COMMON_BACK"), func() -> void: GameStateManager.change_state(State.MENU))
	back.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var next := UiKit.button(Loc.t("HERO_TO_LEVELS"), func() -> void: GameStateManager.change_state(State.LEVEL_SELECTION))
	next.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	buttons.add_child(back)
	buttons.add_child(next)
	content.add_child(buttons)


func _character_card(character: CharacterDefinition, selected: bool) -> Control:
	var row := UiKit.hbox(8)
	if not character.portrait.is_empty():
		row.add_child(UiKit.illustration(character.portrait))
	else:
		row.add_child(UiKit.sprite_icon(character.sheet, 40))
	var info := UiKit.vbox(4)
	info.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var header := UiKit.hbox(4)
	if not character.class_icon.is_empty():
		header.add_child(UiKit.illustration(character.class_icon))
	var name_label := UiKit.label(Loc.name_of(character), 12, UiKit.ACCENT if selected else UiKit.TEXT, HORIZONTAL_ALIGNMENT_LEFT, false)
	name_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	header.add_child(name_label)
	info.add_child(header)
	if selected:
		info.add_child(UiKit.label(Loc.t("HERO_SELECTED"), 8, UiKit.ACCENT))
	info.add_child(UiKit.label(Loc.desc_of(character), 8, UiKit.TEXT_DIM))
	var attack_kind := Loc.t("HERO_ATTACK_MELEE") if character.attack_type == "melee_arc" else Loc.t("HERO_ATTACK_RANGED")
	var skill := Content.get_skill(character.skills[0]) if not character.skills.is_empty() else null
	var kit := attack_kind if skill == null else "%s · %s" % [attack_kind, Loc.t("HERO_SKILL") % Loc.name_of(skill)]
	info.add_child(UiKit.label(kit, 8, UiKit.ACCENT))
	var stats := StatsComponent.new()
	stats.setup(character.base_stats())
	UpgradeService.apply_meta_upgrades(stats, Profile.get_meta_upgrade_levels())
	info.add_child(UiKit.label(Loc.t("HERO_STATS") % [
		stats.get_int(Stats.MAX_HEALTH), stats.get_int(Stats.DAMAGE), stats.get_int(Stats.DEFENSE), stats.get_int(Stats.SPEED)], 8))
	stats.free()
	row.add_child(info)
	if Profile.is_character_unlocked(character.id):
		if not selected:
			var pick := UiKit.button(Loc.t("HERO_PICK"), func() -> void:
				Profile.select_character(character.id)
				Profile.flush()
				rebuild())
			info.add_child(pick)
	else:
		info.add_child(UiKit.label(Loc.t("COMMON_LOCKED"), 8, UiKit.TEXT_DIM))
	return UiKit.panel(row, 6)


func _upgrade_row(upgrade: UpgradeDefinition, levels: Dictionary) -> Control:
	var level := int(levels.get(upgrade.id, 0))
	var row := UiKit.hbox(6)
	var info := UiKit.vbox(0)
	info.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	info.add_child(UiKit.label(Loc.t("UPGRADE_PROGRESS") % [Loc.name_of(upgrade), level, upgrade.max_level], 10))
	info.add_child(UiKit.label(Loc.desc_of(upgrade), 8, UiKit.TEXT_DIM))
	row.add_child(info)
	var buy: Button
	if level >= upgrade.max_level:
		buy = UiKit.button(Loc.t("UPGRADE_MAX"), func() -> void: pass)
		buy.disabled = true
	else:
		buy = UiKit.button(Loc.t("UPGRADE_PRICE") % upgrade.cost_for_level(level), func() -> void:
			if UpgradeService.buy_meta(upgrade.id):
				rebuild())
		buy.disabled = not UpgradeService.can_buy_meta(upgrade, levels, Profile.get_gold())
	buy.custom_minimum_size.x = 56
	row.add_child(buy)
	return UiKit.panel(row, 6)
