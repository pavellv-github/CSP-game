# Pixel Fantasy Survival — инструкции для агентов

Мобильная 2D pixel-art survival / action RPG на **Godot 4.5.2** (typed GDScript, Compatibility renderer, portrait 360×640). Проект Godot — в `game/`. Архитектура и соответствие ТЗ — в `README.md`, ТЗ на графику — в `docs/art/ART_BRIEF.md`.

## Главное
- Контент только в `game/data/*.json` со стабильными ID; доступ через `Content`, данные игрока — через `Profile`.
- Системы общаются через `EventBus`; состояния меняются только через `GameStateManager`.
- UI без игровой логики; тема — `UiKit.shared_theme()` (палитра из ключарта).
- Версию Godot не менять.
- Проверка: `GODOT=/Applications/Godot.app/Contents/MacOS/Godot tools/build.sh test`.
- Не коммитить и не пушить без явной просьбы.

## GodotPrompter
Перед реализацией любой системы Godot (движение, ввод, UI/HUD, AI, сохранения, анимация, экспорт и т. д.) проверь, есть ли подходящий скилл `godot-prompter:*`, и загрузи его. До написания кода коротко назови выбранный паттерн, отвергнутую альтернативу и причину выбора. Если скилл противоречит архитектурным правилам проекта выше, приоритет у правил проекта — сообщи о расхождении.
