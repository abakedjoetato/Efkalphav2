# SYSTEM BUILD PROMPT — From Zip Archive (Claude Opus Engineering Protocol)

## OBJECTIVE
Begin a structured, rule-compliant reconstruction of a Discord bot from a zipped project archive.  
Your task is to initialize the workspace, understand the system holistically, and execute a multi-phase rebuild while minimizing checkpoint charges and supporting resumable progress.

---

## PHASE 0: PROJECT EXTRACTION AND WORKSPACE INIT

### Step 1: Unzip Attached Archive
- Unzip the uploaded archive (usually named `StillBroken.zip` or equivalent) into a temporary staging directory (e.g., `/unzipped_project/`).

### Step 2: Move Files to Main Workspace
- Recursively move all files and folders from `/unzipped_project/` into the root project directory (`/home/runner/`, `/workspace/`, or equivalent).

### Step 3: Initialize Context
- Scan all files and directories to understand the full system architecture.
- Identify the following:
  - Entry point (e.g., `main.py`, `bot.py`, or `app.py`)
  - Command cogs and routing structure
  - MongoDB models
  - Premium logic modules
  - Utilities, config loaders, and compatibility layers

### Step 4: Resume Support
- Store a structured summary of project state in memory:
  - Which cogs exist
  - Which files are loaded
  - Which phases have been completed
  - Which errors are pending
- You must be able to resume from any failed phase without repeating prior work unless necessary.

---

## ENGINEERING RULESET (from rules.md)

You must follow all constraints:
- [ ] No monkey patches or quick fixes (Rule 6)
- [ ] No command behavior changes (Rule 3)
- [ ] Do not add or remove features (Rule 10)
- [ ] Always reuse existing code before creating new (Rule 4)
- [ ] Use compatibility layers where applicable
- [ ] Preserve async and multi-guild safety (Rule 8)

If a fix or build step would violate these, STOP and return:
`CONSTRAINT ESCALATION REQUIRED`

---

## PHASED BUILD STEPS

### PHASE 1: FOUNDATION BOOTSTRAP
- Clean initialization of the command parser, cog loader, and bot entrypoint.
- Validate the directory layout and config/environment structure.

### PHASE 2: DATABASE & MODELS
- Identify all MongoDB models and validate schema structure
- Ensure each model is used safely (async, BSON-safe, correct query handling)

### PHASE 3: PREMIUM LAYER
- Implement guild-only premium logic checks
- Inject checks into feature cogs without code duplication

### PHASE 4: COG REACTIVATION
- Load all cogs, resolve import errors, fix unresolved routes
- Do not modify command logic unless necessary to restore compatibility

### PHASE 5: SYSTEM INTEGRATION
- Validate all cog-to-model and feature interconnections
- Verify shared utilities (cooldowns, shared state, config parsing)

### PHASE 6: STARTUP & LIVE SIMULATION
- Simulate bot startup
- Ensure no cog failures, missing handlers, or runtime errors remain

---

## CHECKPOINT STRATEGY

- Each phase should generate **one** AI checkpoint at most
- Avoid unnecessary recomputes by caching prior analysis
- Bundle related file edits into single response blocks
- Do not trigger a checkpoint for diagnostics, dry-runs, or summaries

---

## VALIDATION GOAL

- Bot starts and loads all cogs without error
- Commands behave as originally intended
- Database ops succeed (no silent fails)
- Premium access is enforced per guild
- No unstructured fixes or architectural violations exist

---

## RESUME/RECOVERY INSTRUCTION

If process is interrupted, next run should:
- Detect `/unzipped_project/` state
- Verify which phases completed
- Resume from the next incomplete phase using stored context

If that is not possible, regenerate `PHASE 0` summary before continuing.

If any phase cannot proceed due to a rule violation, return:
`CONSTRAINT ESCALATION REQUIRED — BUILD HALTED`

==== END OF SYSTEM PROMPT ====
