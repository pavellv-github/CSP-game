class_name PauseOverlay
extends Overlay

const State := preload("res://scripts/core/game_state_manager.gd").State


func _init() -> void:
	super(State.PAUSED)


func refresh() -> void:
	clear_body()
	body.add_child(UiKit.title("Paused"))
	body.add_child(UiKit.button("Resume", _resume, 34))
	body.add_child(UiKit.button("Leave to levels", func() -> void:
		Profile.flush()
		GameStateManager.change_state(State.LEVEL_SELECTION)))
	body.add_child(UiKit.button("Main menu", func() -> void:
		Profile.flush()
		GameStateManager.change_state(State.MENU)))


func _unhandled_input(event: InputEvent) -> void:
	if visible and event.is_action_pressed(InputSetup.PAUSE):
		get_viewport().set_input_as_handled()
		_resume()


func _resume() -> void:
	GameStateManager.change_state(State.GAMEPLAY)
