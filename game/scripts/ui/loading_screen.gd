extends Screen


func _build() -> void:
	content.alignment = BoxContainer.ALIGNMENT_CENTER
	var level := GameManager.get_current_level()
	content.add_child(UiKit.title(Loc.name_of(level) if level != null else Loc.t("LOADING_TITLE")))
	content.add_child(UiKit.label(Loc.t("LOADING_TEXT"), 10, UiKit.TEXT_DIM, HORIZONTAL_ALIGNMENT_CENTER))
