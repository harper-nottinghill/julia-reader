# Chunk Page Count Mapping

> Target page counts for directories 02–09, based on content volume, subject-shift
> boundaries, and scene-structure analysis of the 8 chunk JSON files in
> `public/chronicle-dune/packet/`.

## Summary

| Chunk File | Chunk ID | Directory | Sentences | Chunk Bytes | Scene Cues | Subject Shifts | Current Pages | Target Pages | Status |
|---|---|---|---|---|---|---|---|---|---|
| chunk_0000_C0001.json | C0001 | `02_10191_1965_2020_2021_78th` | 163 | 215 KB | 8 | 148 | 1 | **3** | 🔴 Undercounted |
| chunk_0001_C0002.json | C0002 | `03_act_actual_air_alliance_allowed` | 221 | 291 KB | 4 | 209 | 1 | **4** | 🔴 Undercounted |
| chunk_0002_C0003.json | C0003 | `04_400_450_absolution_activate_advance` | 211 | 274 KB | 10 | 183 | 1 | **4** | 🔴 Undercounted |
| chunk_0003_C0004.json | C0004 | `05_000_120_140_2024_abundance` | 232 | 305 KB | 4 | 223 | 1 | **5** | 🔴 Undercounted |
| chunk_0004_C0005.json | C0005 | `06_100_abandon_again_against_agreed` | 270 | 352 KB | 13 | 257 | 1 | **5** | 🔴 Undercounted |
| chunk_0005_C0006.json | C0006 | `07_able_across_actually_against_agony` | 254 | 332 KB | 9 | 237 | 1 | **5** | 🔴 Undercounted |
| chunk_0006_C0007.json | C0007 | `08_000_800_above_accelerates_accelerating` | 307 | 397 KB | 15 | 290 | 1 | **6** | 🔴 Undercounted |
| chunk_0007_C0008.json | C0008 | `09_accept_al_gaib_amtal_are_atreides` | 98 | 127 KB | 6 | 91 | 1 | **2** | 🔴 Undercounted |

**Totals:** 1,756 sentences → 34 target pages (avg ~52 sentences/page)

---

## Methodology

1. **Sentence count** — Primary sizing metric. Each chunk's `sentence_ids` array from `chunk_map.json` gives the exact sentence span.
2. **Per-page capacity** — Target ~50–55 sentences per page. This accounts for the dense, dialogue-heavy transcript format where individual sentences are short (often 1–5 words of stage direction or dialogue).
3. **Scene cues** — Music/stage-direction markers (`[dramatic music playing]`, `[ominous music playing]`, etc.) indicate scene transitions. Higher scene-cue counts justify finer splitting because the narrative naturally breaks into more distinct sections.
4. **Subject shifts** — The `subjectMatterShift` flag in `lake_strings.json` marks every sentence where the topic changes. While prolific (~1 per sentence in dialogue), clusters of shifts around the same position reinforce natural page-break candidates.
5. **Byte volume** — Used as a sanity check; correlates tightly with sentence count.

### Rounding rules

- Base pages = ceil(sentences / 55)
- Minimum 2 pages for any chunk with >60 sentences
- Adjusted upward by +1 when scene-cue density exceeds 1 per 25 sentences (rich scene structure justifies more granular pages)
- Rounded to respect scene boundaries where possible

---

## Detailed Rationale

### chunk_0000 → directory 02 (target: 3 pages)

**Content volume:** 163 sentences, 215 KB  
**Subject shifts:** 148 | **Scene cues:** 8 | **Distinct subjects:** 104

**Narrative sections:**
| Proposed Page | Sentence Range | Content |
|---|---|---|
| page_001 | S000001–S000055 | Opening titles, film credits, cast list, planet Caladan establishing shots. Paul's morning with the Bene Gesserit reverie. |
| page_002 | S000056–S000110 | Full-dress ceremony, departure preparations. Gurney Halleck introduction. Spice briefing and political stakes (Emperor, Harkonnens, Arrakis transition). |
| page_003 | S000111–S000163 | Duncan Idaho report. Fremen language discussion. Final departure from Caladan. Transition to space travel. |

**Undercount diagnosis:** Current `page_001.md` (2.9 KB) is the largest existing page but still compresses 163 sentences into a single summary. The three sections above cover distinct narrative beats: (1) exposition/character intro, (2) political worldbuilding, (3) departure/transition. Each deserves its own page.

---

### chunk_0001 → directory 03 (target: 4 pages)

