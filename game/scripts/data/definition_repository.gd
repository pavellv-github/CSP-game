class_name DefinitionRepository
extends RefCounted
## In-memory repository of one content collection, indexed by stable ID.
## Gameplay asks repositories for definitions and never knows where the data came from.

var collection: String
var _factory: Callable
var _by_id: Dictionary = {}
var _ordered: Array[ContentDefinition] = []


## `factory` takes a Dictionary and returns a ContentDefinition subclass instance.
func _init(collection_name: String, factory: Callable) -> void:
	collection = collection_name
	_factory = factory


## Replaces the repository contents. Returns validation errors (empty if everything is fine).
func load_entries(entries: Array, include_unpublished: bool = false) -> Array[String]:
	var errors: Array[String] = []
	_by_id.clear()
	_ordered.clear()
	for entry: Variant in entries:
		if not entry is Dictionary:
			errors.append("%s: entry is not an object" % collection)
			continue
		var definition: ContentDefinition = _factory.call(entry)
		for problem in definition.validate():
			errors.append("%s: %s" % [collection, problem])
		if definition.id.is_empty():
			continue
		if _by_id.has(definition.id):
			errors.append("%s: duplicate id '%s'" % [collection, definition.id])
			continue
		# The client only sees published content; drafts are visible to tools/tests on request.
		if not include_unpublished and not definition.is_published():
			continue
		_by_id[definition.id] = definition
		_ordered.append(definition)
	return errors


func get_by_id(id: String) -> ContentDefinition:
	return _by_id.get(id)


func has_id(id: String) -> bool:
	return _by_id.has(id)


func get_all() -> Array[ContentDefinition]:
	return _ordered.duplicate()


func ids() -> Array[String]:
	var result: Array[String] = []
	for definition in _ordered:
		result.append(definition.id)
	return result


func size() -> int:
	return _ordered.size()
