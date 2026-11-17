import math
import re


def parse_request(instruction, options=None):
    options = dict(options or {})
    text = instruction.lower()
    if "vertical" in text or "portrait" in text or "竖屏" in text or "9:16" in text:
        options["aspect"] = "9:16"
    elif "landscape" in text or "horizontal" in text or "横屏" in text or "16:9" in text:
        options["aspect"] = "16:9"
    options.setdefault("aspect", "16:9")
    options["subtitles"] = options.get("subtitles", True)

    range_match = re.search(r"(\d+)\s*(?:-|–|to)\s*(\d+)\s*(?:seconds?|secs?|s\b)", text)
    single_match = re.search(r"(\d+)\s*(?:seconds?|secs?|s\b)", text)
    if range_match:
        options["min_seconds"] = int(range_match.group(1))
        options["max_seconds"] = int(range_match.group(2))
    elif single_match:
        target = int(single_match.group(1))
        options["min_seconds"] = max(1, target - 5)
        options["max_seconds"] = target + 5
    elif options.get("target_seconds"):
        target = int(options["target_seconds"])
        options["min_seconds"] = max(1, target - 5)
        options["max_seconds"] = target + 5
    else:
        options.setdefault("min_seconds", 20)
        options.setdefault("max_seconds", 60)
    if options["min_seconds"] > options["max_seconds"] or options["max_seconds"] > 600:
        raise ValueError("Target duration must be a valid range of at most 600 seconds")

    if not options.get("topics"):
        match = re.search(r"(?:cover(?:ing)?|include|including|about)\s+(?:only\s+)?(.+?)(?:[.;]|$)", instruction, re.I)
        if match:
            raw = re.sub(r"\s+and\s+", ",", match.group(1), flags=re.I)
            options["topics"] = [item.strip(" .") for item in raw.split(",") if item.strip(" .")]
        else:
            options["topics"] = []
    elif isinstance(options["topics"], str):
        options["topics"] = [item.strip() for item in options["topics"].split(",") if item.strip()]
    first_match = re.search(r"(?:put|move)\s+(.+?)\s+(?:first|to the beginning)", instruction, re.I)
    if first_match:
        options["first_topic"] = first_match.group(1).strip().lower()
    return options


def _tokens(text):
    return set(re.findall(r"[a-z0-9]+", text.lower())) - {"the", "a", "an", "of", "and", "to", "in"}


def _score(topic, cue, document_frequency, document_count):
    words = _tokens(topic)
    found = _tokens(cue["text"])
    if not words:
        return 0.0
    score = sum(math.log(1 + (document_count + 1) / (document_frequency.get(word, 0) + 1)) for word in words & found)
    score /= sum(math.log(1 + (document_count + 1) / (document_frequency.get(word, 0) + 1)) for word in words)
    if topic.lower() in cue["text"].lower():
        score += 0.5
    return score


def validate_timeline(timeline, assets):
    by_id = {asset["id"]: asset for asset in assets}
    if not timeline:
        raise ValueError("Timeline is empty")
    seen = {}
    for clip in timeline:
        asset = by_id.get(clip.get("asset_id"))
        if asset is None:
            raise ValueError("Timeline references an unknown source")
        start, end = float(clip["start"]), float(clip["end"])
        if not (0 <= start < end <= asset["duration"] + 0.05):
            raise ValueError("Timeline contains an out-of-bounds clip")
        seen.setdefault(asset["id"], []).append((start, end))
    for intervals in seen.values():
        intervals.sort()
        if any(right[0] < left[1] - 0.05 for left, right in zip(intervals, intervals[1:])):
            raise ValueError("Timeline contains overlapping clips from the same source")
    return round(sum(float(clip["end"]) - float(clip["start"]) for clip in timeline), 3)


