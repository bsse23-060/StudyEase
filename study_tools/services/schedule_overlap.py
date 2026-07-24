from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from study_tools.models import ScheduleBlock

def _occurrences(block, window_start, window_end):
    tz = ZoneInfo(block.timezone)
    if block.recurrence == ScheduleBlock.Recurrence.ONCE:
        dates = [block.calendar_date] if block.calendar_date and window_start <= block.calendar_date <= window_end else []
    else:
        start = max(window_start, block.recurrence_start or window_start)
        end = min(window_end, block.recurrence_end or window_end)
        offset = (block.weekday - start.weekday()) % 7
        first = start + timedelta(days=offset)
        dates = []
        while first <= end and len(dates) < 370:
            dates.append(first); first += timedelta(days=7)
    return [(datetime.combine(day, block.start_time, tz).astimezone(timezone.utc), datetime.combine(day, block.end_time, tz).astimezone(timezone.utc)) for day in dates]

def overlap_warnings(block):
    if not block.routine_id: return []
    others = ScheduleBlock.objects.filter(routine__owner_id=block.routine.owner_id, is_active=True).exclude(pk=block.pk).select_related("routine")
    today = date.today()
    fixed_dates = [d for d in [block.calendar_date, block.recurrence_start, block.recurrence_end] if d]
    window_start = min(fixed_dates + [today]) - timedelta(days=8)
    window_end = max(fixed_dates + [today + timedelta(days=366)]) + timedelta(days=8)
    own = _occurrences(block, window_start, window_end)
    warnings = []
    for other in others:
        if any(left_start < right_end and right_start < left_end for left_start, left_end in own for right_start, right_end in _occurrences(other, window_start, window_end)):
            warnings.append({"code": "schedule_overlap", "conflicting_block_id": other.pk, "message": f"This overlaps with {other.activity_name}."})
    return warnings
