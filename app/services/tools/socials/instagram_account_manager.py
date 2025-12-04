"""
Instagram Account Manager with rotation, rate limiting, and session management
"""
import os
import json
import time
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from pathlib import Path

try:
    from instagrapi import Client
    from instagrapi.exceptions import LoginRequired, ChallengeRequired, PleaseWaitFewMinutes
    INSTAGRAPI_AVAILABLE = True
except ImportError:
    INSTAGRAPI_AVAILABLE = False
    Client = None

from app import config as app_config


class AccountStatus:
    """Track account health and usage"""
    def __init__(self, username: str):
        self.username = username
        self.is_healthy = True
        self.requests_count = 0
        self.requests_hour_start = datetime.now()
        self.last_used = None
        self.total_requests = 0
        self.ban_count = 0
        self.last_error = None


class InstagramAccountManager:
    """Manage multiple Instagram accounts with rotation and rate limiting"""

    MAX_REQUESTS_PER_HOUR = 180  # Conservative limit (Instagram allows ~200)
    SESSION_DIR = "instagram_sessions"

    def __init__(self):
        self.accounts: Dict[str, AccountStatus] = {}
        self.clients: Dict[str, Client] = {}
        self.current_account_index = 0

        # Create session directory if it doesn't exist
        Path(self.SESSION_DIR).mkdir(exist_ok=True)

        # Load accounts from environment
        self._load_accounts_from_env()

    def _load_accounts_from_env(self):
        """Load Instagram accounts from environment variables"""
        # Support multiple accounts: INSTAGRAM_USERNAME_1, INSTAGRAM_PASSWORD_1, etc.
        account_num = 1
        while True:
            username_key = f"INSTAGRAM_USERNAME_{account_num}" if account_num > 1 else "INSTAGRAM_USERNAME"
            password_key = f"INSTAGRAM_PASSWORD_{account_num}" if account_num > 1 else "INSTAGRAM_PASSWORD"

            username = os.getenv(username_key)
            password = os.getenv(password_key)

            if not username or not password:
                # Try just INSTAGRAM_USERNAME for backwards compatibility
                if account_num == 1:
                    username = os.getenv("INSTAGRAM_USERNAME")
                    password = os.getenv("INSTAGRAM_PASSWORD")
                    if username and password:
                        print(f"[instagram] Loaded account: {username}")
                        self.accounts[username] = AccountStatus(username)
                break

            print(f"[instagram] Loaded account {account_num}: {username}")
            self.accounts[username] = AccountStatus(username)
            account_num += 1

        if not self.accounts:
            print("[instagram] No Instagram accounts configured in .env")
            print("[instagram] Add INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD to enable authenticated access")

    def _get_session_file(self, username: str) -> str:
        """Get session file path for a username"""
        safe_username = username.replace(".", "_").replace("@", "_")
        return os.path.join(self.SESSION_DIR, f"{safe_username}_session.json")

    def _reset_hourly_counter(self, status: AccountStatus):
        """Reset hourly request counter if hour has passed"""
        now = datetime.now()
        if now - status.requests_hour_start >= timedelta(hours=1):
            status.requests_count = 0
            status.requests_hour_start = now

    def _get_healthy_account(self) -> Optional[str]:
        """Get a healthy account with available quota"""
        if not self.accounts:
            return None

        # Reset counters and check health
        for username, status in self.accounts.items():
            self._reset_hourly_counter(status)

            # Check if account has quota available
            if status.is_healthy and status.requests_count < self.MAX_REQUESTS_PER_HOUR:
                return username

        # No account with quota, find least used one
        sorted_accounts = sorted(
            [(u, s) for u, s in self.accounts.items() if s.is_healthy],
            key=lambda x: x[1].requests_count
        )

        if sorted_accounts:
            return sorted_accounts[0][0]

        return None

    def _login_account(self, username: str, password: str) -> Optional[Client]:
        """Login to Instagram account with session management"""
        if not INSTAGRAPI_AVAILABLE:
            print("[instagram] instagrapi not available")
            return None

        try:
            cl = Client()
            cl.delay_range = [1, 3]

            # Set proxy if available
            if app_config.IP2WORLD_STICKY_PROXY:
                cl.set_proxy(app_config.IP2WORLD_STICKY_PROXY)

            session_file = self._get_session_file(username)

            # Try to load existing session
            if os.path.exists(session_file):
                try:
                    cl.load_settings(session_file)
                    # Verify session is still valid
                    cl.get_timeline_feed()
                    print(f"[instagram] Loaded session for: {username}")
                    return cl
                except Exception as e:
                    print(f"[instagram] Session invalid for {username}: {e}")
                    # Session expired, will login fresh

            # Fresh login
            print(f"[instagram] Logging in: {username}")
            cl.login(username, password)

            # Save session for future use
            cl.dump_settings(session_file)
            print(f"[instagram] Session saved for: {username}")

            # Add small delay after login
            time.sleep(random.uniform(2, 4))

            return cl

        except ChallengeRequired as e:
            print(f"[instagram] Challenge required for {username}: {e}")
            self.accounts[username].is_healthy = False
            self.accounts[username].last_error = "Challenge required"
            return None

        except PleaseWaitFewMinutes as e:
            print(f"[instagram] Rate limited for {username}: {e}")
            self.accounts[username].requests_count = self.MAX_REQUESTS_PER_HOUR  # Max out quota
            self.accounts[username].last_error = "Rate limited"
            return None

        except Exception as e:
            print(f"[instagram] Login failed for {username}: {e}")
            self.accounts[username].ban_count += 1
            self.accounts[username].last_error = str(e)

            # Mark as unhealthy after 3 failed attempts
            if self.accounts[username].ban_count >= 3:
                self.accounts[username].is_healthy = False

            return None

    def get_client(self) -> Optional[Client]:
        """Get an authenticated Instagram client with rotation"""
        if not self.accounts:
            return None

        # Get healthy account
        username = self._get_healthy_account()
        if not username:
            print("[instagram] No healthy accounts available")
            return None

        # Check if we already have a client for this account
        if username in self.clients:
            client = self.clients[username]
            # Verify client is still valid
            try:
                client.get_timeline_feed()
                self._record_request(username)
                return client
            except Exception:
                # Client invalid, remove and re-login
                del self.clients[username]

        # Get credentials
        account_num = list(self.accounts.keys()).index(username) + 1
        password_key = f"INSTAGRAM_PASSWORD_{account_num}" if account_num > 1 else "INSTAGRAM_PASSWORD"
        if account_num == 1 and not os.getenv(password_key):
            password_key = "INSTAGRAM_PASSWORD"

        password = os.getenv(password_key)
        if not password:
            print(f"[instagram] Password not found for {username}")
            return None

        # Login
        client = self._login_account(username, password)
        if client:
            self.clients[username] = client
            self._record_request(username)
            return client

        return None

    def _record_request(self, username: str):
        """Record a request for rate limiting"""
        if username in self.accounts:
            status = self.accounts[username]
            status.requests_count += 1
            status.total_requests += 1
            status.last_used = datetime.now()

    def get_stats(self) -> Dict:
        """Get statistics about account usage"""
        stats = {
            "total_accounts": len(self.accounts),
            "healthy_accounts": sum(1 for s in self.accounts.values() if s.is_healthy),
            "accounts": []
        }

        for username, status in self.accounts.items():
            self._reset_hourly_counter(status)
            stats["accounts"].append({
                "username": username,
                "is_healthy": status.is_healthy,
                "requests_this_hour": status.requests_count,
                "total_requests": status.total_requests,
                "ban_count": status.ban_count,
                "last_error": status.last_error,
                "quota_remaining": self.MAX_REQUESTS_PER_HOUR - status.requests_count
            })

        return stats


# Global instance
account_manager = InstagramAccountManager()
