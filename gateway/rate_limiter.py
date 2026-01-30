"""
Rate limiting for login endpoints.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple


class RateLimiter:
    """
    Rate limiter for login attempts.

    Limits: 10 login attempts per minute per IP address.
    Uses in-memory cache with automatic cleanup.
    """

    def __init__(self, max_attempts: int = 10, window_seconds: int = 60):
        """
        Initialize RateLimiter.

        Args:
            max_attempts: Maximum attempts allowed in window (default 10)
            window_seconds: Time window in seconds (default 60)
        """
        self.max_attempts = max_attempts
        self.window = timedelta(seconds=window_seconds)

        # Cache: {ip_address: [timestamp1, timestamp2, ...]}
        self.attempts: Dict[str, List[datetime]] = {}

    def _cleanup_old_attempts(self, ip_address: str):
        """Remove attempts older than the time window."""
        if ip_address not in self.attempts:
            return

        now = datetime.utcnow()
        cutoff = now - self.window

        # Keep only attempts within window
        self.attempts[ip_address] = [
            timestamp for timestamp in self.attempts[ip_address] if timestamp > cutoff
        ]

        # Remove empty lists
        if not self.attempts[ip_address]:
            del self.attempts[ip_address]

    def check_rate_limit(self, ip_address: str) -> Tuple[bool, int]:
        """
        Check if IP address has exceeded rate limit.

        Args:
            ip_address: Client IP address

        Returns:
            Tuple of (allowed, retry_after_seconds)
            - allowed: True if request is allowed, False if rate limited
            - retry_after_seconds: Seconds until next attempt allowed (0 if allowed)
        """
        # Cleanup old attempts
        self._cleanup_old_attempts(ip_address)

        # Check current attempt count
        if ip_address in self.attempts:
            attempt_count = len(self.attempts[ip_address])

            if attempt_count >= self.max_attempts:
                # Rate limited - calculate retry_after
                oldest_attempt = min(self.attempts[ip_address])
                retry_after = oldest_attempt + self.window - datetime.utcnow()
                retry_after_seconds = max(int(retry_after.total_seconds()), 1)

                logging.warning(
                    f"GATEWAY: Rate limit exceeded for IP {ip_address} "
                    f"({attempt_count} attempts in window)"
                )
                return False, retry_after_seconds

        return True, 0

    def record_attempt(self, ip_address: str):
        """
        Record login attempt for IP address.

        Args:
            ip_address: Client IP address
        """
        now = datetime.utcnow()

        if ip_address not in self.attempts:
            self.attempts[ip_address] = []

        self.attempts[ip_address].append(now)

        # Cleanup old attempts
        self._cleanup_old_attempts(ip_address)

        logging.debug(
            f"GATEWAY: Recorded login attempt for IP {ip_address} "
            f"({len(self.attempts[ip_address])} attempts in window)"
        )

    def reset_ip(self, ip_address: str):
        """
        Reset rate limit for IP address (e.g., after successful login).

        Args:
            ip_address: Client IP address
        """
        if ip_address in self.attempts:
            del self.attempts[ip_address]
            logging.debug(f"GATEWAY: Reset rate limit for IP {ip_address}")

    def clear_all(self):
        """Clear all rate limit data (useful for testing)."""
        self.attempts.clear()
        logging.info("GATEWAY: Rate limiter cleared")
