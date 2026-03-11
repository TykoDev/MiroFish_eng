<div align="center">

<img src="./static/image/MiroFish_logo_compressed.jpeg" alt="MiroFish Logo" width="75%"/>

Простой и универсальный движок коллективного интеллекта для прогнозирования чего угодно
</br>
<em>A Simple and Universal Swarm Intelligence Engine, Predicting Anything</em>

[![GitHub Stars](https://img.shields.io/github/stars/666ghj/MiroFish?style=flat-square&color=DAA520)](https://github.com/666ghj/MiroFish/stargazers)
[![GitHub Watchers](https://img.shields.io/github/watchers/666ghj/MiroFish?style=flat-square)](https://github.com/666ghj/MiroFish/watchers)
[![GitHub Forks](https://img.shields.io/github/forks/666ghj/MiroFish?style=flat-square)](https://github.com/666ghj/MiroFish/network)
[![Docker](https://img.shields.io/badge/Docker-Build-2496ED?style=flat-square&logo=docker&logoColor=white)](https://hub.docker.com/)

[English](./README-EN.md) | [中文文档](./README.md) | **Русский**

</div>

## ⚡ Обзор проекта

**MiroFish** — это AI-движок прогнозирования нового поколения на основе мультиагентных технологий. Он извлекает seed-информацию из реального мира (экстренные новости, законопроекты, финансовые сигналы) и автоматически строит высокоточный параллельный цифровой мир. В этом пространстве тысячи агентов с уникальными личностями, долгосрочной памятью и поведенческой логикой свободно взаимодействуют и эволюционируют. Вы можете динамически вводить переменные с «позиции бога» и точно моделировать будущие сценарии — **пусть будущее разыграется на цифровом полигоне, а решения победят после сотен симуляций**.

> Вам нужно лишь: загрузить seed-материалы (аналитический отчёт или интересную историю) и описать задачу прогнозирования на естественном языке.
>
> MiroFish вернёт: детальный отчёт-прогноз и интерактивный цифровой мир для глубокого исследования.

### Наше видение

MiroFish создаёт зеркало коллективного интеллекта, отражающее реальность. Захватывая эмерджентные эффекты от взаимодействия индивидов, система преодолевает ограничения традиционного прогнозирования:

- **На макроуровне**: лаборатория для принятия решений — тестируйте политики и PR-стратегии без рисков
- **На микроуровне**: творческая песочница для каждого — от развязки романа до проверки безумных гипотез

От серьёзного прогнозирования до увлекательных симуляций — мы даём возможность увидеть результат каждого «а что если».

## 🌐 Онлайн-демо

Попробуйте демо с прогнозированием резонансного медийного события: [mirofish-live-demo](https://666ghj.github.io/mirofish-demo/)

## 🔄 Как это работает

1. **Построение графа знаний**: извлечение seed-данных из реальности, инъекция индивидуальной и коллективной памяти, построение GraphRAG
2. **Настройка среды**: извлечение сущностей и связей, генерация персонажей, инъекция параметров симуляции
3. **Запуск симуляции**: параллельная симуляция на двух платформах, автоматический анализ задачи прогнозирования, динамическое обновление временной памяти
4. **Генерация отчёта**: ReportAgent использует набор инструментов для глубокого взаимодействия с симулированной средой
5. **Глубокое взаимодействие**: диалог с любым агентом симулированного мира и с ReportAgent

## 🚀 Быстрый старт

### Вариант 1: Запуск из исходников (рекомендуется)

#### Требования

| Инструмент | Версия | Описание | Проверка |
|-----------|--------|----------|----------|
| **Node.js** | 18+ | Среда для фронтенда, включает npm | `node -v` |
| **Python** | ≥3.11, ≤3.12 | Среда для бэкенда | `python --version` |
| **uv** | Последняя | Менеджер пакетов Python | `uv --version` |

#### 1. Настройка переменных окружения

```bash
# Скопируйте пример конфигурации
cp .env.example .env

# Отредактируйте .env, укажите API-ключи
```

**Обязательные переменные:**

```env
# Конфигурация LLM API (поддерживается любой API в формате OpenAI SDK)
# Подойдёт OpenAI, Groq, Together AI, любой OpenAI-совместимый провайдер
LLM_API_KEY=ваш_api_ключ
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL_NAME=llama-3.3-70b-versatile

# Конфигурация Zep Cloud
# Бесплатного лимита достаточно для базового использования: https://app.getzep.com/
ZEP_API_KEY=ваш_zep_ключ
```

#### 2. Установка зависимостей

```bash
# Установка всех зависимостей одной командой (корень + фронтенд + бэкенд)
npm run setup:all
```

Или пошагово:

```bash
# Установка Node-зависимостей (корень + фронтенд)
npm run setup

# Установка Python-зависимостей (бэкенд, автоматическое создание виртуального окружения)
npm run setup:backend
```

#### 3. Запуск

```bash
# Запуск фронтенда и бэкенда одновременно (из корня проекта)
npm run dev
```

**Адреса сервисов:**
- Фронтенд: `http://localhost:3000`
- API бэкенда: `http://localhost:5001`

**Раздельный запуск:**

```bash
npm run backend   # Только бэкенд
npm run frontend  # Только фронтенд
```

### Вариант 2: Docker

```bash
# 1. Настройте переменные окружения (как выше)
cp .env.example .env

# 2. Запустите
docker compose up -d
```

По умолчанию читается `.env` из корня проекта. Порты: `3000 (фронтенд)` / `5001 (бэкенд)`

## 📄 Благодарности

**MiroFish создан при стратегической поддержке Shanda Group!**

Движок симуляции MiroFish построен на базе **[OASIS](https://github.com/camel-ai/oasis)** — спасибо команде CAMEL-AI за открытый исходный код!

## 🇷🇺 Русская локализация

Русский перевод интерфейса и документации выполнен при поддержке:

- **Артём Машин** — Telegram: [@aa_mashin](https://t.me/aa_mashin) | Threads: [@mashin_aa](https://www.threads.com/@mashin_aa)
- Проект **СИНДИКАТ AI** — автономная фабрика проектов на AI-агентах

---

## 📈 Статистика проекта

<a href="https://www.star-history.com/#666ghj/MiroFish&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=666ghj/MiroFish&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=666ghj/MiroFish&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=666ghj/MiroFish&type=date&legend=top-left" />
 </picture>
</a>
