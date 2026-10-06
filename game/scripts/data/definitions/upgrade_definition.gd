class_name UpgradeDefinition
extends ContentDefinition
## Upgrades with scope "run" are offered on level-up and last for one run.
## Upgrades with scope "meta" are bought with gold and persist in the profile.

const SCOPE_RUN := "run"
const SCOPE_META := "meta"

const TYPE_STAT := "stat"
const TYPE_SKILL_MODIFIER := "skill_modifier"
const TYPE_SKILL_UNLOCK := "skill_unlock"
const TYPE_HEAL := "heal"

var name: String = ""
var description: String = ""
var scope: String = SCOPE_RUN
var type: String = TYPE_STAT
var stat: String = ""
var mode: String = Stats.MODE_ADD
var value: float = 0.0
var skill_id: String = ""
var max_level: int = 1
var cost: int = 0
var cost_growth: float = 1.0
var prerequisites: Array[String] = []
## For skill modifiers: [{param, mode, value}]
var effects: Array[Dictionary] = []


func _parse(d: Dictionary) -> void:
	name = str(d.get("name", id))
	description = str(d.get("description", ""))
	scope = str(d.get("scope", scope))
	type = str(d.get("type", type))
	stat = str(d.get("stat", ""))
	mode = str(d.get("mode", mode))
	value = float(d.get("value", 0.0))
	skill_id = str(d.get("skill_id", ""))
	max_level = int(d.get("max_level", 1))
	cost = int(d.get("cost", 0))
	cost_growth = float(d.get("cost_growth", 1.0))
	prerequisites = to_string_array(d.get("prerequisites", []))
	effects = to_dict_array(d.get("effects", []))


## Price of buying the next level when `current_level` levels are already owned.
func cost_for_level(current_level: int) -> int:
	return roundi(cost * pow(cost_growth, current_level))


func validate() -> Array[String]:
	var errors := super.validate()
	if scope not in [SCOPE_RUN, SCOPE_META]:
		errors.append("%s: unknown scope '%s'" % [id, scope])
	if type == TYPE_STAT and stat not in Stats.ALL:
		errors.append("%s: unknown stat '%s'" % [id, stat])
	if max_level < 1:
		errors.append("%s: max_level must be >= 1" % id)
	return errors
