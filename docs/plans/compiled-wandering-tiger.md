# Ребилд MoneyPrinterTurbo: русский по умолчанию + OpenRouter + дизайн + оптимизация сборки

## Context

MoneyPrinterTurbo уже развёрнут в прод на сервере (`/home/nel/money`, 2 контейнера webui+api, healthcheck). Задача — пересобрать «под ключ»: русский интерфейс по умолчанию, LLM через OpenRouter, улучшить дизайн, проверить на ошибки, оптимизировать Docker-сборку.

**Что выяснилось при исследовании (важно для скоупа):**
- Русский перевод **уже готов на 100%** (`webui/i18n/ru.json`, 168/168 ключей) — дописывать нечего, только сменить дефолт.
- OpenRouter **поддерживается из коробки** через `llm_provider = "openai"` + `openai_base_url` — код менять не нужно.
- «kea»/«банан»/nanabanana в проекте отсутствуют. По решению пользователя — **источник видео = сток Pexels**, интеграция генерации картинок nanabanana **вне скоупа** (отдельно, позже).
- Реальное состояние `config.toml` на момент планирования: `openai_api_key` пустой, `openai_base_url` пустой, `pexels_api_keys` пустой, `language = "en"`. То есть ключи придётся ввести при реализации (вопреки «ключ уже есть» — его в конфиге нет).

## Скоуп (согласовано)
1. **Русский по умолчанию** — сменить дефолт языка UI.
2. **LLM через OpenRouter** — `llm_provider=openai` + base_url + дешёвая платная модель (gpt-4o-mini).
3. **Дизайн** — тема Streamlit + аккуратный CSS (полировка, без глубокого редизайна).
4. **Проверка на ошибки** — прогнать тесты проекта, линт, ревью изменений.
5. **Оптимизация сборки** — multi-stage Dockerfile, убрать китайские зеркала, уменьшить образ.

## Вне скоупа
- Интеграция nanabanana / AI-генерации картинок.
- Глубокий редизайн layout, модуляризация Main.py.
- GPU-сборка.

---

## Изменения по файлам

### 1. Русский язык по умолчанию
- `config.toml` → `[ui] language = "ru"` (было `"en"`, строка ~108).
- `config.example.toml` → в секции `[ui]` задать `language = "ru"` (чтобы новые установки тоже стартовали на русском).
- Механизм: `webui/Main.py:141-142` берёт `config.ui.get("language", system_locale)`. Правки кода не требуется.

### 2. OpenRouter (LLM)
- `config.toml`:
  - `llm_provider = "openai"` (уже так)
  - `openai_base_url = "https://openrouter.ai/api/v1"`
  - `openai_model_name = "openai/gpt-4o-mini"` (дешёвая платная)
  - `openai_api_key = "<ключ>"` — ввести через файл `openrouter_key.txt` (прочитать, вписать, удалить файл; значение не эхоить).
- Код не трогаем: `app/services/llm.py` уже поддерживает openai-совместимый base_url.

### 3. Pexels (иначе видео не соберётся — блокер для теста)
- `config.toml` → `pexels_api_keys = ["<ключ>"]`. Ключ бесплатный (pexels.com/api). Ввести через файл аналогично.

### 4. Дизайн: тёмная тема + CSS-полировка (визуал, логику не трогаем)

**4a. `webui/.streamlit/config.toml`** — дописать секцию `[theme]` (сохранить `[browser]`):
```toml
[theme]
base = "dark"
primaryColor = "#6C5CE7"            # брендовый индиго — primary-кнопка, слайдеры, фокус
backgroundColor = "#0E1117"
secondaryBackgroundColor = "#1A1D29" # карточки-контейнеры
textColor = "#E6E8EF"
font = "sans serif"
borderColor = "#2A2E3D"
```
Тема применяется на первом рендере; правок кода не требует. Хочешь светлую — меняется только этот блок.

**4b. `webui/Main.py` строки 45-52** — заменить существующий `streamlit_style` на расширенный `custom_css` (тот же вызов `st.markdown(..., unsafe_allow_html=True)` на строке 52). Решение — **заменить, а не добавлять** второй блок (старое правило `h1{padding-top:0}` входит в новый CSS, чтобы не дублировать).

CSS — только косметика (radius, hover, тени, отступы, фокус-ринг). Таргетит **стабильные** селекторы (`.stButton`, `.stExpander`, `.stTabs`, `[data-testid="stVerticalBlockBorderWrapper"]`, `data-baseweb="tab"`) и CSS-переменные темы (`var(--primary-color)`), не хешированные `css-xxxx` классы. Никаких `display/flex/position/width` на layout-обёртках Streamlit → грид и колонки не ломаются. Полный CSS — в результатах Plan-агента (готов к вставке).

