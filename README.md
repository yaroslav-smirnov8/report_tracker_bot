# Telegram Report Tracker Bot

Production‑ready Telegram bot for cohort‑style courses and team accountability. Participants submit daily and weekly reports using hashtags; the bot validates them, records progress, sends reminders, and generates an analytics‑rich Excel report.

## Project Analysis

### Core Problem
Teams running multi‑week courses or accountability programs need a low‑friction way to collect daily updates, enforce deadlines, and measure progress without manual tracking.

### Target Users and Use Cases
- Course organizers who need automatic progress tracking and reporting.
- Team leads running daily standups via Telegram.
- Accountability groups that need reminders and a progress overview.

### Value Proposition
- Zero‑friction input via hashtags in Telegram.
- Automatic reminders and late‑report notifications.
- Exportable analytics with streaks, trends, and leaderboards.

### Constraints and Assumptions
- Telegram Privacy Mode must be disabled for the bot to read non‑command messages.
- Course start date and timezone must be configured per group.
- MySQL/MariaDB is available for persistence.

### AI/LLM Appropriateness
Not required for core functionality. The current logic is deterministic. LLMs could be added later for natural language summaries, but it is optional.

## Architecture Design

### Frontend
- Telegram chat UI (buttons, commands, inline callbacks)
- No separate web frontend required

### Backend
- Python application using python‑telegram‑bot for command and message handling
- APScheduler for cron‑like background tasks
- SQLAlchemy for data access

### API Design
- Telegram Bot API interface (commands + callback queries)
- No public HTTP API in the current implementation

### AI Layer
- None in current scope
- Optional future: LLM summarization of progress and weekly insights

### Data Layer
- MySQL/MariaDB via SQLAlchemy
- Tables: chats, members, daily_records, settings, fines
- Excel export via OpenPyXL

### Infrastructure
- Single process bot (polling)
- Suitable for Docker or systemd deployment
- Horizontal scaling by sharding chats across bot instances (future)

### Security Considerations
- BOT_TOKEN stored in environment variables
- DB credentials stored in DB_URL
- Telegram admin checks for sensitive actions

### Performance Considerations
- Indexes on chat and date fields for daily checks
- Batch DB queries for report generation
- Scheduler load proportional to number of chats

## Tech Stack Selection

### Backend
- Python 3 + python‑telegram‑bot 13: stable and proven for Telegram bots
- APScheduler: reliable background scheduling
- SQLAlchemy: ORM with MySQL support
- OpenPyXL: Excel analytics output

### Data
- MySQL/MariaDB: simple to operate, good for transactional workloads

### Infra
- Docker or systemd deployment
- Basic CI for linting and unit tests (recommended)

## Repository Structure

```
frontend/
backend/
api/
infra/
docs/
tests/
scripts/
.env.example
```

## Project Overview
Telegram bot that tracks daily and weekly reports via hashtags, automatically reminds participants, and delivers a detailed Excel analytics report to admins.

## Features
- Daily/weekly hashtag validation with day/week numbering
- Per‑chat timezone and start date configuration
- Automated reminders and late‑report notifications
- Exportable Excel report with leaderboards, trends, and heatmap
- Admin controls to manage participants

## Tech Stack
- Frontend: Telegram UI (commands, buttons)
- Backend: Python, python‑telegram‑bot, APScheduler, SQLAlchemy
- Data: MySQL/MariaDB
- Analytics: OpenPyXL
- Infra: Docker/systemd compatible

## Architecture Diagram (Textual)

```
Telegram Users
   |
   v
Telegram Bot API
   |
   v
Python Bot (handlers + scheduler)
   |
   +--> SQLAlchemy --> MySQL/MariaDB
   |
   +--> OpenPyXL --> Excel report (.xlsx)
```

## Setup & Run Instructions

### Local Development
1. Install dependencies:
   ```bash
   pip install python-telegram-bot==13.* apscheduler sqlalchemy pymysql pytz openpyxl
   ```
2. Set environment variables:
   - `BOT_TOKEN` from BotFather
   - `DB_URL` MySQL connection string
3. Run:
   ```bash
   python main.py
   ```

### Production Notes
- Run as a systemd service or container
- Ensure Privacy Mode is disabled for the bot in group chats
- Use a dedicated MySQL user with limited permissions

## Environment Variables

| Variable   | Required | Description |
|------------|----------|-------------|
| BOT_TOKEN  | Yes      | Telegram bot token |
| DB_URL     | No       | SQLAlchemy DB URL (default uses local MySQL) |
| LOG_LEVEL  | No       | Logging level (default INFO) |

## API Overview
There is no public HTTP API. Interaction is via Telegram commands and inline buttons.

Key commands:
- `/menu` / `/buttons` — open actions menu
- `/join` — register as participant
- `/today` — show expected hashtags
- `/setstartdate YYYY-MM-DD` — set start date
- `/settimezone Europe/Moscow` — set timezone
- `/remove USER_ID` — remove participant
- `/status` — show current settings

## Roadmap
- Optional REST API for external dashboards
- LLM‑based weekly summaries
- Multi‑instance scaling via job partitioning
- Persistent job store for APScheduler

## License
MIT License
