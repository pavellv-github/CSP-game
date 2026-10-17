# Pixel Fantasy Survival — инструкции для агентов

Мобильная 2D pixel-art survival / action RPG на **Godot 4.5.2** (typed GDScript, Compatibility renderer, landscape 640×360). Проект Godot — в `game/`. Архитектура и соответствие ТЗ — в `README.md`, ТЗ на графику — в `docs/art/ART_BRIEF.md`.

## Главное
- Контент только в `game/data/*.json` со стабильными ID; доступ через `Content`, данные игрока — через `Profile`.
- Системы общаются через `EventBus`; состояния меняются только через `GameStateManager`.
- UI без игровой логики; тема — `UiKit.shared_theme()` (палитра из ключарта).
- Игра на русском (локализация `TranslationServer`, колонки ru/en): все тексты UI — ключи в `game/translations/ui.csv` через `Loc.t()`; названия и описания контента — `Loc.name_of()/desc_of()` и ключи `<ID>_NAME/_DESC` в `game/translations/content.csv`. Строки прямо в коде не писать; тест проверяет, что у контента есть русский перевод.
- Технический долг: всё, что сознательно откладывается, упрощается или требует оптимизации, сразу записывается в `docs/TECH_DEBT.md` (формат — в шапке документа); закрытые пункты переносятся в «Закрыто».
- Источники правды вне кода: все механики описываются схемами в Miro (https://miro.com/app/board/uXjVEe5RNQk=/), весь визуал (скриншоты, спрайты, иконки, референсы) вносится в Figma (https://www.figma.com/design/oOGt0CIVvhaxkm8a1DHcEw/CSP-game) по группам, на странице версии `v<game_version> · <дата> · <git sha>`; в Miro картинок не держим. После изменения механик, графики или UI документация (`README.md`, `docs/`) актуализируется в том же этапе.
- Версию Godot не менять.
- Проверка: `GODOT=/Applications/Godot.app/Contents/MacOS/Godot tools/build.sh test`.
- Не коммитить и не пушить без явной просьбы.

