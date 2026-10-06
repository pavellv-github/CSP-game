class_name SpriteAnimator
extends AnimatedSprite2D
## Plays animations described by a SpriteSheet (content data). SpriteFrames are built once per
## texture and shared by every entity that uses it.
##
## Looping animations (idle, walk) are requested every frame and never interrupt a one-shot
## (attack, hurt, cast). "death" locks the animator on its last frame.

signal one_shot_finished(anim_name: StringName)

static var _cache: Dictionary = {}

var sheet: SpriteSheet
var _one_shot: StringName = &""
var _locked := false


func _ready() -> void:
	animation_finished.connect(_on_animation_finished)


func setup(sprite_sheet: SpriteSheet) -> void:
	sheet = sprite_sheet
	_one_shot = &""
	_locked = false
	if not ResourceLoader.exists(sheet.texture_path):
		return
	var texture: Texture2D = load(sheet.texture_path)
	var size := sheet.resolve_frame_size(texture)
	sprite_frames = _frames_for(sheet, texture, size)
	# Feet at the node origin (y-sorting uses it), 2 px margin as in the art brief.
	offset = Vector2(0, -size.y * 0.5 + 2.0)
	play_loop(&"idle")


func has_animation(anim_name: StringName) -> bool:
	return sprite_frames != null and sprite_frames.has_animation(anim_name)


## Idle / walk. Ignored while a one-shot plays or after death.
func play_loop(anim_name: StringName) -> void:
	if _locked or _one_shot != &"" or not has_animation(anim_name):
		return
	if animation != anim_name or not is_playing():
		play(anim_name)


func play_once(anim_name: StringName) -> void:
	if _locked or not has_animation(anim_name):
		return
	_one_shot = anim_name
	play(anim_name)
	frame = 0


## Plays death (if present) and stays on its last frame.
func play_death() -> void:
	if _locked:
		return
	_one_shot = &""
	if has_animation(&"death"):
		play(&"death")
	else:
		stop()
	_locked = true


## Seconds a one-shot animation lasts (0 if absent).
func duration(anim_name: StringName) -> float:
	if not has_animation(anim_name):
		return 0.0
	return sprite_frames.get_frame_count(anim_name) / maxf(0.1, sprite_frames.get_animation_speed(anim_name))


func _on_animation_finished() -> void:
	if _one_shot == &"" or _locked:
		return
	var finished := _one_shot
	_one_shot = &""
	one_shot_finished.emit(finished)
	play_loop(&"idle")


static func _frames_for(sprite_sheet: SpriteSheet, texture: Texture2D, size: Vector2i) -> SpriteFrames:
	var key := "%s|%s" % [sprite_sheet.texture_path, JSON.stringify(sprite_sheet.animations)]
	if _cache.has(key):
		return _cache[key]
	var frames := SpriteFrames.new()
	frames.remove_animation(&"default")
	for anim_name: String in sprite_sheet.animations:
		var anim: Dictionary = sprite_sheet.animations[anim_name]
		frames.add_animation(anim_name)
		frames.set_animation_speed(anim_name, float(anim["fps"]))
		frames.set_animation_loop(anim_name, anim_name in SpriteSheet.LOOPING)
		for column in int(anim["frames"]):
			var atlas := AtlasTexture.new()
			atlas.atlas = texture
			atlas.region = Rect2(column * size.x, int(anim["row"]) * size.y, size.x, size.y)
			frames.add_frame(anim_name, atlas)
	_cache[key] = frames
	return frames