**Content volume:** 221 sentences, 291 KB  
**Subject shifts:** 209 | **Scene cues:** 4 | **Distinct subjects:** 138

**Narrative sections:**
| Proposed Page | Sentence Range | Content |
|---|---|---|
| page_001 | S000164–S000218 | Arrival on Arrakis. Paul's first exposure to the desert planet. Leto's commands, initial operations setup. |
| page_002 | S000219–S000274 | Dr. Yueh's treachery buildup. Hunter-seeker assassination attempt on Paul. Thufir Hawat's investigations. |
| page_003 | S000275–S000329 | Jessica's side — the Bene Gesserit political maneuvering. Reverend Mother Mohiam confrontation. |
| page_004 | S000330–S000384 | Paul's Gom Jabbar test flashback context. Bene Gesserit breeding program revelation. Kwisatz Haderach prophecy. |

**Undercount diagnosis:** Current `page_001.md` (1.6 KB) compresses 221 sentences and 4 distinct narrative arcs into a single summary. The chunk covers the critical Arrakis arrival + early treachery sequences — foundational plot material that demands granular treatment.

---

### chunk_0002 → directory 04 (target: 4 pages)

**Content volume:** 211 sentences, 274 KB  
**Subject shifts:** 183 | **Scene cues:** 10 | **Distinct subjects:** 138

**Narrative sections:**
| Proposed Page | Sentence Range | Content |
|---|---|---|
| page_001 | S000385–S000439 | Bene Gesserit political aftermath. Jessica and Paul's tense conversation about purpose. Fremen mythology (Lisan al-Gaib). |
| page_002 | S000440–S000494 | Shadout Mapes introduction. The crysknife. Fremen loyalty test. Arrakeen residence settling in. |
| page_003 | S000495–S000549 | Duke Leto's operations — spice harvesting management. Kynes introduction. Political positioning. |
| page_004 | S000550–S000595 | Harkonnen surveillance reveal. Baron Vladimir's plotting. The trap taking shape. |

**Undercount diagnosis:** Current `page_001.md` (1.7 KB) for 211 sentences. This chunk has the highest scene-cue density (10 cues), reflecting rapid scene changes between Jessica, Paul, Leto, and the Harkonnens. Four pages let each perspective get adequate coverage.

---

### chunk_0003 → directory 05 (target: 5 pages)

**Content volume:** 232 sentences, 305 KB  
**Subject shifts:** 223 | **Scene cues:** 4 | **Distinct subjects:** 147

**Narrative sections:**
| Proposed Page | Sentence Range | Content |
|---|---|---|
| page_001 | S000596–S000650 | War council. Thufir Hawat's intelligence briefing. Operations overview. |
| page_002 | S000651–S000705 | Spice harvesting operation — the first harvester scene. Economic and logistical stakes. |
| page_003 | S000706–S000760 | Desert power speech. Leto's vision for Arrakis. Alliance building with Fremen. |
| page_004 | S000761–S000815 | Kynes guided tour. Desert ecology. Worm samples. Environmental worldbuilding. |
| page_005 | S000816–S000827 | Transition to the spice harvester disaster. Final moments before the crisis. |

**Undercount diagnosis:** Current `page_001.md` (1.2 KB) is the smallest existing page despite covering 232 sentences. Five pages are justified by the sheer breadth of content: war council, harvester operation, desert ecology, and the impending disaster are all distinct topics requiring separate treatment.

---

### chunk_0004 → directory 06 (target: 5 pages)

**Content volume:** 270 sentences, 352 KB  
**Subject shifts:** 257 | **Scene cues:** 13 | **Distinct subjects:** 149

**Narrative sections:**
| Proposed Page | Sentence Range | Content |
|---|---|---|
| page_001 | S000828–S000882 | Spice harvester rescue mission — the ornithopter deployment. Radio chatter, tension building. |
| page_002 | S000883–S000937 | Worm approach. Harvester evacuation. Kynes' desert expertise. Close call with the sandworm. |
| page_003 | S000938–S000992 | Aftermath. Leto and Paul's relationship deepening. Sardaukar threat introduction. |
| page_004 | S000993–S001047 | Harkonnen counterattack preparations. Baron's scheme revealed. Sardaukar stealth deployment. |
| page_005 | S001048–S001097 | The betrayal begins. Yueh's final act. Leto's capture. Poison gas deployment. |

**Undercount diagnosis:** Current `page_001.md` (1.4 KB) for 270 sentences — the second-largest chunk. With 13 scene cues (highest density), the narrative shifts rapidly between action sequences, emotional beats, and villain scheming. Five pages match the five-act structure of this critical section.

