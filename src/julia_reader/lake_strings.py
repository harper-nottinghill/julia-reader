"""Harper Reader-style Lake Strings, breaks, and packets.

This ports the useful data model from the Harper Reader reference into the
Julia Reader Chronicle pipeline without coupling to Electron.
"""

from __future__ import annotations

import datetime as _dt
import re
import uuid
from typing import Any

from .subject_shift import keywords, speaker_label, subject_shift_reason

_POSITIVE = {"good", "great", "love", "success", "clear", "strong", "happy", "works", "useful"}
_NEGATIVE = {"bad", "broken", "fail", "failed", "error", "risk", "problem", "sad", "angry", "wrong"}


def _stable_id(prefix: str, seed: str) -> str:
    return f"{prefix}_{uuid.uuid5(uuid.NAMESPACE_URL, seed).hex[:12]}"


def _tense(text: str) -> str:
    low = text.lower()
    if re.search(r"\b(will|going to|shall|next|future)\b", low):
        return "future"
    if re.search(r"\b(was|were|had|did|went|made|built|created|finished)\b", low):
        return "past"
    return "present"


def _perspective(text: str) -> str:
    low = text.lower()
    if re.search(r"\b(i|we|me|my|our|us)\b", low):
        return "first"
    if re.search(r"\b(you|your|yours)\b", low):
        return "second"
    return "third"


def _statement_type(text: str) -> str:
    stripped = text.strip()
    if stripped.endswith("?"):
        return "question"
    if stripped.endswith("!"):
        return "exclamation"
    if re.match(r"^(do|make|run|create|fix|add|remove|open|read)\b", stripped, re.I):
        return "command"
    return "statement"


def _sentiment(text: str) -> tuple[str, float]:
    words = {w.lower() for w in re.findall(r"[a-z][a-z-]{2,}", text)}
    pos = len(words & _POSITIVE)
    neg = len(words & _NEGATIVE)
    score = 0.0
    if pos or neg:
        score = max(-1.0, min(1.0, (pos - neg) / max(1, pos + neg)))
    if score > 0.2:
        return "positive", score
    if score < -0.2:
        return "negative", score
    return "neutral", score


def _intent_type(text: str) -> str:
    st = _statement_type(text)
    low = text.lower()
    if st == "question":
        return "inquisitive"
    if st == "command" or re.search(r"\b(should|must|need to|todo|action)\b", low):
        return "directive"
    if re.search(r"\b(feel|felt|love|hate|worried|excited)\b", low):
        return "emotional"
    return "informative"


