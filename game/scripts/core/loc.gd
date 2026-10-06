class_name Loc
extends RefCounted
## Localization helpers. UI strings use semantic keys from translations/ui.csv;
## content names/descriptions use keys derived from stable IDs (translations/content.csv):
## character_warrior -> CHARACTER_WARRIOR_NAME / CHARACTER_WARRIOR_DESC.
## Missing content keys fall back to the text in the JSON data.

const DEFAULT_LOCALE := "ru"
const SUPPORTED_LOCALES: Array[String] = ["ru", "en"]


static func apply_locale(locale: String) -> void:
	TranslationServer.set_locale(locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE)


## Translated UI string.
static func t(key: String) -> String:
	return str(TranslationServer.translate(key))


static func name_of(definition: ContentDefinition) -> String:
	return _content(definition.id, "NAME", str(definition.raw.get("name", definition.id)))


static func desc_of(definition: ContentDefinition) -> String:
	return _content(definition.id, "DESC", str(definition.raw.get("description", "")))


static func content_key(id: String, suffix: String) -> String:
	return "%s_%s" % [id.to_upper(), suffix]


static func _content(id: String, suffix: String, fallback: String) -> String:
	var key := content_key(id, suffix)
	var text := str(TranslationServer.translate(key))
	return fallback if text == key else text
