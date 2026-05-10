# Orbos Skills layer: skill name / description fix

This note records a bug you could hit when **Orbos** auto-creates a skill (Skills layer “Grimoire,” or `/skill create`): the UI and install path showed **`generated-skill`** even though the draft scroll contained a real skill such as **`release-verification`**.

## Status

**Fixed upstream in Orbos** (`nottinghillai/orbos` on `main`). Pull the latest Orbos and use that build when you care about correct titles and folder slugs for auto-created skills.

## What went wrong

Some models return **more than one YAML frontmatter block**, or put **scratch workflow** before the final skill:

1. A **placeholder** header: `name: generated-skill` / `description: Generated Orbos skill.`
2. Long **analysis** (“Analyze the Request”, fenced examples, numbered planning steps).
3. The **actual** `SKILL.md`: `---` / real `name:` / real `description:` / workflow body.

Older behavior treated the file as valid as soon as it started with `---`, and used the **first** `name:` line for:

- The Grimoire line **Skill: …**
- The destination folder slug under `skills_library/<category>/…`

So the stored path looked like `engineering/generated-skill-24/` while the scroll further down said `release-verification`.

The harness was still useful—the workflow was there—but **metadata and routing looked broken**.

## What we changed (Orbos)

Implementation lives in the **Orbos** repo, not in Julia Reader.

1. **`src/spells/create_skill.py`**
   - **`_finalize_skill_body`** parses every `--- … ---` segment and keeps the **last substantive** frontmatter (skips placeholder `generated-skill` and the generic “Generated Orbos skill.” description when a better block exists).
   - Drops preamble between blocks so the saved `SKILL.md` is **one** header plus the real workflow.
   - **`_slug_from_skill_md`** prefers the **last non-placeholder** `name:` line when choosing the install slug.
   - **`write_stage_and_install_skill`** always runs `_finalize_skill_body` before writing `SKILL.md`, so pasted paths are normalized too.

2. **`src/enchantments/skills_mode/bridge.py`**
   - **`_skill_title_from_frontmatter`** sets the Grimoire **Skill:** title from the **last non-placeholder** `name:` in the scroll (matches what gets saved after canonicalization).

Together, new auto-created skills should show the **real** skill name in the Grimoire and land under a folder named from that slug (subject to uniqueness suffixes like `-2`, `-3`, etc.).

## What you should do locally

- Update Orbos from `main` and reinstall / run whatever entrypoint you use (e.g. `pip install -e .` in the Orbos tree).
- **Existing** `skills_library/.../generated-skill-*/SKILL.md` files are unchanged on disk; rename or regenerate if you want tidy paths.
- Prefer models that follow the skill prompt (“**only** SKILL.md, YAML + body, no fences”)—canonicalization helps but does not replace a clean reply.

## Related Julia Reader context

Julia Reader itself does not contain this logic. If you saw **Skill Grimoire awakens** while working in a Julia Reader checkout, that came from **Orbos** injecting a drafted skill into the session prefix.
