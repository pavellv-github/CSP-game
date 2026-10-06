extends SceneTree
## Cuts menu art (banner, hero portraits, class icons) out of the key art and extracts its palette.
## Regions live in tools/art/keyart_regions.json, so re-cutting is a data change.
##
## Usage (from the repository root):
##   godot --headless --script tools/art/import_keyart.gd
##
## Portraits and the banner are downscaled with Lanczos: they are menu illustrations, not
## gameplay sprites, and the source is not on a clean pixel grid.

const CONFIG_PATH := "tools/art/keyart_regions.json"


func _init() -> void:
	var root := _repo_root()
	var config: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(root.path_join(CONFIG_PATH)))
	var source := Image.load_from_file(root.path_join(str(config["source"])))
	source.convert(Image.FORMAT_RGBA8)
	var out_root := root.path_join(str(config["output_root"]))

	var banner: Dictionary = config["banner"]
	var banner_image := _cut(source, banner["rect"])
	var banner_width := int(banner["width"])
	banner_image.resize(banner_width, roundi(banner_image.get_height() * float(banner_width) / banner_image.get_width()), Image.INTERPOLATE_LANCZOS)
	_save(banner_image, out_root.path_join(str(banner["output"])))

	var portrait_height := int(config["portrait_height"])
	var icon_size := int(config["icon_size"])
	for hero: Dictionary in config["heroes"]:
		var portrait := _cut(source, hero["portrait"])
		portrait.resize(roundi(portrait.get_width() * float(portrait_height) / portrait.get_height()), portrait_height, Image.INTERPOLATE_LANCZOS)
		_save(portrait, out_root.path_join("portraits/%s.png" % hero["id"]))
		var icon := _cut(source, hero["icon"])
		icon.resize(icon_size, icon_size, Image.INTERPOLATE_LANCZOS)
		_save(_circle_mask(icon), out_root.path_join("class_icons/%s.png" % hero["id"]))

	var palette := _extract_palette(source, int(config["palette_size"]))
	var file := FileAccess.open(root.path_join(str(config["palette_output"])), FileAccess.WRITE)
	file.store_string(JSON.stringify({"source": config["source"], "colors": palette}, "\t") + "\n")
	print("palette: ", " ".join(palette))
	quit(0)


func _cut(source: Image, rect: Array) -> Image:
	return source.get_region(Rect2i(int(rect[0]), int(rect[1]), int(rect[2]), int(rect[3])))


## Keeps only the round emblem: everything outside the inscribed circle becomes transparent.
func _circle_mask(image: Image) -> Image:
	var center := Vector2(image.get_width(), image.get_height()) * 0.5
	var radius := minf(center.x, center.y)
	for y in image.get_height():
		for x in image.get_width():
			if Vector2(x + 0.5, y + 0.5).distance_to(center) > radius:
				image.set_pixel(x, y, Color(0, 0, 0, 0))
	return image


## Most frequent colours after quantizing to 4 bits per channel, skipping near-duplicates.
func _extract_palette(source: Image, count: int) -> Array[String]:
	var histogram: Dictionary = {}
	for y in range(0, source.get_height(), 2):
		for x in range(0, source.get_width(), 2):
			var c := source.get_pixel(x, y)
			var key := (int(c.r * 15.0) << 8) | (int(c.g * 15.0) << 4) | int(c.b * 15.0)
			histogram[key] = int(histogram.get(key, 0)) + 1
	var keys := histogram.keys()
	keys.sort_custom(func(a: int, b: int) -> bool: return histogram[a] > histogram[b])
	var picked: Array[Color] = []
	for key: int in keys:
		var color := Color(((key >> 8) & 15) / 15.0, ((key >> 4) & 15) / 15.0, (key & 15) / 15.0)
		var distinct := true
		for other in picked:
			if Vector3(color.r, color.g, color.b).distance_to(Vector3(other.r, other.g, other.b)) < 0.12:
				distinct = false
				break
		if distinct:
			picked.append(color)
		if picked.size() >= count:
			break
	var result: Array[String] = []
	for color in picked:
		result.append("#" + color.to_html(false))
	return result


func _save(image: Image, path: String) -> void:
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	image.save_png(path)
	print("wrote ", path, " (", image.get_width(), "x", image.get_height(), ")")


func _repo_root() -> String:
	return ProjectSettings.globalize_path("res://") if FileAccess.file_exists("res://tools/art/keyart_regions.json") \
		else OS.get_environment("PWD")
