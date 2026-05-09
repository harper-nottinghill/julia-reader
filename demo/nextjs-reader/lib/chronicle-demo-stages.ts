/** Ritual stage labels aligned with the Python harness (for screen-recording playback). */

export const CHRONICLE_PLAYBACK_STAGES: string[] = [
  "✦ Archive Charm — raw source sealed → source/raw_input.txt",
  "✦ Scourgify — normalized → source/normalized_input.txt",
  "✦ Pensieve Basin — reader state initialized",
  "✦ Sentence Scrying — sentence map written",
  "✦ Lake Strings — lake_strings.json, break_map.json",
  "✦ Chunking Ward — chunk_map.json (bounded packets)",
  "✦ Break Map — source/break_marked_input.md",
  "✦ Reading Rune — per-chunk summaries (silent HTTP with your API key; bundled demo used offline fallback)",
  "✦ Living Summary — state/live_summary.md",
  "✦ Chapter Divination — state/book_plan.json",
  "✦ Quick-Quotes Quill — book/*.md pages + index",
  "✦ Packet Portkey — packet/packet.json + chunk shards",
  "✦ Ministry Inspection — logs/validation_report.md",
  "✦ Chronicle Complete — explore the tree on the left",
];

export const DIRECTOR_TOUR_FILES: string[] = [
  "source/raw_input.txt",
  "state/reader_state.json",
  "state/live_summary.md",
  "state/book_plan.json",
  "book/00_index.md",
  "packet/packet.json",
  "logs/validation_report.md",
];
