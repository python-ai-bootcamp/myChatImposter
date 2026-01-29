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
            # This is the "Ideal execution time" (End of the window)
            current_cron_end_dt = self._get_prev_cron_with_wiggle(cron_expression, now_dt)
            
            if not current_cron_end_dt:
                 logger.error("Failed to calculate current cron end time.")
                 return None, None

            # --- Calculate Ideal Start (Previous Interval) ---
            # using same robust logic relative to End
            ideal_start_dt = self._get_prev_cron_with_wiggle(cron_expression, current_cron_end_dt)
            
            if not ideal_start_dt:
                logger.error("Failed to find valid previous cron time (ideal start).")
                return None, None

            # --- Window Start Logic (Continuity vs Catchup) ---
            current_cron_start_dt = ideal_start_dt
            
            if last_run_ts:
                try:
                    last_run_dt_utc = datetime.fromtimestamp(last_run_ts / 1000, tz=ZoneInfo("UTC"))
                    last_run_dt = last_run_dt_utc.astimezone(tz)
                    
                    if last_run_dt < ideal_start_dt:
                        # Check gap size
                        gap_seconds = (ideal_start_dt - last_run_dt).total_seconds()
                        MAX_CATCHUP_SECONDS = 900 # 15 minutes
                        
                        if gap_seconds <= MAX_CATCHUP_SECONDS:
                            current_cron_start_dt = last_run_dt
                            logger.info(f"Catching up: Using last_run_ts {last_run_dt} (Gap: {gap_seconds}s)")
                        else:
                            # Gap too large. Instead of skipping entirely, CAP the window to the limit.
                            # This ensures we at least process the most recent MAX_CATCHUP_SECONDS of data.
                            from datetime import timedelta
                            current_cron_start_dt = current_cron_end_dt - timedelta(seconds=MAX_CATCHUP_SECONDS)
                            
                            if current_cron_start_dt < last_run_dt:
                                current_cron_start_dt = last_run_dt

                            logger.warning(f"Gap too large ({gap_seconds}s > {MAX_CATCHUP_SECONDS}s). Capping catchup window to last {MAX_CATCHUP_SECONDS}s. Start: {current_cron_start_dt}")
                    else:
                        # last_run >= ideal_start (e.g. perfect alignment or strange clock skew)
                        current_cron_start_dt = last_run_dt
                        logger.info(f"Using persisted last_run_ts as start: {current_cron_start_dt}")

                except Exception as e:
                    logger.warning(f"Failed to process last_run_ts: {e}. Using ideal start.")
            
            return current_cron_start_dt, current_cron_end_dt

        except Exception as e:
            logger.error(f"Failed to calculate cron window: {e}")
            return None, None

    def _get_prev_cron_with_wiggle(self, cron_expression: str, from_dt: datetime) -> Optional[datetime]:
        """
        Calculates the previous cron occurrence relative to from_dt,
        handling DST fallback 'phantom hours' where croniter might skip an occurrence.
        """
        try:
            # A. Try Standard Backward
            iter_back = croniter(cron_expression, from_dt)
            candidate_prev = iter_back.get_prev(datetime)
            
            # Safety: Ensure we actually went back in time (DST quirks)
            while candidate_prev >= from_dt:
                logger.warning(f"Croniter returned future/present time {candidate_prev}. Retrying.")
                candidate_prev = iter_back.get_prev(datetime)
            
            if croniter.match(cron_expression, candidate_prev):
                # Wiggle Check: If skipped due to DST fallback "phantom hour" logic in croniter
                iter_fwd_check = croniter(cron_expression, candidate_prev)
                intermediate = iter_fwd_check.get_next(datetime)
                
                # If intermediate is valid AND effectively 'next' from candidate but 'prev' from from_dt
                if intermediate < from_dt and croniter.match(cron_expression, intermediate):
                        # Found a hidden occurrence
                        return intermediate
                
                # Fold Check: Check for ambiguous hour repetition (e.g. 1:00 AM happening twice)
                # If we have the first occurrence (fold=0), check if the second (fold=1) is valid and earlier than from_dt
                if candidate_prev.fold == 0:
                     other_fold = candidate_prev.replace(fold=1)
                     # Check if it is actually ambiguous (offsets differ)
                     if other_fold.utcoffset() != candidate_prev.utcoffset():
                         match = croniter.match(cron_expression, other_fold)
                         # Explicitly compare timestamps for safety (handle fold comparison quirks)
                         cond1 = other_fold.timestamp() < from_dt.timestamp()
                         cond2 = other_fold.timestamp() > candidate_prev.timestamp()
                         
                         if match and cond1 and cond2:
                             return other_fold

                return candidate_prev
                        
            else: 
                    # Candidate is invalid. Wiggle forward from it.
                    iter_wiggle = croniter(cron_expression, candidate_prev)
                    wiggle_candidate = iter_wiggle.get_next(datetime)
                    
                    if wiggle_candidate < from_dt and croniter.match(cron_expression, wiggle_candidate):
                        return wiggle_candidate
                    else:
                        # Keep going back until valid (Safety loop)
                        for _ in range(5):
                            candidate_prev = iter_back.get_prev(datetime)
                            if croniter.match(cron_expression, candidate_prev):
                                return candidate_prev
                        return None
        except Exception as e:
            logger.error(f"Error in _get_prev_cron_with_wiggle: {e}")
            return None