def review_timeline_evidence(timeline, transcript, topics, *, annotate=False):
    """Check only speech that remains audible inside the selected clip bounds."""
    document_frequency = {}
    for cue in transcript:
        for token in _tokens(cue["text"]):
            document_frequency[token] = document_frequency.get(token, 0) + 1

    reviewed = []
    matches = {topic: [] for topic in topics}
    for clip in timeline:
        fragments = []
        for cue in transcript:
            if cue["asset_id"] != clip["asset_id"]:
                continue
            words = cue.get("words", [])
            if words:
                selected = [
                    word["text"].strip() for word in words
                    if clip["start"] <= (word["start"] + word["end"]) / 2 <= clip["end"]
                ]
                content = " ".join(selected)
            else:
                overlap = max(0, min(clip["end"], cue["end"]) - max(clip["start"], cue["start"]))
                content = cue["text"] if overlap >= 0.8 * (cue["end"] - cue["start"]) else ""
            if content:
                fragments.append((cue["id"], content))

        covered = []
        best_score = 0.0
        for topic in topics:
            for cue_id, content in fragments:
                if not _tokens(topic).issubset(_tokens(content)):
                    continue
                score = _score(topic, {"text": content}, document_frequency, len(transcript))
                if score >= 0.35:
                    if cue_id not in matches[topic]:
                        matches[topic].append(cue_id)
                    if topic not in covered:
                        covered.append(topic)
                    best_score = max(best_score, score)
        if annotate:
            clip = dict(clip)
            clip["evidence_ids"] = list(dict.fromkeys(cue_id for cue_id, _ in fragments))
            clip["required"] = bool(covered)
            clip["score"] = round(best_score, 3)
            clip["reason"] = "Required topic: " + ", ".join(covered) if covered else "Manual timeline edit"
        reviewed.append(clip)

    topic_evidence = [
        {"topic": topic, "evidence_ids": matches[topic], "verified": bool(matches[topic])}
        for topic in topics
    ]
    unresolved = [f"No selected spoken evidence found for: {topic}" for topic in topics if not matches[topic]]
    return reviewed, topic_evidence, unresolved


def build_timeline(assets, transcript, options):
    asset_order = {asset["id"]: i for i, asset in enumerate(assets)}
    document_frequency = {}
    for cue in transcript:
        for token in _tokens(cue["text"]):
            document_frequency[token] = document_frequency.get(token, 0) + 1

    selected = {}
    unresolved = []
    for topic in options["topics"]:
        ranked = sorted(
            ((_score(topic, cue, document_frequency, len(transcript)), cue) for cue in transcript),
            key=lambda pair: pair[0], reverse=True,
        )
        if not ranked or ranked[0][0] < 0.35:
            unresolved.append(f"No reliable spoken evidence found for: {topic}")
            continue
        score, cue = ranked[0]
        entry = selected.setdefault(cue["id"], {"cue": cue, "topics": [], "score": score})
        entry["topics"].append(topic)
        entry["score"] = max(entry["score"], score)

    def clip_from(cue, topics, score):
        asset = assets[asset_order[cue["asset_id"]]]
        return {
            "asset_id": cue["asset_id"],
            "start": round(max(0, cue["start"] - 0.18), 3),
            "end": round(min(asset["duration"], cue["end"] + 0.22), 3),
            "evidence_ids": [cue["id"]],
            "reason": "Required topic: " + ", ".join(topics) if topics else "Supporting context",
            "required": bool(topics),
            "score": round(score, 3),
        }

    clips = [clip_from(entry["cue"], entry["topics"], entry["score"]) for entry in selected.values()]
    total = sum(clip["end"] - clip["start"] for clip in clips)
    others = [cue for cue in transcript if cue["id"] not in selected]
    others.sort(key=lambda cue: (asset_order[cue["asset_id"]], cue["start"]))
    for cue in others:
        if total >= options["min_seconds"]:
            break
        clip = clip_from(cue, [], 0.0)
        duration = clip["end"] - clip["start"]
        if total + duration <= options["max_seconds"] + 0.5:
            clips.append(clip)
            total += duration

    if not clips:
        unresolved.append("No speech was detected; using source previews as a fallback")
        for asset in assets:
            clips.append({
                "asset_id": asset["id"], "start": 0.0,
                "end": round(min(asset["duration"], 5.0), 3),
                "evidence_ids": [], "reason": "Unverified visual preview",
                "required": False, "score": 0.0,
            })

    clips.sort(key=lambda clip: (asset_order[clip["asset_id"]], clip["start"]))
    merged = []
    for clip in clips:
        if merged and merged[-1]["asset_id"] == clip["asset_id"] and clip["start"] <= merged[-1]["end"] + 0.12:
            previous = merged[-1]
            previous["end"] = max(previous["end"], clip["end"])
            previous["evidence_ids"] += clip["evidence_ids"]
            previous["required"] = previous["required"] or clip["required"]
            previous["score"] = max(previous["score"], clip["score"])
            if clip["required"] and not previous["reason"].startswith("Required"):
                previous["reason"] = clip["reason"]
        else:
            merged.append(clip)
    first_topic = options.get("first_topic")
    if first_topic:
        cue_by_id = {cue["id"]: cue for cue in transcript}
        match_index = next((
            index for index, clip in enumerate(merged)
            if first_topic in clip["reason"].lower() or any(
                first_topic in cue_by_id[cue_id]["text"].lower()
                for cue_id in clip["evidence_ids"] if cue_id in cue_by_id
            )
        ), None)
        if match_index is not None:
            merged.insert(0, merged.pop(match_index))
        else:
            unresolved.append(f"Could not locate the requested first topic: {first_topic}")
    duration = validate_timeline(merged, assets)
    if duration > options["max_seconds"] + 0.5:
        unresolved.append("Required content exceeds the maximum duration")
    if duration < options["min_seconds"] - 0.5:
        unresolved.append("Not enough relevant speech to meet the minimum duration")
    return merged, unresolved


