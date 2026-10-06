# Pixel Fantasy Survival — MVP

Мобильная 2D pixel-art survival / action RPG (iOS / Android, portrait) по ТЗ «Technical Specification — MVP v0.1».

- Движок: **Godot 4.5.2** (зафиксирован; смена версии — отдельная задача миграции), typed GDScript
- Renderer: **Compatibility** (OpenGL ES 3.0), внутреннее разрешение 360×640, nearest-фильтрация, integer scaling
- Контент полностью data-driven (`game/data/*.json`), сохранения версионированы, игра работает без сети

## Структура репозитория

```
game/                      Godot-проект (project.godot)
  assets/                  спрайты, тайлсеты (сейчас — сгенерированные плейсхолдеры)
  data/                    контент: characters, enemies, items, levels, skills, progression, buildings, config
  scenes/                  main, ui/*, game/game, player/player, enemies/enemy
  scripts/
    core/                  автозагрузки: EventBus, Content, SaveManager, GameStateManager, SceneManager, GameManager, AudioManager
    data/                  определения сущностей, репозитории, источники контента
    gameplay/              player + компоненты, combat (DamageCalculator, CombatSystem), enemies + AI, items/loot, levels, vfx
    progression/           Profile (репозиторий данных игрока), UpgradeService
    input/                 InputCommand, InputRouter, виртуальный джойстик, тач-кнопки
    services/              Remote Config, Analytics, Crashlytics, Backend (Supabase) — за интерфейсами
    ui/                    экраны и оверлеи (без игровой логики)
  tests/                   юнит-тесты + smoke-тест полного игрового цикла
  export_presets.cfg       Android (arm64) и iOS (Xcode-проект, iOS 16+)
backend/supabase/          схема БД (контент + данные игрока, RLS) — задел под фазы 5–6
tools/build.sh             тесты и сборки
tools/gen_placeholder_sprites.py  генератор плейсхолдер-спрайтов
.github/workflows/build.yml       CI: тесты → Android APK → iOS Xcode-проект
```

## Запуск