### 5. Оптимизация Dockerfile: multi-stage + убрать китайские зеркала

Заменить `Dockerfile` целиком на 2-stage:
- **builder** (`python:3.11-slim-bullseye`): `build-essential`+`git`, `pip install --prefix=/install` — изолированное дерево пакетов, компиляторы и pip-кэш НЕ попадают в финал.
- **runtime** (тот же base): только `ffmpeg`+`imagemagick` (нужны в рантайме для moviepy), IM6 policy-fix (bullseye → `/etc/ImageMagick-6/`, НЕ прыгать на bookworm/IM7 — сломает sed), `COPY --from=builder /install /usr/local`, затем `COPY . .`.
- Убрать build-args `DOCKER_BUILD_MIRROR`/`PIP_USE_OFFICIAL` и всю лестницу aliyun→tsinghua→debian для apt и pip. Официальные Debian/PyPI.

Инвариант корректности: `--prefix=/install` → `/usr/local` работает только потому, что оба stage на **идентичном** base-образе (тот же Python 3.11, тот же layout site-packages). Console-скрипты (`streamlit`, `uvicorn`) попадают в `/usr/local/bin` → `CMD` работает.

**Экономия:** ~350-600MB (уходят компиляторы/git/pip-кэш), цель **2.11GB → ~1.5-1.7GB**. Rebuild при неизменном `requirements.txt` — почти мгновенный (builder-слой кэшируется). Полный Dockerfile — в результатах Plan-агента.

_Примечание:_ `faster-whisper` тянет CTranslate2/av, а НЕ torch — поэтому CPU-образ ~2GB, и multi-stage даёт умеренную, а не радикальную экономию. `resource/` (198MB шрифты+песни) остаётся в образе — вынос в volume вне скоупа (риск сломать рантайм).

---

## Порядок работ (с раскладкой по агентам/моделям)

Правки делаются в рабочей копии `/home/nel/money`, git-ветка `rebuild/ru-openrouter-design` (форк Nelson053-n). Прод (`:prod`) НЕ трогаем до финальной проверки.

1. **Конфиги** (дешёвая модель, механически): `language="ru"`, OpenRouter base_url/model, ключи через файлы (`openrouter_key.txt`, `pexels_key.txt` → прочитать, вписать, удалить, не эхоить).
2. **Дизайн** (дорогая уже спроектировала → применение дешёвой): `[theme]` + замена CSS-блока в Main.py.
3. **Dockerfile** (применение дешёвой по готовому проекту).
4. **Проверка на ошибки** (параллельные агенты):
   - Unit-тесты: `python -m unittest discover -s test` (llm, video, material, voice — 4354 строк).
   - `/code-review` по диффу (дорогая модель — ревью качества и багов).
   - Сборка `:next`, verification-чек-лист из Plan-агента (ffmpeg/convert -version, import streamlit/moviepy/faster_whisper/litellm, policy.xml пропатчен).
5. **Smoke + прод-swap** (см. Verification).

## Verification (end-to-end)
1. `docker build -t moneyprinterturbo:next .` → размер < 2.11GB (`docker images`).
2. Verification-команды Plan-агента против `:next` (бинарники, импорты, policy fix).
3. Временный контейнер на порту 8599 с примонтированными config.toml+storage → открыть UI: **интерфейс на русском**, тёмная тема применена.
4. В UI: OpenRouter выбран, задать тему видео → **сгенерировать короткое видео** (нужны Pexels + OpenRouter ключи) → mp4 в `storage/`.
5. Тег бэкапа `moneyprinterturbo:prod-backup` со старого образа, затем `docker tag :next :prod`, пересоздать прод-контейнеры (через `docker run`, т.к. compose v1 багует — см. [[docker-compose-v1-incompatible]]). Оба healthy, HTTP 200.
6. Rollback при проблеме: retag `:prod-backup` → `:prod`, пересоздать.

## Блокеры (нужно от тебя при реализации)
- **Ключ OpenRouter** — в конфиге его нет (проверено). Положить в `openrouter_key.txt`.
- **Ключ Pexels** — тоже пустой. Без него шаг 4 (тестовая генерация) невозможен. Положить в `pexels_key.txt`.

## Модели (по запросу пользователя)
- Дорогие (Opus/Plan-агенты) — планирование, дизайн-архитектура, code-review. ✅ уже использованы для ресёрча и дизайна.
- Дешёвые (Haiku/Sonnet-агенты) — механические правки конфигов/CSS/Dockerfile, прогон тестов.
