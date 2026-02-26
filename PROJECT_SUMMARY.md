# Telegram Report Tracker Bot

## 1. Project Summary (Plain English)
This is a Telegram bot that helps a team or course group collect daily and weekly check-ins without spreadsheets. People post short updates with simple hashtags, and the bot tracks who submitted on time, sends reminders, and generates an Excel report with progress and trends.

## 2. Problem Statement
Teams running multi-week programs often rely on manual tracking for daily updates. That creates missed deadlines, inconsistent reporting, and a lot of coordinator overhead. The goal is to make reporting effortless for participants and provide clear visibility for organizers.

## 3. Solution Approach
The bot runs inside Telegram and listens for specific hashtags in group chats. It stores each submission in a database, schedules reminders based on the group’s timezone and start date, and compiles analytics into a downloadable Excel report for admins.

## 4. My Role (Primary Developer)
- Designed the overall bot architecture, including handler flow, data model, and scheduling strategy.
- Implemented message parsing, validation rules, and reporting logic.
- Built the Excel analytics output and formatted it for readability.
- Owned database schema, data access patterns, and background jobs.
- Set up testing with isolated in-memory database fixtures.

## 5. Technical Complexity
- Real-time chat input with strict deadline logic and timezone handling.
- Scheduled jobs for reminders, late checks, and course milestones.
- Data aggregation for streaks, completion rates, and leaderboards.
- Tradeoff: polling-based Telegram bot for simplicity and reliability over webhooks.
- Deterministic rules-based system; no AI required for core behavior.

## 6. Business / User Value
- Reduces manual effort for organizers by automating reminders and progress tracking.
- Increases compliance by making reporting quick and visible in the chat.
- Provides clear progress visibility with exportable analytics for leadership.

## 7. Quality Signals
- Automated tests for reporting metrics and database updates.
- Clear separation between handlers, services, data models, and reports.
- Documented setup and operational constraints (privacy mode, timezone, start date).
- Database indexes and batch queries to keep daily checks efficient as groups grow.
