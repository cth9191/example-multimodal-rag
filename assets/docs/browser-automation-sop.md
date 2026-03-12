# Standard Operating Procedure: Browser Automation with Playwright CLI

**Document ID:** SOP-QA-2026-003
**Department:** Engineering / QA
**Effective Date:** March 2026
**Last Updated:** 2026-03-12
**Owner:** QA Lead
**Classification:** Internal

---

## 1. Purpose

This document establishes the standard process for running automated browser tests using Claude Code and the Playwright CLI. It applies to all UI testing, form validation, and regression testing across company web properties.

## 2. Scope

- All customer-facing web applications hosted on company infrastructure
- All form submission flows (contact, signup, checkout, booking)
- Pre-deployment validation testing
- Regression testing after frontend changes

## 3. Prerequisites

Before running browser automation tests, confirm the following are installed:

- [ ] **Node.js** (v18+)
- [ ] **Claude Code** (active subscription with API access)
- [ ] **Playwright CLI** — `npm install -g @anthropic-ai/playwright-cli`
- [ ] **Chromium browser engine** — `npx playwright install chromium`
- [ ] **Playwright CLI skill for Claude Code** — `playwright-cli install --skills`
- [ ] Target application running on localhost or accessible staging URL

## 4. How Playwright CLI Works

Playwright CLI uses the **accessibility tree** — a structured map of every interactive element on a page. Each element receives a reference (e1, e2, e3, etc.). Claude Code reads this tree as text and issues commands against those references.

**This is NOT screenshot-based.** The CLI does not take screenshots to "see" the page. It reads the same structured data that screen readers use, which is far more reliable and token-efficient.

**Token efficiency:** The CLI saves accessibility snapshots to disk and sends only a summary to Claude Code. The MCP server alternative dumps the full tree into the context window — roughly 90,000 more tokens for the same task.

## 5. Step-by-Step Process

### Step 1: Install Playwright CLI

```bash
npm install -g @anthropic-ai/playwright-cli
```

### Step 2: Install Browser Engine

```bash
npx playwright install chromium
```

### Step 3: Install Claude Code Skill

```bash
playwright-cli install --skills
```

The skill is stored in `.claude/skills/` and is available globally if copied to `~/.claude/skills/`.

### Step 4: Run a Single Headed Test

Use this for initial testing, debugging, or demos where you need to visually confirm behavior.

**Prompt Claude Code:**
> "Use the Playwright CLI in headed mode to go to [URL], find the [form name], fill it out with realistic test data, and submit it. Screenshot each step."

**What to expect:**
- A visible browser window opens
- Claude Code reads the accessibility tree and identifies form fields
- Text appears in fields as Claude fills them
- Form submits and Claude reports the result
- Snapshots are saved to `.playwright-cli/`

### Step 5: Run Parallel Headless Tests

Use this for comprehensive testing across multiple scenarios simultaneously.

**Prompt Claude Code:**
> "Run three Playwright CLI sessions in parallel against [URL]. Agent 1: fill out everything correctly with realistic data and submit (happy path). Agent 2: leave all fields empty and try to submit (validation). Agent 3: fill fields with edge case data — long strings, special characters, emoji, script tags (security). Screenshot every step. Give me a pass/fail report."

**What to expect:**
- Three headless browser sessions launch simultaneously
- Each agent runs its assigned test scenario independently
- A consolidated pass/fail report is returned

### Step 6: Review Results

- Check the pass/fail report for any failures
- Review screenshots saved during the test run
- Document any unexpected behavior
- File bug tickets for legitimate failures (see Section 8)

### Step 7: Create a Reusable Skill (Optional)

If this test will run repeatedly (e.g., after every deploy), package it into a skill:

1. Run `/skill-creator` in Claude Code
2. Describe the full workflow including test scenarios, URL, and report format
3. Test the skill with evals
4. Deploy — now run tests with a single command (e.g., "run the form tester")

## 6. Headed vs. Headless Decision Guide

| Scenario | Mode | Why |
|---|---|---|
| First time testing a new page | Headed | Visually confirm correct element targeting |
| Debugging a failed test | Headed | Watch what's happening in real time |
| Demo or screen recording | Headed | Audience needs to see the browser |
| Routine regression testing | Headless | Faster, less resource-intensive |
| CI/CD pipeline integration | Headless | No display available |
| Parallel multi-agent runs | Headless | Multiple windows are distracting and resource-heavy |

## 7. Authentication / Persistent Sessions

For pages behind login:

1. Run Playwright in **persistent mode** with headed browser
2. Log in manually (or have Claude do it)
3. Session cookies are saved to disk
4. All subsequent headless runs use the saved session — no re-login needed

This works for any site that uses cookie-based or session-based authentication.

## 8. Troubleshooting

| Issue | Likely Cause | Fix |
|---|---|---|
| "Browser not found" | Chromium not installed | Run `npx playwright install chromium` |
| Elements not detected | Page hasn't fully loaded | Add a wait/delay before interaction |
| Wrong element targeted | Ambiguous accessibility labels | Use more specific element references |
| High token usage | Using MCP instead of CLI | Confirm you're using the CLI skill, not MCP |
| Session expired | Persistent mode not enabled | Re-run in persistent headed mode to refresh session |
| Parallel tests interfering | Shared state between agents | Ensure each agent has its own browser instance (default behavior) |

## 9. Revision History

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-03-12 | 1.0 | Initial release | QA Lead |