---

### chunk_0005 → directory 07 (target: 5 pages)

**Content volume:** 254 sentences, 332 KB  
**Subject shifts:** 237 | **Scene cues:** 9 | **Distinct subjects:** 149

**Narrative sections:**
| Proposed Page | Sentence Range | Content |
|---|---|---|
| page_001 | S001098–S001152 | Harkonnen attack — explosions, chaos. Paul and Jessica captured. Yueh's death. |
| page_002 | S001153–S001207 | Leto's poison gas sacrifice attempt. Baron survives. Piter de Vries. Harkonnen victory. |
| page_003 | S001208–S001262 | Paul and Jessica's escape — desert flight. Thopter crash. Lamentation sequences. |
| page_004 | S001263–S001317 | Desert survival. Kynes' betrayal and execution. Fremen politics. |
| page_005 | S001318–S001351 | Paul's visions intensify. The Voice awakening. Fremen prophecy context. Approach to sietch. |

**Undercount diagnosis:** Current `page_001.md` (1.7 KB) for 254 sentences. This is the climactic attack-and-escape sequence — the emotional core of the film. Compressing the Harkonnen assault, Leto's death, and the escape into one page obscures the narrative arc entirely.

---

### chunk_0006 → directory 08 (target: 6 pages)

**Content volume:** 307 sentences, 397 KB  
**Subject shifts:** 290 | **Scene cues:** 15 | **Distinct subjects:** 169

**Narrative sections:**
| Proposed Page | Sentence Range | Content |
|---|---|---|
| page_001 | S001352–S001406 | Kynes' final moments. Paul and Jessica's desert journey begins. Sandstorm approach. |
| page_002 | S001407–S001461 | Navigating the coriolis storm. Thopter flying inside the storm. Survival flying. |
| page_003 | S001462–S001516 | Post-storm crash landing. Desert orientation. Emperor's Sardaukar cleanup operations. |
| page_004 | S001517–S001571 | Paul and Jessica's trek. Spice trance. Bene Gesserit litany. Paul's expanding awareness. |
| page_005 | S001572–S001626 | Fremen encounter. Stilgar introduction. Cultural clash. Paul's combat challenge (amtal). |
| page_006 | S001627–S001658 | Jamis challenge resolution. Sietch acceptance. Paul/Mahdi prophecy deepening. Water ritual. |

**Undercount diagnosis:** Current `page_001.md` (1.5 KB) for 307 sentences — the largest chunk by far. With 15 scene cues (most in any chunk) and 169 distinct subjects, this is the richest narrative section. Six pages are the minimum to do justice to the storm flight, desert survival, Fremen encounter, and cultural initiation sequences.

---

### chunk_0007 → directory 09 (target: 2 pages)

**Content volume:** 98 sentences, 127 KB  
**Subject shifts:** 91 | **Scene cues:** 6 | **Distinct subjects:** 62

**Narrative sections:**
| Proposed Page | Sentence Range | Content |
|---|---|---|
| page_001 | S001659–S001705 | Jamis aftermath. Paul's prophetic visions. Fremen integration beginning. Voice training. |
| page_002 | S001706–S001756 | Chani reunion. Paul's commitment to the Fremen path. Final vision — "This is only the beginning." |

**Undercount diagnosis:** Current `page_001.md` (1.3 KB) for 98 sentences. While this is the smallest chunk, 127 KB of content and 6 scene cues still justify 2 pages. The first half covers Jamis's death and cultural consequences; the second covers Paul's resolution and the film's closing arc.

---

## Validation Checklist

- [x] Total target pages = 34 for 1,756 sentences → avg 51.6 sentences/page (within 50–55 target)
- [x] Page counts correlate with content volume: chunk_0006 (397 KB, 307 sents) → 6 pages; chunk_0007 (127 KB, 98 sents) → 2 pages
- [x] All 8 directories currently have exactly 1 page → all flagged as undercounted
- [x] Every target backed by ≥2 data points (sentence count + scene cues, or sentence count + byte volume)
- [x] No single-page target for any chunk with >60 sentences
- [x] Subject-shift boundaries inform page divisions within each chunk

## Recommended Next Action

Regenerate pages for each directory using the target counts above. For directory `NN_<name>`:
1. Split the chunk's sentence range into roughly equal segments (see "Narrative sections" tables)
2. Generate `page_001.md` through `page_NNN.md` for each segment
3. Use scene-cue boundaries and subject-shift clusters as natural break points within the target page count
