import re


def format_ass_timestamp(seconds):
    """Convert a duration in seconds to an ASS timestamp (H:MM:SS.cs)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centiseconds = int(round((seconds - int(seconds)) * 100))
    if centiseconds == 100:
        secs += 1
        centiseconds = 0
    if secs == 60:
        minutes += 1
        secs = 0
    if minutes == 60:
        hours += 1
        minutes = 0
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def generate_ass_file(df, output_path, font_name="Arial", font_size=24, alignment=2, bg_box=False):
    """Generate an ASS subtitle file from a DataFrame of timed segments."""
    border_style = 3 if bg_box else 1
    back_colour = "&H90000000" if bg_box else "&H00000000"
    ass_content = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 384", "PlayResY: 288", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H00000000,{back_colour},0,0,0,0,100,100,0,0,{border_style},2,1,{alignment},10,10,10,1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for _, row in df.iterrows():
        trans_text = str(row["Trans"]).strip()
        if trans_text:
            start_ts = format_ass_timestamp(timestamp_to_seconds(row["Start"]))
            end_ts = format_ass_timestamp(timestamp_to_seconds(row["End"]))
            ass_text = trans_text.replace("\n", "\\N")
            ass_content.append(f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{ass_text}")

    with open(output_path, "w", encoding="utf-8") as subtitle_file:
        subtitle_file.write("\n".join(ass_content))
    print(f"ASS subtitle script generated: {output_path}")


def clean_khmer_subtitles(text):
    """Normalize Khmer subtitle punctuation and spacing without changing wording."""
    if not text:
        return text
    text = re.sub(r"[\r\n]+", " ", str(text))
    text = re.sub(r"[ \t]+", " ", text).strip()
    text = re.sub(r"\s+([។៕៖?!])", r"\1", text)
    if text.endswith("."):
        text = text[:-1] + "។"
    elif text.endswith((",", ";", ":")):
        text = text[:-1].rstrip() + "។"
    elif not text.endswith(("។", "៕", "៖", "?", "!")):
        text += "។"
    return text


def balance_khmer_lines(text, max_len=42):
    """Use at most two balanced lines, breaking only between words."""
    if not text or len(text) <= max_len:
        return text
    break_points = [i for i, char in enumerate(text) if char in (" ", "\u200b") and 0 < i < len(text) - 1]
    if not break_points:
        return text

    def line_balance_cost(index):
        left = len(text[:index].strip())
        right = len(text[index + 1:].strip())
        return abs(left - right) + max(0, left - max_len) * 3 + max(0, right - max_len) * 3

    best_break = min(break_points, key=line_balance_cost)
    return text[:best_break].rstrip() + "\n" + text[best_break + 1:].lstrip()


def merge_fragmented_segments(segments, max_gap=1.5):
    """Merge adjacent fragments while preserving their enclosing timing (limit to max 5 merged segments)."""
    if not segments:
        return []
    merged = []
    current = None
    terminal_marks = (".", "។", "៕", "៖", "?", "!")
    for segment in segments:
        text = segment.get("text", "").strip()
        if not text:
            continue
        if current is None:
            current = {
                "id": segment.get("id", 0), 
                "start": segment.get("start", 0.0), 
                "end": segment.get("end", 0.0), 
                "text": text,
                "merge_count": 1
            }
            continue
        gap = segment.get("start", 0.0) - current["end"]
        if not current["text"].rstrip().endswith(terminal_marks) and gap <= max_gap and current.get("merge_count", 1) < 5:
            current["text"] += " " + text
            current["end"] = segment.get("end", current["end"])
            current["merge_count"] = current.get("merge_count", 1) + 1
        else:
            current.pop("merge_count", None)
            merged.append(current)
            current = {
                "id": segment.get("id", 0), 
                "start": segment.get("start", 0.0), 
                "end": segment.get("end", 0.0), 
                "text": text,
                "merge_count": 1
            }
    if current is not None:
        current.pop("merge_count", None)
        merged.append(current)
    return merged


def seconds_to_timestamp(seconds):
    """Convert float seconds to a MM:SS.SS string."""
    try:
        seconds = float(seconds)
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes:02d}:{secs:05.2f}"
    except Exception:
        return "00:00.00"


def timestamp_to_seconds(ts_str):
    """Convert MM:SS.SS or HH:MM:SS.ms string back to float seconds."""
    try:
        ts_str = str(ts_str).strip()
        if not ts_str:
            return 0.0
        parts = ts_str.split(":")
        if len(parts) == 3: # HH:MM:SS.ms
            h, m, s = parts
            return float(h) * 3600 + float(m) * 60 + float(s)
        elif len(parts) == 2: # MM:SS.ms
            m, s = parts
            return float(m) * 60 + float(s)
        return float(ts_str)
    except Exception:
        return 0.0