1. Установить [Godot 4.5.2](https://godotengine.org/download/archive/4.5.2-stable/) (standard, не .NET).
2. Открыть `game/project.godot`, нажать Play. На десктопе: WASD/стрелки — движение, J/Space — атака, K — навык, L/Shift — рывок, I/Tab — сумка, Esc — пауза; мышь эмулирует тач (джойстик и кнопки).

## Тесты

```bash
GODOT=/path/to/Godot tools/build.sh test
```

Юнит-тесты (формулы урона, статы, XP-кривая, лут, валидация контента и ссылок между сущностями, сохранения и миграции, инвентарь, апгрейды, таблица переходов состояний) и smoke-тест, который headless проходит весь цикл: меню → выбор героя → выбор уровня → бой → level-up → выбор апгрейда → босс → победа и награды → второй забег → смерть → Game Over, с проверкой аналитических событий.

## Сборка

Нужны шаблоны экспорта Godot 4.5.2 (Editor → Manage Export Templates), для Android — Android SDK и JDK 17 (Editor Settings → Export → Android).

```bash
export GODOT=/path/to/Godot
tools/build.sh android-debug      # build/android/pixel-fantasy-survival-debug.apk (debug keystore создаётся при отсутствии)
tools/build.sh android-release    # нужны GODOT_ANDROID_KEYSTORE_RELEASE_PATH / _USER / _PASSWORD
IOS_TEAM_ID=XXXXXXXXXX tools/build.sh ios   # build/ios/PixelFantasySurvival.xcodeproj → подпись и архив в Xcode
```

CI (`.github/workflows/build.yml`): на каждый push/PR — тесты и debug APK (артефакт `android-apk`); release APK — если заданы секреты `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_ALIAS`, `ANDROID_KEYSTORE_PASSWORD`; iOS Xcode-проект — на тегах `v*` или вручную, при наличии секрета `IOS_TEAM_ID`.

## Агенты Claude Code

Эталонные агенты лежат в `tools/claude/agents/` (developer, tester, designer, manager); локальная папка `.claude/` не коммитится и собирается одной командой:

```bash
tools/claude/setup.sh                               # только агенты -> .claude/agents
GODOT=/path/to/Godot tools/claude/setup.sh --recommended   # + Godot-скиллы, ревью/коммиты, Godot MCP
GODOT=/path/to/Godot tools/claude/setup.sh --all           # + Supabase, Firebase, Aseprite (pixel art)
```

Плагины и MCP ставятся в scope `local` — только для этой копии репозитория. Список рекомендаций и его состав — в начале `tools/claude/setup.sh`. Изменения агентов вносятся в `tools/claude/agents/` и раздаются повторным запуском скрипта (локально изменённые файлы не перезаписываются без `--force`).

## Как устроено (соответствие ТЗ)

| ТЗ | Реализация |
|---|---|
| §6 модульная архитектура, gameplay не зависит от хранилища | `Content` (репозитории определений) и `Profile` (данные игрока) — единственные точки доступа к данным; источник контента — `ContentSource` (сейчас `LocalJsonContentSource`) |
| §7 data-driven, стабильные ID | все сущности в JSON с `id`; валидация дубликатов и ссылок при загрузке и в тестах |
| §8–10 Character / Enemy / Level | `CharacterDefinition`, `EnemyDefinition`, `LevelDefinition`; уровень = данные (волны, босс, награды, размер карты) |
| §9 AI отделён от врага | `ai_type` → `AiFactory`: chase, melee (с замахом), ranged, passive, boss (залп снарядов + призыв) |
| §12 Player из компонентов | Movement, Health, Combat, Experience, Inventory, Stats, Skill + PlayerController |
| §13 боевая система, формулы в DamageCalculator | `max(1, attack − defense)`, криты; `CombatSystem` не зависит от Player/Enemy |
| §14 XP-кривая в данных | `data/progression/xp_curve.json` |
| §15–16 апгрейды, дерево навыков | run-апгрейды при level-up и meta-апгрейды за золото (с prerequisites); узлы дерева заведены в данных как draft |
| §17 инвентарь | стаки, валюта, расходники, экипировка (бонусы к статам) |
| §18 строительство | только задел: данные `buildings.json` (draft), события в EventBus, таблицы в БД |
| §19 сохранения | `user://savegame.dat`, `save_version`, цепочка миграций, атомарная запись + резервная копия |
| §20–23 backend / БД / админка | `BackendClient` (интерфейс, офлайн), схема `backend/supabase/migrations` с draft/published и RLS |
| §24–25 статусы и версии контента | клиент грузит только `published`; `content_version` в манифесте и конфиге |
| §26 Remote Config | `RemoteConfigService`: дефолты из `game_config.json` + кэш удалённых значений; feature flags и множители баланса уже читаются игрой |
| §27–28 аналитика, Crashlytics | события из ТЗ формирует `AnalyticsEventBridge` по EventBus; `CrashLogger` (Logger API 4.5) отправляет ошибки как non-fatal |
| §31 состояния | `GameStateManager`: таблица разрешённых переходов, оверлеи ставят игру на паузу |
| §32 EventBus | враг публикует `enemy_killed` → опыт, лут, аналитика, HUD подписаны независимо |
| §34 pixel art | 360×640, viewport stretch + integer scale, nearest, snap к пикселям |
| §35 ввод | Touch/клавиатура/геймпад → `InputCommand` → `PlayerController` |

## Что не входит в эту сборку / требует решения

- **Арт и звук** — плейсхолдеры: спрайты сгенерированы `tools/gen_placeholder_sprites.py` (замена файлов 1:1 по тем же путям), звуков нет (`AudioManager` молча пропускает отсутствующие файлы).
- **Firebase (Analytics, Crashlytics, Remote Config)** — код-мосты готовы и ждут нативные плагины Godot для Android/iOS (singleton'ы `FirebaseAnalytics`, `FirebaseCrashlytics`). Подключение плагинов, `google-services.json` / `GoogleService-Info.plist` — отдельная задача; без них игра работает, события пишутся в debug-провайдер.
- **Supabase** — не подключён (по ТЗ backend не обязателен для MVP); SQL-схема не прогонялась на реальном инстансе.
- **Идентификатор приложения** `com.csp.pixelfantasysurvival` — временный, заменить в `export_presets.cfg`.
- **Android minSdk** — стандартный шаблон Godot даёт minSdk 24 (Android 7), что покрывает требование Android 9+. Для поднятия minSdk нужен gradle-build.
- Status effects из §13 пока не реализованы (в MVP Scope не обязательны).
