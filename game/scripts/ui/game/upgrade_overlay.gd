class_name UpgradeOverlay
extends Overlay
## Shows the level-up choices; the pick is forwarded to the game.

signal upgrade_chosen(upgrade_id: String)

const State := preload("res://scripts/core/game_state_manager.gd").State

var choices: Array[UpgradeDefinition] = []
var owned: Dictionary = {}
var player_level: int = 1


func _init() -> void:
	super(State.UPGRADE)


func set_choices(upgrades: Array[UpgradeDefinition], owned_levels: Dictionary, level: int) -> void:
	choices = upgrades
	owned = owned_levels
	player_level = level
	if visible:
		refresh()


func refresh() -> void:
	clear_body()
	body.add_child(UiKit.title(Loc.t("LEVEL_UP_TITLE") % player_level))
	body.add_child(UiKit.label(Loc.t("LEVEL_UP_CHOOSE"), 10, UiKit.TEXT_DIM, HORIZONTAL_ALIGNMENT_CENTER))
	for upgrade in choices:
		var level := int(owned.get(upgrade.id, 0))
		var text := Loc.t("LEVEL_UP_CHOICE") % [Loc.name_of(upgrade), level + 1, upgrade.max_level, Loc.desc_of(upgrade)]
		var button := UiKit.button(text, func() -> void: upgrade_chosen.emit(upgrade.id), 44)
		button.alignment = HORIZONTAL_ALIGNMENT_LEFT
		button.add_theme_font_size_override("font_size", 10)
		body.add_child(button)
