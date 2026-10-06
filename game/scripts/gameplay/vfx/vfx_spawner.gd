class_name VfxSpawner
extends Node2D
## Short-lived visual effects: weapon slashes, skill rings, floating damage numbers.

const SLASH_TEXTURE := "res://assets/sprites/vfx/slash.png"
const MAX_DAMAGE_NUMBERS := 40

var _slash: Texture2D
var _textures: Dictionary = {}
var _damage_numbers := 0


func _ready() -> void:
	_slash = load(SLASH_TEXTURE) if ResourceLoader.exists(SLASH_TEXTURE) else null
	EventBus.damage_dealt.connect(_on_damage_dealt)


func slash(origin: Vector2, direction: Vector2, attack_range: float) -> void:
	if _slash == null:
		return
	var sprite := Sprite2D.new()
	sprite.texture = _slash
	sprite.global_position = origin
	sprite.rotation = direction.angle()
	var scale_factor := attack_range / (_slash.get_width() * 0.5)
	sprite.scale = Vector2.ONE * scale_factor
	add_child(sprite)
	var tween := sprite.create_tween()
	tween.tween_property(sprite, "modulate:a", 0.0, 0.15)
	tween.tween_callback(sprite.queue_free)


func ring(origin: Vector2, radius: float, texture_path: String) -> void:
	if not _textures.has(texture_path):
		_textures[texture_path] = load(texture_path) if ResourceLoader.exists(texture_path) else null
	var texture: Texture2D = _textures[texture_path]
	if texture == null:
		return
	var sprite := Sprite2D.new()
	sprite.texture = texture
	sprite.global_position = origin
	var target_scale := Vector2.ONE * radius / (texture.get_width() * 0.5)
	sprite.scale = target_scale * 0.3
	add_child(sprite)
	var tween := sprite.create_tween()
	tween.tween_property(sprite, "scale", target_scale, 0.18)
	tween.tween_property(sprite, "modulate:a", 0.0, 0.15)
	tween.tween_callback(sprite.queue_free)


func _on_damage_dealt(_target: Node2D, amount: int, is_crit: bool, position: Vector2) -> void:
	if _damage_numbers >= MAX_DAMAGE_NUMBERS:
		return
	_damage_numbers += 1
	var label := Label.new()
	label.text = str(amount)
	label.add_theme_font_size_override("font_size", 8 if not is_crit else 10)
	label.add_theme_color_override("font_color", Color(1, 0.85, 0.3) if is_crit else Color.WHITE)
	label.add_theme_color_override("font_outline_color", Color(0.1, 0.08, 0.14))
	label.add_theme_constant_override("outline_size", 2)
	label.global_position = position + Vector2(randf_range(-6, 2), -14)
	label.z_index = 10
	add_child(label)
	var tween := label.create_tween()
	tween.tween_property(label, "position:y", label.position.y - 10.0, 0.45)
	tween.parallel().tween_property(label, "modulate:a", 0.0, 0.45).set_delay(0.2)
	tween.tween_callback(func() -> void:
		_damage_numbers -= 1
		label.queue_free())
