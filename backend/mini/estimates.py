"""Read-only broad ETA ranges; never imply completion from a clock."""
import json
import math
import statistics
import time


def number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) and value > 0 else None
    except (ValueError, TypeError):
        return None


def timing(row):
    try:
        value = json.loads(row.get('timing') or '{}')
        return value if isinstance(value, dict) else {}
    except (ValueError, TypeError):
        return {}


def estimates(rows, snapshot, mode, now=None):
    now = time.time() if now is None else now
    active, history, episodes = snapshot
    ratios = []
    for row in history:
        t = timing(row)
        duration, seconds = number(t.get('audio_duration_seconds')), number(t.get('transcription_seconds'))
        if t.get('mode') == mode and duration and seconds:
            ratios.append(seconds / duration)
            if len(ratios) == 30:
                break
    ratio = max(.05, min(2., statistics.median(ratios))) if ratios else .25
    basis = 'history' if ratios else 'initial'

    def own(row):
        t = timing(row)
        duration = number(t.get('audio_duration_seconds')) or number(episodes.get(row.get('episode'), {}).get('duration_seconds'))
        if duration is None:
            return None, None, False
        budget = 30 + ratio * duration
        start = number(t.get('transcription_started_at') if row['status'] == 'transcribing' else t.get('download_started_at')) or number(t.get('started_at'))
        elapsed = max(0, now - start) if start and row['status'] != 'queued' else 0
        low, high = max(15, .6 * budget), max(30, 1.8 * budget)
        if elapsed >= high:
            return None, None, True
        return math.ceil(max(1, low-elapsed)), math.ceil(high-elapsed), False

    result = {}
    lower = upper = 0
    predictable = True
    for index, row in enumerate(active):
        lo, hi, overdue = own(row)
        queued = row['status'] == 'queued'
        known = lo is not None and (predictable or not queued)
        result[row['id']] = {'remaining_lower_seconds': lo + lower if known and queued else lo if known else None,
                             'remaining_upper_seconds': hi + upper if known and queued else hi if known else None,
                             'queue_ahead': index if queued else 0, 'overdue': overdue,
                             'basis': basis if known else 'unknown'}
        if lo is None:
            predictable = False
        else:
            lower += lo
            upper += hi
    return {r['id']: result.get(r['id']) if r['status'] in ('queued','downloading','transcribing') else None for r in rows}
