# Refactoring Plan: English Translation

## Overview
This document outlines the systematic refactoring plan to translate all human language and written text within the repository from its current language (primarily Chinese) into English. The goal is to ensure the entire codebase is universally understandable.

## Scope of Translation
- **Code Comments:** Python, JavaScript, Vue template comments.
- **Docstrings:** Function, class, and module-level descriptions.
- **User Interface (UI) Text:** All text elements in `.vue` and `.html` files intended for user display.
- **Logging and Error Messages:** Hardcoded `print`, `logging`, `console.log`, and `throw/raise Exception` text strings.
- **Configuration and Environment Setup Texts:** `.env.example`, `requirements.txt` comments, `docker-compose.yml` comments.
- **Documentation:** `README.md` and other documentation files.

## Guidelines
1. **Meaningful Translation:** Avoid direct word-for-word translations that sound unnatural. Use standard technical terminology (e.g., "Knowledge Graph" instead of "Knowledge Map" if context dictates).
2. **Logic Preservation:** Ensure that keys, variable names, and programmatic strings (e.g., event names, API endpoints, JSON keys) are only translated if they are safe to do so. If an API expects a specific Chinese string as a payload parameter or key, **do not change it** unless the backend parser is updated simultaneously. Primarily focus on text meant for human consumption.
3. **Consistency:** Keep phrasing consistent across the application. E.g., if translating "分析" as "Analyze", stick to "Analyze" in all similar contexts instead of mixing with "Examine".

## Process Flow
1. **Initialize Tracking:** Establish `STATUS.md` to track which files have been checked and translated.
2. **Backend Services Refactoring:** Begin with utility scripts and models, working up to services and APIs. Translating log messages and docstrings will clear up backend intentions.
3. **Frontend Refactoring:** Translate the user interface components (`src/components/`, `src/views/`) to ensure the user-facing application is in English.
4. **Root & Docs Refactoring:** Align the main `README.md` with the English translation and clean up root configs.
5. **Review and Testing:** Run the application to ensure that no structural breakages occurred due to translated text.
