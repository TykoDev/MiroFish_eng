# Project Instructions and Rules

## Overview
This document contains the guidelines, rules, and coding conventions for all autonomous agents, contributors, and maintainers interacting with this codebase.

## 1. Core Rule: English-Only Codebase
- **Strictly English:** All human-readable text, code comments, variable names, docstrings, user interfaces, documentation, logging, and error messages MUST be written in standard English.
- **No Chinese Characters:** Any remaining Chinese characters in the codebase must be immediately refactored into their English equivalents.
- **Exception:** If an API payload key or third-party dependency strictly requires a Chinese string (e.g., legacy integration), this must be clearly documented in a code comment. Otherwise, all text is to be translated.

## 2. Translation Guidelines
- **Maintain Meaning:** Translate contextually, not literally. Ensure technical terms align with standard industry usage (e.g., "Agent" instead of "Representative", "Swarm Intelligence" instead of "Group Wisdom").
- **UI Text:** Ensure Vue templates and HTML texts are grammatically correct and concise for user display.
- **Logging & Errors:** Translate all `logger.info`, `logger.error`, `print()`, and `console.log()` statements clearly to help with debugging. Keep formatting string placeholders (`%s`, `{}`) intact.

## 3. Coding Conventions
- **Python (Backend):**
  - Follow PEP 8 guidelines for naming conventions and formatting.
  - Use clear type hints where applicable.
  - Ensure docstrings follow a consistent format (e.g., Google or Sphinx) in English.
- **JavaScript/Vue (Frontend):**
  - Follow standard ESLint recommended rules or Vue style guides.
  - Component names should be PascalCase.
  - Method and variable names should be camelCase.

## 4. Refactoring Instructions
- **Safety First:** Do not break logic or data structures. When translating keys in JSON or dicts, ensure the counterpart in the frontend/backend is updated simultaneously. If a value is used for logic branching (e.g., `if status == '完成':`), update the logic appropriately to its English equivalent (`if status == 'Completed':`).
- **Tracking:** Use `STATUS.md` to track refactoring progress. Mark files as complete `[x]` only when thoroughly verified.
- **Testing:** Always run the application (e.g., using `docker-compose up --build` or by starting the backend/frontend servers independently) to ensure the translation hasn't caused errors or UI breakages.

## 5. Pre-commit Checks
- Before submitting code, ensure that:
  - No new non-English text has been introduced.
  - All translated files have been tested for syntax and runtime errors.
  - `STATUS.md` is accurately updated reflecting completed work.
