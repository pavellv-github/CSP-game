class_name SpriteSheet
extends RefCounted
## Sprite sheet description from content data: row = animation, column = frame.
##
## "sprite": "res://...png",
## "frame_size": [32, 32],
## "animations": {"idle": {"row": 0, "frames": 4, "fps": 6}, "attack": {..., "hit_frame": 2}, ...}
##
## Legacy entries with only "frames": N are read as one row of N walk frames.

const LOOPING := ["idle", "walk"]

var texture_path: String = ""
var frame_size: Vector2i = Vector2i.ZERO
## name -> {row: int, frames: int, fps: float, hit_frame: int}
var animations: Dictionary = {}


static func from_data(d: Dictionary) -> SpriteSheet:
	var sheet := SpriteSheet.new()
	sheet.texture_path = str(d.get("sprite", ""))
	var size: Variant = d.get("frame_size", [])
	if size is Array and (size as Array).size() == 2:
		sheet.frame_size = Vector2i(int(size[0]), int(size[1]))
	var animations: Variant = d.get("animations", {})
	if animations is Dictionary and not (animations as Dictionary).is_empty():
		for anim_name: String in animations:
			var anim: Dictionary = animations[anim_name]
			sheet.animations[anim_name] = {
				"row": int(anim.get("row", 0)),
				"frames": maxi(1, int(anim.get("frames", 1))),
				"fps": float(anim.get("fps", 8.0)),
				"hit_frame": int(anim.get("hit_frame", -1)),
			}
	else:
		var frames := maxi(1, int(d.get("frames", 1)))
		sheet.animations["walk"] = {"row": 0, "frames": frames, "fps": 8.0, "hit_frame": -1}
		sheet.animations["idle"] = {"row": 0, "frames": 1, "fps": 1.0, "hit_frame": -1}
	return sheet


func has_animation(anim_name: String) -> bool:
	return animations.has(anim_name)


## Frame size, derived from the texture for legacy single-row sheets.
func resolve_frame_size(texture: Texture2D) -> Vector2i:
	if frame_size != Vector2i.ZERO:
		return frame_size
	var columns := 1
	for anim: Dictionary in animations.values():
		columns = maxi(columns, int(anim["frames"]))
	return Vector2i(texture.get_width() / columns, texture.get_height())


func validate(owner_id: String) -> Array[String]:
	var errors: Array[String] = []
	if texture_path.is_empty() or not ResourceLoader.exists(texture_path):
		errors.append("%s: missing sprite '%s'" % [owner_id, texture_path])
		return errors
	var texture: Texture2D = load(texture_path)
	var size := resolve_frame_size(texture)
	for anim_name: String in animations:
		var anim: Dictionary = animations[anim_name]
		if (int(anim["row"]) + 1) * size.y > texture.get_height() or int(anim["frames"]) * size.x > texture.get_width():
			errors.append("%s: animation '%s' does not fit into %s" % [owner_id, anim_name, texture_path])
	return errors
