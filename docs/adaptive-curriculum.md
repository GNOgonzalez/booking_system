# Adaptive Curriculum

## Goal (original draft)

- Find the optimal skill path for English language learning from A1 level to C2.
  - Draw on trusted language frameworks (the app uses **CEFR**, the standard behind Cambridge levels).
  - Break the path into modular, digestible lessons covering one subject each.
- Create an integrated system that admin can opt into after connecting a chosen LLM.
  - The system reads a student's reports for language that outlines strengths and weaknesses.
  - It also reads metrics such as Grammar/Vocab, Speaking/Listening, Writing, and Reading (the default language metrics).
  - It then suggests supplementary material to bolster weak points, or the next logical skill to keep momentum.
  - This happens lesson by lesson and also feeds periodic reporting.

## Decisions

| Question | Choice | Why |
|----------|--------|-----|
| Framework | CEFR A1–C2 | Common Core is US K–12 literacy; CEFR is what language studios mean by A1–C2. |
| Source material | Curated seed file in the repo | No runtime scraping — predictable deploys, no copyright or API fragility. |
| Automation | Teacher approves every suggestion | Nothing changes a student's path silently. |
| AI | Optional, staff opt-in | Rule-based suggestions always work; the LLM adds nuance from teacher notes. |
| Remedial material | Attached to the student | Studio templates stay shared and untouched. |

## How it works

```text
Teacher saves a session report (scores + class notes)
        │
        ▼
Teacher clicks "Suggest next step" on the Curriculum page
        │
        ▼
student_learning_signals ──► rule_based_suggestions ──┐
        │                                              ├──► pending CurriculumSuggestion rows
        └──► suggest_curriculum_steps (LLM, optional) ─┘
                                                       │
                                  Teacher: Accept ─────┼──► apply_suggestion
                                  Teacher: Dismiss ────┘    (complete module / add extra practice)
```

### Data

| Model | Purpose |
|-------|---------|
| `CurriculumTrack.framework` / `subject` / `cefr_band` | Marks the CEFR path (`framework='cefr'`). |
| `CurriculumModule.cefr_level` / `skill_keys` | Level (A1…C2) and which score metrics the module trains. |
| `CurriculumSuggestion` | A proposal: `kind` (next_module / supplementary / review), `status` (pending / accepted / dismissed), `source` (rules / llm), rationale, target module, audit fields. |
| `StudentSupplementaryMaterial` | Extra practice for one student, created when a supplementary or review suggestion is accepted. |
| `StudioLLMConfig.adaptive_curriculum_enabled` | Staff switch for the AI layer (default off). |

### Score-key mapping

Module `skill_keys` must match `ScoreDimension.key` values so the rules can connect a weak score to a module.
The default language metrics are:

| Metric key | Covers |
|------------|--------|
| `grammar` | Grammar and vocabulary |
| `reading` | Reading |
| `writing` | Writing |
| `speaking` | Speaking and listening |

If staff add custom metrics for a subject, tag modules with those keys too; otherwise the rules can still suggest
the next module but cannot match weak areas.

### Rules (always on)

In `scheduling/services/adaptive_curriculum.py`:

1. Average each metric over the student's reports in the last 90 days (up to 20 reports).
2. A metric is **weak** when its average is below 60% of the metric's max.
3. For up to two weak metrics:
   - suggest **supplementary** practice from the first pending module tagged with that metric, or
   - if none are pending, suggest a **review** of the most recent completed module with that tag.
4. If the current module's skills are not weak, suggest **next_module**: mark it done and move on.
5. No duplicates: a pending suggestion with the same kind and module is never created twice.

### Accepting and dismissing

- **next_module** marks the target module completed; the next pending module becomes current.
- **supplementary / review** creates a `StudentSupplementaryMaterial` (the suggestion's content, or the module's
  content if blank). Students see it under "Extra practice from your teacher".
- **Dismiss** only changes the suggestion's status.

### AI layer (optional)

The AI runs only when all of these are true:

- studio AI is enabled and configured (Staff → AI settings);
- "Adaptive curriculum suggestions" is switched on;
- the teacher has the `use_ai` permission (staff always may).

The prompt includes score averages, the last three note excerpts, the current module, the next five pending modules,
and the last three completed ones. The model must reply with JSON; any suggestion that points at a module it was not
shown is dropped. AI suggestions win when they target the same kind and module as a rule suggestion. If the call
fails, rule suggestions are still saved and the teacher sees why the AI was skipped.

The AI never runs on report save — only when a teacher clicks "Suggest next step" — so there are no cost surprises.

### Periodic summary

`GET …/curriculum/students/<id>/summary/?days=7|30|90` returns modules finished in the window, report count, metric
averages, weak areas, suggestion activity, and an **estimated CEFR band**. The band is the level of the current
module, or of the last completed module when the track is finished. It reflects position on the path, not a formal
assessment.

## Seeding the CEFR path

```bash
python manage.py seed_cefr_curriculum            # create once (safe to re-run)
python manage.py seed_cefr_curriculum --refresh  # rewrite modules from the JSON
```

- Source: `scheduling/data/cefr_english_path.json` — 48 modules, 8 per level, each tagged with a level and skills.
- Creates the template track "English — CEFR path (A1 to C2)".
- `--refresh` rewrites the modules, which **resets progress for every student on that track**.
- `bootstrap_sandbox --demo` seeds it and enrolls `demo_student_2` if they have no active curriculum.

To add another language, write a JSON file in the same shape and a matching seed call; the schema already supports it.

## API

Teacher paths (staff mirrors live under `/api/staff/teachers/<teacher_id>/curriculum/…`):

| Method | Path | Needs |
|--------|------|-------|
| GET | `/api/teacher/curriculum/students/<id>/suggestions/` | student on roster |
| POST | `/api/teacher/curriculum/students/<id>/suggest/` | + `manage_curriculum` |
| POST | `/api/teacher/curriculum/suggestions/<id>/accept/` | + `manage_curriculum` |
| POST | `/api/teacher/curriculum/suggestions/<id>/dismiss/` | + `manage_curriculum` |
| GET | `/api/teacher/curriculum/students/<id>/summary/?days=30` | student on roster |
| GET | `/api/curriculum/me/supplementary/` | student |

## Deferred

| Item | Why |
|------|-----|
| Strict unlock gating | Conflicts with 1:1 flexibility; "current" stays a hint. |
| Auto-advance without a teacher | Approval-only by design. |
| Auto-suggest after every report save | Possible later behind its own staff flag. |
| Homework auto-assigned per module | Follow-up: link `HomeworkAssignment` to `CurriculumModule`. |
| More CEFR languages | Seed English first; same schema. |