def build_lake_strings(sentences: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Create Lake String records and soft/hard break records from sentence maps."""
    lake_strings: list[dict[str, Any]] = []
    breaks: list[dict[str, Any]] = []
    previous_subject = None

    for idx, sent in enumerate(sentences):
        text = str(sent.get("text", ""))
        tags = sorted(keywords(text))[:8]
        subject = tags[0] if tags else (speaker_label(text) or "general")
        sentiment, score = _sentiment(text)
        lake_id = _stable_id("LS", f"{idx}:{text}")
        previous = lake_strings[-1] if lake_strings else None
        prev_tags = set(previous.get("tags", [])) if previous else set()
        cur_tags = set(tags)
        related: bool | str | None = None
        strength: str | None = None
        connected: list[str] = []
        shift = False
        new_subject = None

        if previous is None:
            related = None
            strength = None
        else:
            overlap = len(prev_tags & cur_tags) / max(1, len(prev_tags | cur_tags))
            explicit_reason = subject_shift_reason(sent, [sentences[idx - 1]])
            if explicit_reason or overlap < 0.08:
                related = False
                strength = "none"
                shift = True
                new_subject = subject
            elif overlap < 0.2:
                related = "loosely"
                strength = "loose"
                shift = True
                new_subject = subject
                connected = [previous["id"]]
            else:
                related = True
                strength = "strong"
                connected = [previous["id"]]

        understanding = (
            f"This sentence {'introduces' if shift else 'continues'} the thread around "
            f"{new_subject or subject}, with {sentiment} tone."
        )
        lake = {
            "id": lake_id,
            "sentence_id": sent["sentence_id"],
            "index": idx,
            "timestamp": _dt.datetime.now().isoformat(),
            "originalSentence": text,
            "characterCount": len(text),
            "tags": tags,
            "abstractTags": [_statement_type(text), _intent_type(text)],
            "tense": _tense(text),
            "perspective": _perspective(text),
            "subject": subject,
            "sentiment": sentiment,
            "sentimentScore": score,
            "statementType": _statement_type(text),
            "intentType": _intent_type(text),
            "isRelatedToPrevious": related,
            "relationshipStrength": strength,
            "previousSentenceId": previous["id"] if previous else None,
            "connectedSentenceIds": connected,
            "subjectMatterShift": shift,
            "newSubjectMatter": new_subject,
            "storyArcPosition": "beginning" if idx == 0 else "transition" if shift else "middle",
            "narrativeRole": "setup" if idx == 0 else "transition" if shift else "development",
            "understanding": understanding,
        }
        lake_strings.append(lake)
        sent["lake_string_id"] = lake_id
        sent["subject_tags"] = tags
        sent["importance_score"] = min(1.0, 0.2 + (0.15 if shift else 0) + min(0.5, len(tags) * 0.05))
        sent["subject"] = subject
        sent["sentiment"] = sentiment
        sent["subject_matter_shift"] = shift

        if previous_subject and shift:
            break_type = "hard" if related is False else "soft"
            break_id = _stable_id("BR", f"{lake_id}:{previous_subject}:{new_subject}:{break_type}")
            breaks.append(
                {
                    "id": break_id,
                    "timestamp": _dt.datetime.now().isoformat(),
                    "lakeStringId": lake_id,
                    "sentence_id": sent["sentence_id"],
                    "previousSubject": previous_subject,
                    "newSubject": new_subject or subject,
                    "breakType": break_type,
                    "breakCode": f"<!-- HARPER_BREAK:{break_id} -->",
                }
            )
        if subject:
            previous_subject = subject
    return lake_strings, breaks


def build_packet(
    *,
    raw_text: str,
    chunks: list[dict[str, Any]],
    lake_strings: list[dict[str, Any]],
    breaks: list[dict[str, Any]],
    model_used: str,
    processing_time_ms: int,
) -> dict[str, Any]:
    lake_by_sentence = {ls["sentence_id"]: ls for ls in lake_strings}
    breaks_by_lake = {b["lakeStringId"]: b for b in breaks}
    subject_index: dict[str, list[str]] = {}
    sentiment_index: dict[str, list[str]] = {}
    packet_chunks: list[dict[str, Any]] = []

    for chunk in chunks:
        chunk_lakes = [lake_by_sentence[sid] for sid in chunk["sentence_ids"] if sid in lake_by_sentence]
        chunk_breaks = [breaks_by_lake[ls["id"]] for ls in chunk_lakes if ls["id"] in breaks_by_lake]
        subjects = []
        for ls in chunk_lakes:
            if ls.get("subject") and ls["subject"] not in subjects:
                subjects.append(ls["subject"])
            for tag in ls.get("tags", []):
                subject_index.setdefault(tag, []).append(chunk["chunk_id"])
            sentiment_index.setdefault(ls.get("sentiment") or "neutral", []).append(chunk["chunk_id"])
        packet_chunks.append(
            {
                "id": chunk["chunk_id"],
                "index": int(chunk["chunk_id"][1:]) - 1,
                "timestamp": _dt.datetime.now().isoformat(),
                "contextWindow": chunk.get("estimated_tokens"),
                "totalCharacters": sum(int(ls.get("characterCount", 0)) for ls in chunk_lakes),
                "primarySubjectMatter": subjects[0] if subjects else None,
                "subjectMatters": subjects,
                "sentimentSummary": _summarize_sentiment(chunk_lakes),
                "lakeStrings": chunk_lakes,
                "breaks": chunk_breaks,
                "sentenceCount": len(chunk_lakes),
                "breakCount": len(chunk_breaks),
            }
        )

    subject_index = {k: sorted(set(v)) for k, v in subject_index.items()}
    sentiment_index = {k: sorted(set(v)) for k, v in sentiment_index.items()}
    return {
        "id": _stable_id("PKT", raw_text[:500]),
        "timestamp": _dt.datetime.now().isoformat(),
        "sourceTextLength": len(raw_text),
        "sourceTextPreview": raw_text[:500] + ("..." if len(raw_text) > 500 else ""),
        "totalChunks": len(packet_chunks),
        "totalSentences": len(lake_strings),
        "totalBreaks": len(breaks),
        "subjectMatterIndex": subject_index,
        "sentimentIndex": sentiment_index,
        "processingTime": processing_time_ms,
        "modelUsed": model_used,
        "chunks": packet_chunks,
    }


def _summarize_sentiment(lake_strings: list[dict[str, Any]]) -> str:
    if not lake_strings:
        return "neutral"
    avg = sum(float(ls.get("sentimentScore", 0) or 0) for ls in lake_strings) / len(lake_strings)
    if avg > 0.2:
        return "positive"
    if avg < -0.2:
        return "negative"
    return "neutral"


def generate_break_marked_text(chunks: list[dict[str, Any]], lake_strings: list[dict[str, Any]], breaks: list[dict[str, Any]]) -> str:
    lake_by_sentence = {ls["sentence_id"]: ls for ls in lake_strings}
    break_by_lake = {b["lakeStringId"]: b for b in breaks}
    parts: list[str] = []
    for chunk in chunks:
        for sid in chunk["sentence_ids"]:
            lake = lake_by_sentence.get(sid)
            if not lake:
                continue
            br = break_by_lake.get(lake["id"])
            if br:
                parts.append(f"\n{br['breakCode']}\n")
            parts.append(lake["originalSentence"] + " ")
        parts.append(f"\n\n<!-- HARPER_CHUNK:{chunk['chunk_id']} -->\n\n")
    return "".join(parts).strip() + "\n"
