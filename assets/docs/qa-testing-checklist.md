# QA Testing Checklist: Playwright CLI Browser Tests

**Document ID:** QA-CHK-2026-007
**Applies To:** All web form submissions
**Last Updated:** 2026-03-12
**Owner:** QA Team

---

## Pre-Test Setup

- [ ] Playwright CLI installed (`npm install -g @anthropic-ai/playwright-cli`)
- [ ] Chromium browser engine installed (`npx playwright install chromium`)
- [ ] Playwright CLI skill installed (`playwright-cli install --skills`)
- [ ] Target site running and accessible (localhost or staging URL)
- [ ] Claude Code open and ready
- [ ] Test scenarios documented (see below)

---

## Test Scenarios

### Scenario 1: Happy Path (Valid Submission)

**Objective:** Confirm the form works correctly with realistic, valid data.

- [ ] Navigate to form page
- [ ] Fill **all** required fields with realistic data:
  - Name: Full name (e.g., "Sarah Mitchell")
  - Email: Valid format (e.g., "sarah.mitchell@company.com")
  - Phone: Valid format (e.g., "555-0142")
  - Message/Comments: 2-3 sentences of realistic text
  - Dropdowns/selects: Choose a valid option
  - Checkboxes/radios: Select appropriate values
- [ ] Submit the form
- [ ] **Verify:** Success message or confirmation page appears
- [ ] **Verify:** No console errors
- [ ] **Verify:** Data appears in backend/database (if accessible)
- [ ] Screenshot captured at each step

**Expected Result:** Form submits successfully. User sees confirmation.

---

### Scenario 2: Validation Testing (Empty/Invalid Submission)

**Objective:** Confirm the form correctly rejects incomplete or invalid input.

- [ ] Navigate to form page
- [ ] Leave **all** fields empty
- [ ] Click submit
- [ ] **Verify:** Form does NOT submit
- [ ] **Verify:** Error messages appear for each required field
- [ ] **Verify:** Error messages are clear and specific (not generic "error")
- [ ] Test individual field validation:
  - [ ] Email field with invalid format (e.g., "notanemail")
  - [ ] Phone field with letters (e.g., "abcdefg")
  - [ ] Required field left blank while others are filled
- [ ] **Verify:** Inline validation triggers (if applicable)
- [ ] Screenshot captured at each step

**Expected Result:** Form rejects submission. Clear error messages displayed for each invalid/missing field.

---

### Scenario 3: Edge Cases / Security Testing

**Objective:** Confirm the form handles unusual or malicious input without breaking.

- [ ] Navigate to form page
- [ ] Test the following inputs across all text fields:

| Input Type | Test Value | What to Check |
|---|---|---|
| Long string | 500+ characters | Field truncates or handles gracefully |
| Special characters | `!@#$%^&*()_+-=[]{}` | No errors, characters escaped properly |
| Emoji | `Testing form 🚀🔥💯` | Accepted or gracefully rejected |
| Script injection | `<script>alert('xss')</script>` | Script does NOT execute, input sanitized |
| SQL injection | `'; DROP TABLE users; --` | No database errors, input sanitized |
| HTML injection | `<b>bold</b><img src=x onerror=alert(1)>` | Tags stripped or escaped |
| Unicode | `Ñoño Müller François` | Accepted and displayed correctly |
| Leading/trailing spaces | `   test   ` | Trimmed or handled appropriately |
| Empty spaces only | `      ` | Treated as empty / validation triggers |

- [ ] Submit with each input type
- [ ] **Verify:** Page does not crash or show unhandled errors
- [ ] **Verify:** No JavaScript alerts or XSS execution
- [ ] **Verify:** Backend does not return 500 errors
- [ ] Screenshot captured at each step

**Expected Result:** Form handles all edge cases gracefully. No crashes, no XSS, no unhandled errors.

---

## Post-Test Review

- [ ] Collect pass/fail report from Claude Code
- [ ] Review all screenshots for visual anomalies
- [ ] Document any failures:
  - Which scenario failed
  - What the expected vs. actual behavior was
  - Screenshot of the failure
- [ ] File bug tickets for legitimate failures with:
  - Steps to reproduce
  - Expected behavior
  - Actual behavior
  - Screenshots
  - Browser/environment info
- [ ] Re-test after fixes are deployed

---

## Headed vs. Headless Decision Matrix

| Question | If Yes → | If No → |
|---|---|---|
| First time testing this form? | Headed | Headless |
| Debugging a known failure? | Headed | Headless |
| Recording a demo? | Headed | Headless |
| Running as part of CI/CD? | Headless | Headless |
| Running 3+ parallel agents? | Headless | Either |

---

## Quick Reference: Parallel Test Command

**Prompt template for Claude Code:**

> "Run three Playwright CLI sessions in parallel against [URL]. Agent 1: happy path — fill all fields with realistic data and submit. Agent 2: validation — leave all fields empty and submit. Agent 3: edge cases — fill fields with long strings, special characters, emoji, and script tags. Screenshot every step. Give me a consolidated pass/fail report."

---

**Sign-off:**

| Role | Name | Date | Signature |
|---|---|---|---|
| QA Tester | | | |
| Dev Lead | | | |
| Project Manager | | | |
