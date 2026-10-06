extends Node
## Entry scene ("Main"): applies the global theme and hands control to the state machine.


func _ready() -> void:
	get_tree().root.theme = UiKit.shared_theme()
	if not Content.errors.is_empty():
		Services.crash.record_non_fatal("content validation: %d problems" % Content.errors.size())
	GameManager.boot.call_deferred()
