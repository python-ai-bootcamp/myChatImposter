import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from features.periodic_group_tracking.cron_window import CronWindowCalculator

class TestCronWindowCalculator(unittest.TestCase):
    def setUp(self):
        self.calculator = CronWindowCalculator()

    # --- Scenario 1: Regular Period Calculation ---
    def test_regular_period(self):
        """Test standard hourly calculation in UTC."""
        cron = "0 * * * *"
        tz = "UTC"
        now = datetime(2025, 1, 1, 10, 5, 0, tzinfo=ZoneInfo("UTC"))
        
        start, end = self.calculator.calculate_window(cron, tz, now)
        
        # Window: 09:00 -> 10:00
        self.assertEqual(end, datetime(2025, 1, 1, 10, 0, 0, tzinfo=ZoneInfo("UTC")))
        self.assertEqual(start, datetime(2025, 1, 1, 9, 0, 0, tzinfo=ZoneInfo("UTC")))

    # --- Scenario 4: Regular Catchup ---
    def test_regular_catchup(self):
        """Test catchup when gap is small (e.g. 4 mins)."""
        cron = "0/2 * * * *" # Every 2 mins
        tz = "UTC"
        now = datetime(2025, 1, 1, 10, 5, 5, tzinfo=ZoneInfo("UTC")) # At 10:05:05
        # Ideal End: 10:04:00 (Previous 10:06 is future). 
        # Wait. "0/2". 10:00, 10:02, 10:04, 10:06.
        # Now 10:05. Prev is 10:04.
        
        # Last run: 10:02:00. (Missed 10:04).
        last_run_dt = datetime(2025, 1, 1, 10, 2, 0, tzinfo=ZoneInfo("UTC"))
        last_run_ts = int(last_run_dt.timestamp() * 1000)
        
        start, end = self.calculator.calculate_window(cron, tz, now, last_run_ts)
        
        # Should catch up from 10:02
        self.assertEqual(end, datetime(2025, 1, 1, 10, 4, 0, tzinfo=ZoneInfo("UTC")))
        self.assertEqual(start, last_run_dt)

    # --- Scenario 5: Catchup with Limit (Capping) ---
    def test_catchup_cap_when_exceeds_limit_small(self):
        """Test catchup CAPPED if gap is 30 mins (Limit 15 mins)."""
        cron = "0 * * * *" # Hourly
        tz = "UTC"
        now = datetime(2025, 1, 1, 10, 5, 0, tzinfo=ZoneInfo("UTC"))
        
        # Last run: 30 minutes ago (09:30).
        # Ideal Start: 09:00. End: 10:00.
        # last_run (09:30) > ideal (09:00). Wait.
        # If last_run is 09:30.
        # Logic: last_run (09:30) > ideal (09:00).
        # THEN it falls into `else` block (Restored).
        # current = last_run (09:30).
        # Window: 09:30 -> 10:00.
        # THIS IS CONTINUITY. IT DOES NOT TRIGGER CATCHUP LIMIT.
        # Why? Because `Gap` logic is `ideal_start - last_run`.
        # If `last_run > ideal_start`, gap is negative.
        # So it uses continuity.
        
        # TO TRIGGER LIMIT:
        # We need `last_run < ideal_start - 15m`.
        # ideal_start = 09:00.
        # Limit = 15m.
        # So last_run must be < 08:45.
        
        # Let's say last_run = 08:30.
        # Gap = 09:00 - 08:30 = 30 mins.
        # 30m > 15m.
        # Logic: Cap to 15m.
        # Start = End (10:00) - 15m = 09:45.
        # Window: 09:45 -> 10:00.
        # (We lose 08:30 -> 09:45).
        
        last_run_dt = datetime(2025, 1, 1, 8, 30, 0, tzinfo=ZoneInfo("UTC"))
        last_run_ts = int(last_run_dt.timestamp() * 1000)
        
        start, end = self.calculator.calculate_window(cron, tz, now, last_run_ts)
        
        # Expect Capping to last 15 mins
        expected_start = datetime(2025, 1, 1, 9, 45, 0, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(end, datetime(2025, 1, 1, 10, 0, 0, tzinfo=ZoneInfo("UTC")))
        self.assertEqual(start, expected_start)

    def test_catchup_with_limit_massive_gap(self):
        """Test catchup CAPPED if gap is 17 hours."""
        cron = "0 * * * *" # Hourly
        tz = "UTC"
        now = datetime(2025, 1, 2, 10, 5, 0, tzinfo=ZoneInfo("UTC"))
        
        # Last run: 17 hours ago
        last_run_dt = datetime(2025, 1, 1, 17, 0, 0, tzinfo=ZoneInfo("UTC"))
        last_run_ts = int(last_run_dt.timestamp() * 1000)
        
        start, end = self.calculator.calculate_window(cron, tz, now, last_run_ts)
        
        # Ideal window: 09:00 -> 10:00.
        # Gap is huge.
        # Cap to 15 mins.
        # Start = 10:00 - 15m = 09:45.
        
        expected_end = datetime(2025, 1, 2, 10, 0, 0, tzinfo=ZoneInfo("UTC"))
        expected_start = datetime(2025, 1, 2, 9, 45, 0, tzinfo=ZoneInfo("UTC"))
        
        self.assertEqual(end, expected_end)
        self.assertEqual(start, expected_start)

    # --- Scenario 2: DST Spring Forward ---
    def test_dst_spring_forward(self):
        """
        March 10, 2024 (US/Eastern). 02:00 -> 03:00.
        01:00 EST -> 03:00 EDT.
        """
        cron = "0 * * * *"
        tz = "America/New_York"
        
        # Run at 03:05 EDT (07:05 UTC)
        # Previous run was 01:00 EST (06:00 UTC)
        now = datetime(2024, 3, 10, 7, 5, 0, tzinfo=ZoneInfo("UTC")) # 03:05 EDT
        last_run_dt = datetime(2024, 3, 10, 6, 0, 0, tzinfo=ZoneInfo("UTC")) # 01:00 EST
        last_run_ts = int(last_run_dt.timestamp() * 1000)
        
        start, end = self.calculator.calculate_window(cron, tz, now, last_run_ts)
        
        # End: 03:00 EDT (07:00 UTC)
        # Start: Should be 01:00 EST (06:00 UTC) because 02:00 was skipped.
        # And we have last_run_ts matching it.
        
        self.assertEqual(end.astimezone(ZoneInfo("UTC")), datetime(2024, 3, 10, 7, 0, 0, tzinfo=ZoneInfo("UTC")))
        self.assertEqual(start.astimezone(ZoneInfo("UTC")), datetime(2024, 3, 10, 6, 0, 0, tzinfo=ZoneInfo("UTC")))

    # --- Scenario 3: DST Fall Back ---
    def test_dst_fall_back(self):
        """
        Nov 3, 2024 (US/Eastern). 02:00 -> 01:00.
        01:00 happened twice: 01:00 EDT and 01:00 EST.
        """
        cron = "0 * * * *"
        tz = "America/New_York"
        
        # CASE A: Run at 01:05 EST (Second 1:00). 06:05 UTC.
        # This is where 'phantom hour' usually gets skipped.
        # We expect window: 01:00 EDT (05:00 UTC) -> 01:00 EST (06:00 UTC).
        
        now = datetime(2024, 11, 3, 6, 5, 0, tzinfo=ZoneInfo("UTC")) # 01:05 EST
        
        # Last run was 01:00 EDT (05:00 UTC)
        last_run_dt = datetime(2024, 11, 3, 5, 0, 0, tzinfo=ZoneInfo("UTC"))
        last_run_ts = int(last_run_dt.timestamp() * 1000)
        
        start, end = self.calculator.calculate_window(cron, tz, now, last_run_ts)
        
        # End must be 01:00 EST (06:00 UTC).
        self.assertEqual(end.astimezone(ZoneInfo("UTC")), datetime(2024, 11, 3, 6, 0, 0, tzinfo=ZoneInfo("UTC")))
        
        # Start must be 01:00 EDT (05:00 UTC).
        self.assertEqual(start.astimezone(ZoneInfo("UTC")), datetime(2024, 11, 3, 5, 0, 0, tzinfo=ZoneInfo("UTC")))

    # --- Scenario 6: Spring Forward (Small Period 30m) ---
    def test_dst_spring_forward_small_period(self):
        """
        March 10, 2024. 02:00 -> 03:00.
        Cron: */30.
        Sequence: 01:30 EST -> (02:00 skipped) -> (02:30 skipped) -> 03:00 EDT.
        """
        cron = "*/30 * * * *"
        tz = "America/New_York"
        
        # Run at 03:05 EDT (07:05 UTC)
        # Previous successful run was 01:30 EST (06:30 UTC)
        now = datetime(2024, 3, 10, 7, 5, 0, tzinfo=ZoneInfo("UTC"))
        last_run_dt = datetime(2024, 3, 10, 6, 30, 0, tzinfo=ZoneInfo("UTC"))
        last_run_ts = int(last_run_dt.timestamp() * 1000)
        
        start, end = self.calculator.calculate_window(cron, tz, now, last_run_ts)
        
        # End should be 03:00 EDT (07:00 UTC).
        self.assertEqual(end.astimezone(ZoneInfo("UTC")), datetime(2024, 3, 10, 7, 0, 0, tzinfo=ZoneInfo("UTC")))
        
        # Start should be last_run_dt (01:30 EST / 06:30 UTC) to ensure continuity over the gap.
        # Ideally, prev of 03:00 EDT is 01:30 EST. (Since 02:00/02:30 skipped).
        self.assertEqual(start.astimezone(ZoneInfo("UTC")), datetime(2024, 3, 10, 6, 30, 0, tzinfo=ZoneInfo("UTC")))

    # --- Scenario 7: Fall Back (Small Period 30m) ---
    def test_dst_fall_back_small_period(self):
        """
        Nov 3, 2024. 02:00 -> 01:00.
        Cron: */30.
        Sequence: 01:00 EDT, 01:30 EDT, 01:00 EST, 01:30 EST.
        """
        cron = "*/30 * * * *"
        tz = "America/New_York"
        
        # Run at 01:05 EST (06:05 UTC).
        # Should capture window ending at 01:00 EST (06:00 UTC).
        # Previous run was 01:30 EDT (05:30 UTC).
        
        now = datetime(2024, 11, 3, 6, 5, 0, tzinfo=ZoneInfo("UTC"))
        last_run_dt = datetime(2024, 11, 3, 5, 30, 0, tzinfo=ZoneInfo("UTC"))
        last_run_ts = int(last_run_dt.timestamp() * 1000)
        
        start, end = self.calculator.calculate_window(cron, tz, now, last_run_ts)
        
        # End: 01:00 EST (06:00 UTC).
        self.assertEqual(end.astimezone(ZoneInfo("UTC")), datetime(2024, 11, 3, 6, 0, 0, tzinfo=ZoneInfo("UTC")))
        
        # Start: 01:30 EDT (05:30 UTC).
        self.assertEqual(start.astimezone(ZoneInfo("UTC")), datetime(2024, 11, 3, 5, 30, 0, tzinfo=ZoneInfo("UTC")))


if __name__ == '__main__':
    unittest.main()
