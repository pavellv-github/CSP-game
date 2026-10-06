class_name LootTableDefinition
extends ContentDefinition

var rolls: int = 1
## [{item_id, weight, min, max}] — empty item_id means "nothing dropped".
var entries: Array[Dictionary] = []


func _parse(d: Dictionary) -> void:
	rolls = int(d.get("rolls", 1))
	entries = to_dict_array(d.get("entries", []))


## Returns [{item_id, quantity}] for a single kill.
func roll(rng: RandomNumberGenerator, quantity_multiplier: float = 1.0) -> Array[Dictionary]:
	var drops: Array[Dictionary] = []
	var total_weight := 0.0
	for entry: Dictionary in entries:
		total_weight += float(entry.get("weight", 0))
	if total_weight <= 0.0:
		return drops
	for _i in rolls:
		var pick := rng.randf() * total_weight
		for entry: Dictionary in entries:
			pick -= float(entry.get("weight", 0))
			if pick > 0.0:
				continue
			var item_id := str(entry.get("item_id", ""))
			if not item_id.is_empty():
				var quantity := rng.randi_range(int(entry.get("min", 1)), int(entry.get("max", 1)))
				quantity = maxi(1, roundi(quantity * quantity_multiplier))
				drops.append({"item_id": item_id, "quantity": quantity})
			break
	return drops
