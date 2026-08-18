<div align="center">

<img src="assets/banner.jpg" alt="OpenTTD WebAssembly — браузерный порт" width="800">

# OpenTTD · браузерный WebAssembly-порт

**OpenTTD 15.3 для браузерных игровых платформ с отдельными путями интеграции для Яндекс Игр и Playgama.**

[![Сборка Яндекс Игр](https://github.com/kalandos240/openttd-yandexgames/actions/workflows/final-package.yml/badge.svg)](https://github.com/kalandos240/openttd-yandexgames/actions/workflows/final-package.yml)
[![Playgama v10](https://github.com/kalandos240/openttd-yandexgames/actions/workflows/build-playgama-v10-cloud-saves.yml/badge.svg)](https://github.com/kalandos240/openttd-yandexgames/actions/workflows/build-playgama-v10-cloud-saves.yml)
![OpenTTD](https://img.shields.io/badge/OpenTTD-15.3-2f7d32?style=flat-square)
![WebAssembly](https://img.shields.io/badge/WebAssembly-Emscripten-654ff0?style=flat-square)
![Playgama](https://img.shields.io/badge/Playgama-Bridge%20v2-7c3aed?style=flat-square)

[English](README.md) · **Русский**

*Неофициальный пользовательский порт и проект воспроизводимой сборки/интеграции.*

</div>

---

## О проекте

Репозиторий содержит интеграционный слой, патчи и автоматизированные пайплайны для подготовки **OpenTTD 15.3** к публикации в браузере.

Полное дерево исходников OpenTTD здесь не хранится. CI загружает официальный релиз `OpenTTD/OpenTTD`, применяет платформенные веб-патчи, собирает игру через Emscripten и формирует готовые ZIP-пакеты.

> Это не официальный релиз OpenTTD. Проект не связан с командой OpenTTD, Яндексом или Playgama и не является их официальным продуктом.

## Текущая сборка Playgama — v10

Актуальный Playgama-пакет использует **Playgama Bridge JS Core v2** и включает:

- настольную браузерную сборку в landscape-ориентации;
- русский и английский языки, FreeType и корректную кириллицу;
- локальные сохранения OpenTTD через Emscripten IDBFS / IndexedDB;
- **облачные сохранения через Playgama `platform_internal`**;
- разбиение `.sav` на чанки по 64 КиБ;
- чередование облачных поколений A/B и запись метаданных только после полной загрузки;
- проверку размера и CRC32 перед восстановлением сейва;
- миграцию старого формата `openttdSaveV1`;
- сохранение локальной копии как fallback, если облачное хранилище платформы недоступно;
- встроенный **SimpleAI** и необходимые AI-библиотеки;
- локально поставляемые NewGRF/OpenGFX2 дополнения, выключенные по умолчанию;
- нативное окно лицензий с полным юридическим пакетом;
- межстраничную рекламу только в безопасных паузах; rewarded и banner отключены.

Активная система облачных сейвов больше не использует старое ограничение примерно **120 КБ**. Оставлен только технический защитный предел **64 МиБ на один `.sav`**, чтобы не допускать патологического потребления памяти браузера.

Подробности: **[docs/PLAYGAMA.md](docs/PLAYGAMA.md)** и **[docs/PLAYGAMA_ADDONS.md](docs/PLAYGAMA_ADDONS.md)**.

## Встроенные дополнительные материалы

В Playgama-сборке локально поставляются следующие опциональные пакеты:

- Iron Horse 4
- FIRS Industries 5
- Road Hog
- GIST — German Industries Set
- Early Vehicle Set
- OpenGFX2 Settings
- OpenGFX2 Classic

NewGRF **не включаются автоматически**. FIRS и GIST являются альтернативными наборами промышленности — их не следует одновременно включать в одной новой игре.

## Обложки для консоли Playgama

В репозитории лежат готовые файлы точных размеров:

| Формат | Файл |
|---|---|
| Квадрат 1:1 — 800×800 | [`assets/playgama/cover-square-800x800.jpg`](assets/playgama/cover-square-800x800.jpg) |
| Вертикальная 9:16 — 1080×1920 | [`assets/playgama/cover-portrait-1080x1920.jpg`](assets/playgama/cover-portrait-1080x1920.jpg) |
| Горизонтальная 16:9 — 1920×1080 | [`assets/playgama/cover-landscape-1920x1080.jpg`](assets/playgama/cover-landscape-1920x1080.jpg) |

## Сборка

### Playgama v10

1. Открой вкладку **Actions**.
2. Выбери **Build Playgama v10 cloud saves**.
3. Запусти workflow.
4. Скачай артефакт `openttd-playgama-v10-cloud-saves`.

Workflow берёт проверенную Playgama v8-сборку, применяет текущие исправления доставки дополнений, добавляет v10-систему облачных сохранений, заново собирает юридический пакет, прогоняет проверки сейвов и аддонов и создаёт финальный ZIP.

### Яндекс Игры

Отдельный пайплайн Яндекс Игр сохранён в **Final OpenTTD Package**. Платформенные изменения разделены, чтобы развитие Playgama-версии не меняло Яндекс-сборку незаметно.

## Документация

| Документ | Назначение |
|---|---|
| [Сборка](docs/BUILDING.md) | Окружение сборки и устранение ошибок |
| [Интеграция Playgama](docs/PLAYGAMA.md) | Bridge v2, lifecycle, реклама, облачные сейвы и поля публикации |
| [Дополнения Playgama](docs/PLAYGAMA_ADDONS.md) | NewGRF/OpenGFX2, состав и лицензирование |
| [Интеграция Яндекс Игр](docs/YANDEX_GAMES.md) | SDK, локаль и структура Яндекс-пакета |
| [Сторонние компоненты](THIRD_PARTY_NOTICES.md) | OpenTTD и включённые сторонние проекты |
| [Участие в разработке](CONTRIBUTING.md) | Правила для issues и pull requests |

## Структура репозитория

```text
.
├── .github/workflows/      # Воспроизводимые пайплайны браузерных сборок
├── assets/                 # Изображения репозитория и публикации
│   └── playgama/           # Обложки точных размеров для Playgama
├── ci/                     # Основные скрипты веб/Яндекс-сборки
├── docs/                   # Документация сборки и платформ
├── playgama/               # Bridge v2, аддоны, облачные сейвы и упаковка
├── LICENSE
├── THIRD_PARTY_NOTICES.md
├── README.md
└── README.ru.md
```

## Оригинальный проект и лицензии

OpenTTD — открытая транспортно-экономическая стратегия, поддерживаемая командой OpenTTD.

- Официальный исходный код: [`OpenTTD/OpenTTD`](https://github.com/OpenTTD/OpenTTD)
- Версия, на которую рассчитан порт: **15.3**
- Лицензия OpenTTD: **GNU GPL v2**

Базовые наборы, AI и опциональные NewGRF сохраняют собственные лицензии и уведомления. Финальная Playgama-сборка содержит полный комплект лицензий и сведений об исходном коде для распространяемых компонентов.

---

<div align="center">

**OpenTTD → WebAssembly → Яндекс Игры / Playgama**

</div>