def _timestamp(seconds):
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"


def repair_duration(timeline, transcript, assets, options, rendered_duration):
    """Make one evidence-preserving duration repair, or return no change."""
    clips = [dict(clip) for clip in timeline]
    if rendered_duration > options["max_seconds"] + 0.7:
        removable = [index for index, clip in enumerate(clips) if not clip["required"]]
        if removable and len(clips) > 1:
            removed = clips.pop(removable[-1])
            return clips, f"Removed supporting clip at {removed['start']:.1f}s to reduce duration"
        return None, "No optional clip can be removed without dropping required content"
    if rendered_duration < options["min_seconds"] - 0.7:
        used = {evidence_id for clip in clips for evidence_id in clip["evidence_ids"]}
        current = sum(clip["end"] - clip["start"] for clip in clips)
        by_id = {asset["id"]: asset for asset in assets}
        for cue in transcript:
            if cue["id"] in used:
                continue
            asset = by_id[cue["asset_id"]]
            start = round(max(0, cue["start"] - 0.18), 3)
            end = round(min(asset["duration"], cue["end"] + 0.22), 3)
            if current + end - start > options["max_seconds"] + 0.5:
                continue
            if any(clip["asset_id"] == cue["asset_id"] and start < clip["end"] and end > clip["start"] for clip in clips):
                continue
            clips.append({
                "asset_id": cue["asset_id"], "start": start, "end": end,
                "evidence_ids": [cue["id"]], "reason": "Added context after duration check",
                "required": False, "score": 0.0,
            })
            order = {asset["id"]: index for index, asset in enumerate(assets)}
            clips.sort(key=lambda clip: (order[clip["asset_id"]], clip["start"]))
            # Duration repair must preserve an explicit first-topic constraint.
            first_topic = options.get("first_topic")
            if first_topic:
                cues = {cue["id"]: cue for cue in transcript}
                first = next((i for i, clip in enumerate(clips) if any(
                    first_topic.lower() in cues[eid]["text"].lower()
                    for eid in clip.get("evidence_ids", []) if eid in cues
                )), None)
                if first is not None:
                    clips.insert(0, clips.pop(first))
            return clips, f"Added source evidence at {cue['start']:.1f}s to meet duration"
        return None, "No suitable source evidence remains to lengthen the recap"
    return None, "Duration already satisfies the brief"


def srt_max_end(srt):
    ends = []
    for line in srt.splitlines():
        if " --> " not in line:
            continue
        value = line.split(" --> ", 1)[1]
        hours, minutes, rest = value.split(":")
        seconds, milliseconds = rest.split(",")
        ends.append(int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000)
    return max(ends, default=0.0)


def make_srt(timeline, transcript):
    cues_by_asset = {}
    for cue in transcript:
        cues_by_asset.setdefault(cue["asset_id"], []).append(cue)
    output = []
    offset = 0.0
    for clip in timeline:
        for cue in cues_by_asset.get(clip["asset_id"], []):
            words = [
                word for word in cue.get("words", [])
                if word["end"] > clip["start"] and word["start"] < clip["end"]
            ]
            if words:
                group = []
                for word in words:
                    group.append(word)
                    content = "".join(item["text"] for item in group).strip()
                    if len(group) >= 7 or len(content) >= 42 or content.endswith((".", "?", "!")):
                        output.append((max(0, offset + group[0]["start"] - clip["start"]), offset + min(group[-1]["end"], clip["end"]) - clip["start"], content))
                        group = []
                if group:
                    output.append((max(0, offset + group[0]["start"] - clip["start"]), offset + min(group[-1]["end"], clip["end"]) - clip["start"], "".join(item["text"] for item in group).strip()))
            else:
                start = max(cue["start"], clip["start"])
                end = min(cue["end"], clip["end"])
                if end - start >= 0.25:
                    output.append((offset + start - clip["start"], offset + end - clip["start"], cue["text"]))
        offset += clip["end"] - clip["start"]
    output.sort()
    return "".join(
        f"{index}\n{_timestamp(start)} --> {_timestamp(end)}\n{text}\n\n"
        for index, (start, end, text) in enumerate(output, start=1)
    )
