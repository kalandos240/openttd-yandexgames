<div align="center">

<img src="assets/banner.jpg" alt="OpenTTD WebAssembly — Яндекс Игры и Playgama" width="800">

# OpenTTD · WebAssembly-порт для Яндекс Игр и Playgama

**OpenTTD 15.3 в браузере через WebAssembly с отдельными, независимыми интеграциями для Яндекс Игр и Playgama.**

[![Сборка Яндекс Игр](https://github.com/kalandos240/openttd-yandexgames/actions/workflows/final-package.yml/badge.svg)](https://github.com/kalandos240/openttd-yandexgames/actions/workflows/final-package.yml)
[![Playgama v10](https://github.com/kalandos240/openttd-yandexgames/actions/workflows/build-playgama-v10-cloud-saves.yml/badge.svg)](https://github.com/kalandos240/openttd-yandexgames/actions/workflows/build-playgama-v10-cloud-saves.yml)
![OpenTTD](https://img.shields.io/badge/OpenTTD-15.3-2f7d32?style=flat-square)
![WebAssembly](https://img.shields.io/badge/WebAssembly-Emscripten-654ff0?style=flat-square)
![Яндекс Игры](https://img.shields.io/badge/Яндекс%20Игры-SDK-ffcc00?style=flat-square)
![Playgama](https://img.shields.io/badge/Playgama-Bridge%20v2-7c3aed?style=flat-square)

[English](README.md) · **Русский**

*Неофициальный пользовательский порт и проект воспроизводимой браузерной сборки OpenTTD.*

</div>

---

## О проекте

Этот репозиторий изначально создан для портирования **OpenTTD 15.3 на Яндекс Игры** и теперь также содержит отдельную интеграцию для **Playgama**.

Полное дерево исходников OpenTTD здесь не хранится. GitHub Actions загружает официальный релиз `OpenTTD/OpenTTD`, применяет платформенные веб-патчи, собирает игру через Emscripten и формирует готовые ZIP-пакеты.

**Яндекс Игры и Playgama — это две отдельные сборочные ветки.** Изменения Playgama не должны незаметно менять Яндекс-сборку, и наоборот.

> Это не официальный релиз OpenTTD. Репозиторий не связан с командой OpenTTD, Яндексом или Playgama и не является их официальным продуктом.

## Поддерживаемые платформы

| Возможность | Яндекс Игры | Playgama |
|---|---|---|
| OpenTTD 15.3 WebAssembly | ✅ | ✅ |
| Emscripten + FreeType | ✅ | ✅ |
| Русский и английский | ✅ | ✅ |
| Автовыбор языка платформы | ✅ | ✅ |
| Локальные сохранения через браузерное хранилище | ✅ | ✅ |
| Платформенная интеграция загрузки/жизненного цикла | Yandex Games SDK | Playgama Bridge v2 |
| Отдельный готовый ZIP | `openttd-yandexgames.zip` | `openttd-playgama-v10-cloud-saves.zip` |
| Облачные сейвы текущей ветки | отдельная Yandex-интеграция/локальное хранилище | chunked cloud saves v10 |
| Локально поставляемые NewGRF/OpenGFX2 | не часть основной Yandex-сборки | ✅ |

---

# Яндекс Игры

## Возможности порта для Яндекс Игр

Яндекс-ветка остаётся полноценной основной частью этого репозитория.

- **WebAssembly-сборка OpenTTD 15.3** через Emscripten.
- Инициализация **Yandex Games SDK** через `/sdk.js`.
- Запуск `YaGames.init()` до платформенно-зависимой логики.
- Интеграция **Yandex Loading API** — после готовности рантайма вызывается сигнал загрузки платформе.
- Чтение локали Яндекс Игр и автоматический выбор русского или английского языка на первом запуске.
- Сборка с **FreeType** для корректной кириллицы.
- Постоянные локальные данные OpenTTD через файловую систему Emscripten и браузерное хранилище.
- В основной пакет входят свободные базовые наборы **OpenGFX, OpenSFX и OpenMSX**.
- `index.html` находится в корне ZIP и готов для загрузки в консоль Яндекс Игр.
- Платформенные патчи применяются во время CI, поэтому исходный OpenTTD остаётся максимально близким к upstream.

Подробная схема интеграции: **[docs/YANDEX_GAMES.md](docs/YANDEX_GAMES.md)**.

## Сборка для Яндекс Игр

Основной workflow:

**Final OpenTTD Package** → `.github/workflows/final-package.yml`

1. Открой вкладку **Actions**.
2. Выбери **Final OpenTTD Package**.
3. Нажми **Run workflow**.
4. После успешной сборки скачай артефакт `openttd-yandexgames-final`.

На выходе получается:

```text
openttd-yandexgames.zip
```

Архив содержит `index.html` в корне и предназначен именно для публикации на **Яндекс Играх**.

---

# Playgama

## Текущая сборка Playgama — v10

Playgama существует как отдельная платформенная ветка поверх той же WebAssembly-базы OpenTTD.

Текущая версия включает:

- **Playgama Bridge JS Core v2**;
- desktop / landscape конфигурацию;
- русский и английский языки;
- локальные сохранения через IDBFS / IndexedDB;
- облачные сейвы через `platform_internal`;
- разбиение `.sav` на чанки по 64 КиБ;
- A/B-поколения облачных сохранений;
- проверку размера и CRC32 при восстановлении;
- миграцию старого `openttdSaveV1`;
- fallback на локальное сохранение при недоступности облака;
- встроенный SimpleAI и необходимые AI-библиотеки;
- опциональные локальные NewGRF/OpenGFX2;
- полный пакет лицензий и нативное окно лицензий;
- interstitial-рекламу только в безопасных паузах.

Старое ограничение примерно 120 КБ для облачного `.sav` в активной v10-системе больше не используется. Оставлен клиентский защитный предел 64 МиБ на один сейв.

Подробности:

- **[docs/PLAYGAMA.md](docs/PLAYGAMA.md)**
- **[docs/PLAYGAMA_ADDONS.md](docs/PLAYGAMA_ADDONS.md)**

## Дополнения Playgama

В Playgama-пакете локально поставляются:

- Iron Horse 4
- FIRS Industries 5
- Road Hog
- GIST — German Industries Set
- Early Vehicle Set
- OpenGFX2 Settings
- OpenGFX2 Classic

NewGRF не включаются автоматически. FIRS и GIST являются альтернативными наборами промышленности и не должны одновременно включаться в одной новой игре.

## Сборка Playgama v10

1. Открой **Actions**.
2. Выбери **Build Playgama v10 cloud saves**.
3. Запусти workflow.
4. Скачай `openttd-playgama-v10-cloud-saves`.

## Обложки Playgama

| Формат | Файл |
|---|---|
| 800×800 | [`assets/playgama/cover-square-800x800.jpg`](assets/playgama/cover-square-800x800.jpg) |
| 1080×1920 | [`assets/playgama/cover-portrait-1080x1920.jpg`](assets/playgama/cover-portrait-1080x1920.jpg) |
| 1920×1080 | [`assets/playgama/cover-landscape-1920x1080.jpg`](assets/playgama/cover-landscape-1920x1080.jpg) |

---

## Документация

| Документ | Назначение |
|---|---|
| [Сборка](docs/BUILDING.md) | Общая среда сборки и устранение ошибок |
| [Яндекс Игры](docs/YANDEX_GAMES.md) | Yandex SDK, локаль, Loading API, структура ZIP |
| [Playgama](docs/PLAYGAMA.md) | Bridge v2, lifecycle, реклама и облачные сейвы |
| [Дополнения Playgama](docs/PLAYGAMA_ADDONS.md) | NewGRF/OpenGFX2, версии и лицензирование |
| [Сторонние компоненты](THIRD_PARTY_NOTICES.md) | OpenTTD и сторонние проекты |
| [Участие в разработке](CONTRIBUTING.md) | Issues и pull requests |

## Структура репозитория

```text
.
├── .github/workflows/      # Яндекс + Playgama build pipelines
├── assets/                 # Баннер и publishing assets
│   └── playgama/           # Обложки Playgama
├── ci/                     # Основная WebAssembly/Yandex-сборка
├── docs/                   # Документация обеих платформ
├── playgama/               # Playgama Bridge, сейвы, аддоны, упаковка
├── LICENSE
├── THIRD_PARTY_NOTICES.md
├── README.md
└── README.ru.md
```

## Оригинальный проект и лицензирование

OpenTTD — открытая транспортная экономическая стратегия, поддерживаемая командой OpenTTD.

- Upstream: [`OpenTTD/OpenTTD`](https://github.com/OpenTTD/OpenTTD)
- Целевая версия: **15.3**
- Лицензия OpenTTD: **GNU GPL v2**

OpenGFX, OpenSFX, OpenMSX, AI и опциональные NewGRF/OpenGFX2 сохраняют собственные лицензии и уведомления. Платформенные сборки не меняют лицензию оригинального OpenTTD.

---

<div align="center">

**OpenTTD → WebAssembly → Яндекс Игры + Playgama**

</div>
