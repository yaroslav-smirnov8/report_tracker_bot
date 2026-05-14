# Telegram Report Tracker Bot

## 🚀 Overview
Telegram Report Tracker Bot is an operations-grade reporting system for cohort programs, accountability groups, and manager-led training environments. It turns everyday Telegram activity into a structured compliance and analytics pipeline: participants submit hashtag-based reports, the bot validates them against course timing rules, automates reminders, and delivers leadership-ready Excel reporting.

## 🎯 Problem
Teams running multi-week programs often manage participation manually through chat history, spreadsheets, and ad hoc reminders. That creates missed submissions, inconsistent enforcement, weak visibility into progress, and unnecessary coordinator overhead.

## 💡 Solution
This system embeds reporting directly into the collaboration channel teams already use. It captures daily and weekly submissions in Telegram, tracks performance per participant and per cohort, schedules deadline-aware reminders in each chat's timezone, and generates multi-sheet Excel analytics for admins without introducing a separate dashboard.

## ⚙️ Features
- Hashtag-driven reporting workflow for daily morning, daily evening, and weekly check-ins
- Per-chat configuration for course start date, timezone, and reporting conventions
- Automated reminder pipeline with one-hour and fifteen-minute deadline notifications
- Late-submission detection and targeted compliance nudges for missing participants
- Admin-controlled participant lifecycle management inside Telegram
- Progress visibility for both admins and participants via commands, menus, and DM delivery
- Excel analytics export with overview metrics, leaderboard, trend charts, attendance heatmap, raw records, and fines
- Course-aware logic that maps messages to expected day and week numbers across a 63-day program window
- Persistent SQL-backed state for chats, members, records, settings, fines, and scoring data

## 🧠 Architecture
The bot is built as a single-process event-driven backend with three main execution paths:

1. Telegram updates enter through `python-telegram-bot` handlers.
2. Messages are validated against course timing, expected hashtag number, and chat-level settings.
3. Valid submissions are persisted to SQL through SQLAlchemy models.
4. APScheduler jobs run independently to send reminders, check missing reports, and schedule course completion messages.
5. Admins can trigger Excel export generation, which aggregates transactional data into decision-friendly analytics sheets.

Key architectural decisions:
- Telegram-native UX instead of a custom frontend, reducing adoption friction for real teams
- Polling-based runtime for simpler deployment and operational reliability
- Deterministic rules engine instead of LLM-based parsing, which keeps reporting behavior predictable and auditable
- Per-chat scheduling and timezone support, allowing one bot instance to serve multiple cohorts with different operating cadences
- Analytics generation as a separate reporting layer, so operational data capture and management reporting stay decoupled

```mermaid
flowchart TD
    A[Participants in Telegram] --> B[Bot Handlers]
    B --> C[Validation Layer<br/>day/week logic, hashtags, admin rules]
    C --> D[SQLAlchemy Persistence]
    D --> E[(MySQL / MariaDB)]
    E --> F[Analytics Engine]
    F --> G[Excel Report for Admins]
    E --> H[APScheduler Jobs]
    H --> I[Reminders, Late Checks,<br/>Course Completion Messages]
    I --> A
```

## 🔧 Tech Stack
- Python 3
- `python-telegram-bot` 13.15
- APScheduler 3.10
- SQLAlchemy 2.0
- MySQL / MariaDB via PyMySQL
- OpenPyXL for analytics export
- PyTZ for timezone-aware scheduling
- Pytest-based test suite

## 🧪 Example Usage
Typical operator flow:

1. Admin adds the bot to a Telegram group and disables Privacy Mode for message visibility.
2. Admin sets the course start date with `/setstartdate 2026-02-01`.
3. Admin sets the reporting timezone with `/settimezone Europe/Moscow`.
4. Participants register with `/join` or are auto-recognized when they submit valid reports.
5. Participants post reports like `#morning12`, `#evening12`, or `#week2`.
6. The bot records submissions, sends reminder notifications before deadlines, and flags missing reports after cutoff.
7. Admin requests the Excel export and receives a workbook containing cohort KPIs, leaderboards, trends, and detailed records.

## 🎯 Why This Matters
For startups:
This system replaces manual coordination work with lightweight operational automation. Small teams can enforce discipline, measure engagement, and run structured programs without building a separate internal tool.

For AI systems:
It demonstrates the surrounding infrastructure real AI products need even when the core workflow is deterministic: event ingestion, state management, scheduling, rules enforcement, analytics output, and operator-friendly controls.

For automation:
It is a concrete example of chat-native workflow automation where the interface, orchestration engine, and reporting pipeline are tightly integrated. The result is a system that fits naturally into how teams already work while still producing structured business data.

## 📈 Possible Extensions
- Replace polling with webhooks for higher-throughput deployments
- Add REST or GraphQL APIs for external dashboards and integrations
- Store scheduler jobs persistently to improve restart resilience
- Add role-based admin tiers for larger organizations
- Introduce multi-cohort analytics across groups for portfolio-level reporting
- Add LLM-generated weekly summaries on top of the existing structured metrics
- Extend the scoring and fines models into a fuller performance management module
- Containerize and deploy as a horizontally partitioned multi-instance bot service

## Repository Layout
```text
app/
  core/        database, config, ORM models
  handlers/    Telegram commands, callbacks, message processing
  reports/     Excel analytics generation
  services/    scheduling and settings logic
tests/         reporting and persistence tests
main.py        application entrypoint
requirements.txt
.env.example
```

## Run Locally
```bash
pip install -r requirements.txt
```

Create a `.env` file:

```env
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
DB_URL=mysql+pymysql://botuser:password@localhost/botdb
LOG_LEVEL=INFO
```

Start the bot:

```bash
python main.py
```

Operational notes:
- Telegram Privacy Mode must be disabled for the bot to inspect group messages
- The database schema is created automatically on first run
- The default deployment model is a long-running single process with background scheduling

## Validation
The repository includes tests for reporting metrics, workbook generation, and daily record updates under `tests/`.

I could not run the suite in this workspace because neither `python` nor `pytest` is installed in the current environment.
