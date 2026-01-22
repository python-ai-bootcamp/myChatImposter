from croniter import croniter
from datetime import datetime
from zoneinfo import ZoneInfo

def test_dst_transition():
    tz_name = "America/New_York"
    tz = ZoneInfo(tz_name)
    cron_schedule = "0 20 * * *"  # 20:00 Daily

    print(f"Testing Schedule: {cron_schedule} in {tz_name}")

    # --- Scenario 1: Spring Forward (March) ---
    # Switch happens early morning March 10, 2024.
    # Run on March 10, 20:00 (This is AFTER the switch, so it's EDT)
    # Actually, let's look at the run on March 10.
    # March 9 20:00 is EST.
    # March 10 20:00 is EDT.
    
    print("\n--- Scenario 1: Spring Forward (Short Day: 23 hours) ---")
    run_time = datetime(2024, 3, 10, 20, 0, 0, tzinfo=tz) 
    print(f"Run Time (Local): {run_time}")
    print(f"Run Time (UTC):   {run_time.astimezone(ZoneInfo('UTC'))}")

    iter = croniter(cron_schedule, run_time)
    # We want the PREVIOUS occurrence relative to this run time (which matches the schedule)
    # croniter.get_prev() from a matching time returns that time first? No, it goes back.
    # Let's verify.
    prev_run = iter.get_prev(datetime)
    
    # If run_time matches exactly, we might need a small delta or just see what get_prev does.
    # If we are executing AT 20:00, we want the period ending NOW.
    # So the *current* window end is run_time. The start is prev_run.
    
    print(f"Prev Run (Local): {prev_run}")
    print(f"Prev Run (UTC):   {prev_run.astimezone(ZoneInfo('UTC'))}")

    # Calculate duration
    diff = run_time.astimezone(ZoneInfo('UTC')) - prev_run.astimezone(ZoneInfo('UTC'))
    print(f"Duration covered: {diff}")
    
    # --- Scenario 2: Fall Back (November) ---
    # Switch happens Nov 3, 2024.
    # Run on Nov 3, 20:00 (EST)
    # Prev run on Nov 2, 20:00 (EDT)

    print("\n--- Scenario 2: Fall Back (Long Day: 25 hours) ---")
    run_time_nov = datetime(2024, 11, 3, 20, 0, 0, tzinfo=tz)
    print(f"Run Time (Local): {run_time_nov}")
    print(f"Run Time (UTC):   {run_time_nov.astimezone(ZoneInfo('UTC'))}")

    iter_nov = croniter(cron_schedule, run_time_nov)
    prev_run_nov = iter_nov.get_prev(datetime)

    print(f"Prev Run (Local): {prev_run_nov}")
    print(f"Prev Run (UTC):   {prev_run_nov.astimezone(ZoneInfo('UTC'))}")

    diff_nov = run_time_nov.astimezone(ZoneInfo('UTC')) - prev_run_nov.astimezone(ZoneInfo('UTC'))
    print(f"Duration covered: {diff_nov}")

if __name__ == "__main__":
    test_dst_transition()
