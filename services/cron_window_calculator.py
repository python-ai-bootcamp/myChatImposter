import logging
from datetime import datetime
from croniter import croniter
from zoneinfo import ZoneInfo
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class CronWindowCalculator:
    """
    Service to calculate the time window for a scheduled job based on a cron expression.
    Handles timezone conversions, DST fallback "wiggle" logic, and continuity from persisted state.
    """

    def calculate_window(self, cron_expression: str, timezone: str, now_dt: datetime, last_run_ts: Optional[int] = None) -> Tuple[datetime, datetime]:
        """
        Calculates the start and end of the current processing window.

        Args:
            cron_expression: The cron schedule string.
            timezone: The timezone string (e.g., "UTC", "America/New_York").
            now_dt: The current datetime (timezone-aware).
            last_run_ts: The timestamp (in ms) of the last successful run, if available.

        Returns:
            Tuple[datetime, datetime]: (start_dt, end_dt) of the window.
            Returns (None, None) if calculation fails.
        """
        try:
            # Current Trigger Time (Window End)
            # Use timezone-aware now (passed in) or ensure it matches requested timezone
            # We assume now_dt is already in the correct timezone or we ensure it here.
            tz = ZoneInfo(timezone)
            if now_dt.tzinfo is None:
                # If naive, assume UTC system clock.
                now_dt = now_dt.replace(tzinfo=ZoneInfo("UTC"))
            
            # Convert to target timezone for cron calculation
            now_dt = now_dt.astimezone(tz)
            
            # Snap to the scheduled time (removes jitter/execution delay)
            # This is the "Ideal execution time"
            iter = croniter(cron_expression, now_dt)
            current_cron_end_dt = iter.get_prev(datetime)
            
            # Window Start Logic
            current_cron_start_dt = None
            
            # 1. Try to use persisted state from DB (Most Robust for Continuity)
            if last_run_ts:
                # Safety check: If last run was surprisingly recent (< 2 days), trust it.
                last_run_dt_utc = datetime.fromtimestamp(last_run_ts / 1000, tz=ZoneInfo("UTC"))
                
                # Check age against UTC now
                age_seconds = (datetime.now(ZoneInfo("UTC")) - last_run_dt_utc).total_seconds()
                
                if age_seconds < 48 * 3600:
                    current_cron_start_dt = last_run_dt_utc.astimezone(tz)
                    logger.info(f"Using persisted last_run_ts as start: {current_cron_start_dt}")
            
            # 2. Fallback Calculation (First Run or after Long Downtime)
            if not current_cron_start_dt:
                # We need to find the "Previous Valid Occurrence" relative to End.
                # Standard croniter.get_prev() is known to be buggy around DST Fall Back (skips hour).
                # We implement "Wiggle Recovery".
                
                # A. Try Standard Backward
                iter_back = croniter(cron_expression, current_cron_end_dt)
                candidate_prev = iter_back.get_prev(datetime)
                
                if croniter.match(cron_expression, candidate_prev):
                    # Wiggle Check: If skipped due to DST fallback "phantom hour" logic in croniter
                    iter_fwd_check = croniter(cron_expression, candidate_prev)
                    intermediate = iter_fwd_check.get_next(datetime)
                    
                    if intermediate < current_cron_end_dt and croniter.match(cron_expression, intermediate):
                         logger.info(f"Wiggle Recovery: Found intermediate valid time {intermediate}")
                         current_cron_start_dt = intermediate
                    else:
                         current_cron_start_dt = candidate_prev
                         
                else: 
                     # Candidate is invalid. Wiggle forward from it.
                     iter_wiggle = croniter(cron_expression, candidate_prev)
                     wiggle_candidate = iter_wiggle.get_next(datetime)
                     
                     if wiggle_candidate < current_cron_end_dt and croniter.match(cron_expression, wiggle_candidate):
                         current_cron_start_dt = wiggle_candidate
                     else:
                         # Keep going back until valid (Safety loop)
                         found = False
                         for _ in range(5):
                             candidate_prev = iter_back.get_prev(datetime)
                             if croniter.match(cron_expression, candidate_prev):
                                 current_cron_start_dt = candidate_prev
                                 found = True
                                 break
                         if not found:
                             logger.error("Failed to find valid previous cron time.")
                             return None, None

            return current_cron_start_dt, current_cron_end_dt

        except Exception as e:
            logger.error(f"Failed to calculate cron window: {e}")
            return None, None
