class_name LevelDecorator
extends RefCounted
## Scatters decor from LevelDefinition.decor over the arena, deterministically per level.
## Entry: {sprite, count, layer: "ground" | "object", min_spacing}
## - ground: flat decals (dirt, grass patches) drawn under everything;
## - object: standing props (trees, rocks) y-sorted with characters, with a ground shadow.
## Decor is visual only (no collisions).

const LAYER_GROUND := "ground"
const LAYER_OBJECT := "object"
const SPAWN_CLEAR_RADIUS := 70.0
const BORDER := 12.0


static func decorate(level: LevelDefinition, ground_layer: Node2D, object_layer: Node2D) -> int:
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(level.id)
	var placed: Array[Vector2] = []
	var total := 0
	for entry in level.decor:
		var path := str(entry.get("sprite", ""))
		if not ResourceLoader.exists(path):
			continue
		var texture: Texture2D = load(path)
		var is_object := str(entry.get("layer", LAYER_OBJECT)) == LAYER_OBJECT
		var spacing := float(entry.get("min_spacing", 18.0 if is_object else 0.0))
		for _i in int(entry.get("count", 0)):
			var position := _free_position(level, rng, placed, spacing)
			if position == Vector2.INF:
				break
			var sprite := Sprite2D.new()
			sprite.texture = texture
			sprite.position = position
			sprite.flip_h = rng.randf() < 0.5
			if is_object:
				# Base of the prop at its position, so y-sorting matches the characters' feet.
				sprite.offset = Vector2(0, -texture.get_height() * 0.5 + 1.0)
				GroundShadow.attach(sprite, texture.get_width() * 0.8)
				object_layer.add_child(sprite)
				placed.append(position)
			else:
				ground_layer.add_child(sprite)
			total += 1
	return total


static func _free_position(level: LevelDefinition, rng: RandomNumberGenerator, placed: Array[Vector2], spacing: float) -> Vector2:
	var spawn := level.player_spawn()
	for _attempt in 12:
		var candidate := Vector2(rng.randf_range(BORDER, level.map_size.x - BORDER), rng.randf_range(BORDER, level.map_size.y - BORDER)).floor()
		if candidate.distance_to(spawn) < SPAWN_CLEAR_RADIUS:
			continue
		var free := true
		if spacing > 0.0:
			for other in placed:
				if other.distance_to(candidate) < spacing:
					free = false
					break
		if free:
			return candidate
	return Vector2.INF
