# Playwright CLI Quick Reference Guide

**Version:** 1.0 | **Updated:** 2026-03-12 | **For:** Claude Code Users

---

## Installation (3 Steps)

```bash
# 1. Install Playwright CLI
npm install -g @anthropic-ai/playwright-cli

# 2. Install browser engine
npx playwright install chromium

# 3. Install Claude Code skill
playwright-cli install --skills
```

Optional: Copy skill to `~/.claude/skills/` for global access across all projects.

---

## Token Comparison

| Approach | Tokens (Same Task) | Parallel Support | Headless Support |
|---|---|---|---|
| **Playwright CLI** | ~26,000 | Yes | Yes |
| **Playwright MCP Server** | ~114,000 | Yes | Yes |
| **Chrome Extension** | Highest | No | No |

**Bottom line:** The CLI uses ~90,000 fewer tokens than MCP for the same multi-page task. The gap widens with every additional page visited.

---

## How It Works

### The Accessibility Tree

Every web page has an **accessibility tree** — a structured map of interactive elements originally built for screen readers and assistive technology.

Playwright reads this tree and assigns each element a reference:

```
e1: input "Name" (text field)
e2: input "Email" (text field)
e3: select "Subject" (dropdown)
e4: textarea "Message" (text area)
e5: button "Submit" (submit button)
```

Claude Code uses these references to interact with the page. Instead of "click the blue button 340px from the top left," it's "click e5."

### CLI vs. MCP: What's Different

- **MCP Server:** Dumps the full accessibility tree into Claude Code's context window on every page load. Tokens stack up fast.
- **CLI:** Saves snapshots to disk (`/.playwright-cli/`). Only sends Claude Code a summary with element references. Disk storage is free — context window is not.

---

## Common Prompts

**Single test (headed):**
> "Use Playwright CLI in headed mode to go to localhost:3000, find the contact form, fill it out with realistic data, and submit. Screenshot each step."

**Parallel tests (headless):**
> "Run three Playwright CLI sessions in parallel against localhost:3000. Agent 1: happy path. Agent 2: empty fields. Agent 3: edge cases (long strings, emoji, script tags). Screenshot every step. Pass/fail report."

**Persistent session (login required):**
> "Use Playwright CLI in persistent headed mode. Go to [URL], log in with [credentials], then navigate to [page] and [action]."

**Screenshot capture:**
> "Use Playwright CLI to navigate to [URL] and take a full-page screenshot."

---

## Use Cases

- **UI Testing** — Form submissions, validation checks, regression testing
- **Web Scraping** — Extract structured data from websites without APIs
- **E-commerce Automation** — Add to cart, checkout flows, price monitoring
- **Screenshot Capture** — Documentation, visual regression, comparison
- **Persistent Sessions** — Login once, run headless from then on (cookies saved to disk)
- **Lead Generation** — Navigate platforms, extract contact info, fill forms

---

## Headed vs. Headless

| Mode | What It Does | When to Use |
|---|---|---|
| **Headless** (default) | Browser runs invisibly in background | Routine tests, CI/CD, parallel runs |
| **Headed** | Browser window visible on screen | Debugging, demos, first-time testing |

To get headed mode, you must explicitly say "headed" in your prompt. Otherwise Claude Code defaults to headless.

---

## Key Concepts

| Concept | Description |
|---|---|
| **Accessibility Tree** | Structured page map — same tech used by screen readers |
| **Element References** | e1, e2, e3... — how Claude identifies interactive elements |
| **Snapshots** | Saved to `.playwright-cli/` on disk, not in context window |
| **Parallel Agents** | Multiple browser instances running simultaneously |
| **Persistent Mode** | Saves session/cookies to disk for authenticated workflows |
| **Skills** | Package a Playwright workflow into a reusable one-command trigger |

---

## Supported Browsers

- Chromium (default, recommended)
- Firefox
- WebKit

Install additional engines: `npx playwright install firefox`
