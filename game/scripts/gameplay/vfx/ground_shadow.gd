class_name GroundShadow
extends Sprite2D
## Soft-edged ellipse under a character's feet. Drawn by code (style v2): sprites carry no
## baked shadows, so one shadow works on any ground.

const COLOR := Color("#2a1d16")
const ALPHA := 0.32

static var _texture: Texture2D


## Adds a shadow as the first child of `body` (drawn under the sprite), `width` px wide.
static func attach(body: Node2D, width: float) -> GroundShadow:
	var shadow := GroundShadow.new()
	shadow.texture = _ellipse_texture()
	shadow.scale = Vector2.ONE * (width / shadow.texture.get_width())
	shadow.modulate = Color(COLOR, ALPHA)
	shadow.position = Vector2(0, 1)
	body.add_child(shadow)
	body.move_child(shadow, 0)
	return shadow


## 16x6 pixel ellipse, opaque white (tinted by modulate), crisp pixel edge.
static func _ellipse_texture() -> Texture2D:
	if _texture != null:
		return _texture
	var image := Image.create(16, 6, false, Image.FORMAT_RGBA8)
	var center := Vector2(8.0, 3.0)
	for y in 6:
		for x in 16:
			var d := Vector2((x + 0.5 - center.x) / 8.0, (y + 0.5 - center.y) / 3.0)
			if d.length_squared() <= 1.0:
				image.set_pixel(x, y, Color.WHITE)
	_texture = ImageTexture.create_from_image(image)
	return _texture
