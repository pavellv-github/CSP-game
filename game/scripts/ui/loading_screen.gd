extends Screen


func _build() -> void:
	content.alignment = BoxContainer.ALIGNMENT_CENTER
	var level := GameManager.get_current_level()
	content.add_child(UiKit.title(level.name if level != null else "Loading"))
	content.add_child(UiKit.label("Loading...", 10, UiKit.TEXT_DIM, HORIZONTAL_ALIGNMENT_CENTER))
