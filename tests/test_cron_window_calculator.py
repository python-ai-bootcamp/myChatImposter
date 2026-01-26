import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from services.cron_window_calculator import CronWindowCalculator

@pytest.fixture
def calculator():
    return CronWindowCalculator()

def test_standard_interval(calculator):
    """Test a standard 10-minute interval."""
    cron = "*/10 * * * *"
    tz = "UTC"
    
    # Simulate run at 10:05 (Should trigger for 10:00 window)
    now = datetime(2025, 1, 1, 10, 5, 0, tzinfo=ZoneInfo(tz))
    
    start_dt, end_dt = calculator.calculate_window(cron, tz, now)
    
    assert end_dt == datetime(2025, 1, 1, 10, 0, 0, tzinfo=ZoneInfo(tz))
    assert start_dt == datetime(2025, 1, 1, 9, 50, 0, tzinfo=ZoneInfo(tz))

def test_persisted_state(calculator):
    """Test using persisted last_run_ts."""
    cron = "*/10 * * * *"
    tz = "UTC"
    now = datetime(2025, 1, 1, 10, 5, 0, tzinfo=ZoneInfo(tz))
    
    # Last run was at 09:50
    last_run_dt = datetime(2025, 1, 1, 9, 50, 0, tzinfo=ZoneInfo("UTC"))
    last_run_ts = int(last_run_dt.timestamp() * 1000)
    
    start_dt, end_dt = calculator.calculate_window(cron, tz, now, last_run_ts=last_run_ts)
    
    assert end_dt == datetime(2025, 1, 1, 10, 0, 0, tzinfo=ZoneInfo(tz))
    assert start_dt == last_run_dt

def test_persisted_state_too_old(calculator):
    """Test persisted state ignored if too old (> 48h)."""
    cron = "0 10 * * *" # Daily at 10am
    tz = "UTC"
    now = datetime(2025, 1, 10, 10, 5, 0, tzinfo=ZoneInfo(tz))
    
    # Last run was month ago
    last_run_dt = datetime(2024, 12, 1, 10, 0, 0, tzinfo=ZoneInfo("UTC"))
    last_run_ts = int(last_run_dt.timestamp() * 1000)
    
    start_dt, end_dt = calculator.calculate_window(cron, tz, now, last_run_ts=last_run_ts)
    
    assert end_dt == datetime(2025, 1, 10, 10, 0, 0, tzinfo=ZoneInfo(tz))
    # Should fallback to previous day, ignoring the stale last_run_ts
    assert start_dt == datetime(2025, 1, 9, 10, 0, 0, tzinfo=ZoneInfo(tz))

def test_timezone_conversion(calculator):
    """Test window calculation in specific timezone (EST)."""
    cron = "0 9 * * *" # 9 AM Daily
    tz = "America/New_York"
    
    # Run at 9:05 EST
    now = datetime(2025, 1, 1, 9, 5, 0, tzinfo=ZoneInfo(tz))
    
    start_dt, end_dt = calculator.calculate_window(cron, tz, now)
    
    assert end_dt == datetime(2025, 1, 1, 9, 0, 0, tzinfo=ZoneInfo(tz))
    assert start_dt == datetime(2024, 12, 31, 9, 0, 0, tzinfo=ZoneInfo(tz))


def test_naive_input_assumed_utc(calculator):
    """Test that naive input is treated as UTC, not the target timezone."""
    cron = "*/10 * * * *"
    tz = "America/New_York" # UTC-5
    
    # Input: 10:05 (Naive, implying UTC system clock)
    now = datetime(2025, 1, 1, 10, 5, 0)
    
    start_dt, end_dt = calculator.calculate_window(cron, tz, now)
    
    # 10:05 UTC is 05:05 EST.
    # Window should be 05:00 EST (End) and 04:50 EST (Start)
    expected_end = datetime(2025, 1, 1, 5, 0, 0, tzinfo=ZoneInfo(tz))
    expected_start = datetime(2025, 1, 1, 4, 50, 0, tzinfo=ZoneInfo(tz))
    
    assert end_dt == expected_end
    assert start_dt == expected_start
