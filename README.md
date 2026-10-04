# Telegram-бот на Haystack + Docling + Pinecone

Персональный Telegram-помощник с долговременной памятью в векторной базе, RAG по загруженным документам и Haystack Agent с внешними API (собаки, Vision).

## Что было сделано

### Эволюция проекта

1. **Первая версия** — монолит в каталоге `example/hay/` (`bot.py`, `assistant.py`, `haystack_memory.py`): Haystack Agent, Pinecone, инструменты dog.ceo / kinduff, команды памяти и сессии.
2. **Вторая версия (v2)** — модульная архитектура: компоненты, Haystack-пайплайны индексации и генерации, обработка файлов через **Docling**, сохранение чанков в Pinecone, краткое резюме после загрузки файла.
3. **Перенос в корень репозитория** — рабочий код, `.env`, `venv` и точка входа `main.py` лежат в корне `VPg07`, без привязки к `example/`.

### Что добавлено (относительно v1)

| Возможность | Описание |
|-------------|----------|
| **Загрузка документов** | PDF, DOCX, PPT, HTML, изображения и др. (лимит 20 МБ в Telegram) |
| **Docling** | Парсинг структуры, чанки `DOC_CHUNKS`, метаданные страницы |
| **`ingestion_pipeline`** | Docling → обогащение meta → OpenAI embed → Pinecone |
| **`generation_pipeline`** | Запрос → retriever по чанкам пользователя → prompt → LLM |
| **Резюме файла** | Одно предложение после успешной индексации |
| **RAG в диалоге** | При текстовых сообщениях подмешиваются релевантные фрагменты файлов |
| **Модульная структура** | `components/`, `pipelines/`, `services/`, `bot/` |

Метаданные каждого чанка в Pinecone: `file_name`, `chunk_index`, `page_number` (если есть), `kind=document_chunk`, `user_id`.

### Что сохранено из v1 (без изменения поведения)

- Команды `/start`, `/help`, `/memory`, `/forget`, `/reset`
- Pinecone-память диалога с дедупликацией по косинусному сходству
- Haystack **Agent** с инструментами: случайный факт о собаках, фото + описание породы (OpenAI Vision)
- Отправка фото dog.ceo, если в ответе есть URL
- Краткая сессия чата в памяти процесса (отдельно от Pinecone)
- Блокировка второго экземпляра polling (файл `.bot.lock`)

### Что удалено / устарело

| Было | Статус |
|------|--------|
| `example/hay/` как основное приложение | Перенесено в корень; каталог `example/` в `.gitignore` (устаревшая копия) |
| `hay_v2_bot/` | Промежуточная папка; логика в корне, каталог в `.gitignore` |
| `.env` в `example/` | Перенесён в **корень** проекта |
| `example/venv` | Перенесён в **`venv/`** в корне |

Файл `.env` и каталог `venv/` **не коммитятся** (см. `.gitignore`). В репозитории есть только `.env.example`.

---

## Структура проекта

```
VPg07/
  main.py                 # запуск бота
  config.py               # загрузка .env из корня
  requirements.txt
  .env.example
  components/             # Haystack-компоненты, Pinecone, память
  pipelines/              # ingestion, generation, summarization
  services/               # assistant, ingestion, dog_tools
  bot/
    handlers/             # commands, text, documents
    context.py, session.py, lock.py, messaging.py
```

---

## Требования

- Python 3.12+ (рекомендуется)
- Аккаунты и ключи: **Telegram Bot Token**, **OpenAI** (или совместимый API), **Pinecone**
- Для Docling при первом запуске возможна загрузка моделей/t tokenizer (нужен интернет; установка `docling` тяжёлая из‑за `torch`)

---

## Установка и запуск

```bash
cd VPg07

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
```

Скопируйте шаблон окружения и заполните ключи:

```bash
copy .env.example .env         # Windows
# cp .env.example .env         # Linux/macOS
```

Запуск бота (из корня проекта):

```bash
python main.py
```

Одновременно с тем же `TELEGRAM_BOT_TOKEN` должен работать **только один** процесс бота.

---

## Переменные окружения

| Переменная | Назначение |
|------------|------------|
| `TELEGRAM_BOT_TOKEN` | Токен бота |
| `OPENAI_API_KEY` | API для чата, эмбеддингов и Vision |
| `OPENAI_CHAT_MODEL` | Модель агента (по умолчанию `gpt-4o-mini`) |
| `OPENAI_BASE_URL` | Необязательно: совместимый OpenAI API |
| `OPENAI_EMBEDDING_MODEL` | Модель эмбеддингов |
| `OPENAI_EMBEDDING_DIMENSIONS` | Размерность вектора (должна совпадать с индексом Pinecone) |
| `PINECONE_*` | Ключ, индекс, регион, namespace |
| `MEMORY_RETRIEVAL_TOP_K` | Сколько записей памяти подтягивать в контекст |
| `DOCUMENT_RETRIEVAL_TOP_K` | Сколько чанков документов подтягивать |
| `CHAT_SESSION_MAX_MESSAGES` | Длина сессии в RAM |
| `DOC_CHUNK_TOKENIZER` | HF-модель для `HybridChunker` (Docling) |

---

## Как пользоваться ботом

### Текст

Напишите сообщение — бот ответит с учётом:

- истории текущей сессии;
- долговременной памяти в Pinecone;
- фрагментов загруженных вами файлов (RAG).

Можно просить факт о собаках или картинку с описанием породы — агент вызовет инструменты.

### Файл

Отправьте документ как **файл** в Telegram (не как сжатое фото, если нужен PDF/DOCX).

1. «Файл получен. Запускаю анализ…»
2. Индексация через Docling и Pinecone
3. «Готово. Я изучил этот файл…»
4. Одно предложение — краткое резюме содержимого

Дальше можно задавать вопросы по документу обыным текстом.

### Команды

| Команда | Действие |
|---------|----------|
| `/start`, `/help` | Приветствие и справка |
| `/memory` | Что сохранено в памяти + число фрагментов документов |
| `/forget` | Удалить память **и** все чанки документов пользователя в Pinecone |
| `/reset` | Сбросить только сессию диалога в RAM (Pinecone не трогает) |

---

## Пайплайны (кратко)

**Ingestion:** `DoclingConverter` → `DocumentMetaEnricher` → `OpenAIDocumentEmbedder` → `DocumentWriter` → Pinecone.

**Generation (RAG по файлам):** эмбеддинг вопроса → `PineconeEmbeddingRetriever` (фильтр `user_id` + `document_chunk`) → prompt → OpenAI Chat.

**Диалог:** retriever документов + retriever памяти → system-контекст → Haystack **Agent** (как в v1).

---

## `.gitignore`

Игнорируются:

- `.env` и локальные варианты секретов;
- `venv/`, `.venv/`;
- `__pycache__`, артефакты сборки и кэши линтеров;
- `.bot.lock`;
- IDE (`.idea/`, `.vscode/`);
- устаревшие каталоги `example/`, `hay_v2_bot/`, `legacy/`.

**Не игнорируются:** исходный код, `requirements.txt`, `.env.example`, `README.md`.

---

## Устранение неполадок

- **409 Conflict** от Telegram — уже запущен второй экземпляр бота; остановите лишний процесс или удалите `.bot.lock`, если процесс завершился некорректно.
- **Docling / pip timeout** — повторите установку с увеличенным таймаутом:  
  `pip install --default-timeout=300 -r requirements.txt`
- **Размерность эмбеддингов** — `OPENAI_EMBEDDING_DIMENSIONS` должна совпадать с настройками индекса Pinecone.
