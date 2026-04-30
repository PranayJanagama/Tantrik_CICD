import datetime
import time
import mysql.connector

from nativeauthenticator import NativeAuthenticator
from tornado.web import HTTPError
import os

class JSONBasedNativeAuthenticator(NativeAuthenticator):

    # -------------------------------
    # MYSQL CONFIG
    # -------------------------------
    MYSQL_CONFIG = {
        "host": "10.11.51.225",
        "user": os.getenv("MYSQL_USER"),
        "password": os.getenv("MYSQL_PASSWORD"),
        "database": os.getenv("MYSQL_DATABASE"),
    }

    AL_GROUP_NAME = "nbgrader-al"

    _al_users_cache = set()
    _last_cache_update = 0
    CACHE_TTL = 60   # seconds

    # -------------------------------
    # LOAD AL USERS FROM MYSQL
    # -------------------------------
    def load_al_users(self):
        conn = None
        cursor = None

        try:
            self.log.info("[AL] Loading AL users from MySQL...")

            conn = mysql.connector.connect(**self.MYSQL_CONFIG)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT u.name
                FROM users u
                JOIN user_group_map ugm ON ugm.user_id = u.id
                JOIN `groups` g ON g.id = ugm.group_id
                WHERE g.name = %s
            """, (self.AL_GROUP_NAME,))

            users = {row[0].lower() for row in cursor.fetchall()}

            self._al_users_cache = users
            self._last_cache_update = time.time()

            self.log.info(
                f"[AL CACHE UPDATED] {len(users)} users loaded: {list(users)}"
            )

        except Exception as e:
            self.log.error(f"[AL Enrollment Error] {e}")

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # -------------------------------
    # CHECK IF USER IN AL GROUP
    # -------------------------------
    def is_enrolled_in_al(self, username):

        if time.time() - self._last_cache_update > self.CACHE_TTL:
            self.log.info("[AL] Cache expired. Reloading AL users.")
            self.load_al_users()

        enrolled = username.lower() in self._al_users_cache

        self.log.info(
            f"[AL CHECK] User='{username}' enrolled_in_AL={enrolled}"
        )

        return enrolled

    # -------------------------------
    # AL TIME CHECK
    # -------------------------------
    def is_al_time_allowed(self):
        now = datetime.datetime.now().time()

        start_time = datetime.time(10, 30)
        end_time = datetime.time(18, 0)

        allowed = start_time <= now <= end_time

        self.log.info(
            f"[AL TIME CHECK] current_time={now}, allowed={allowed}"
        )

        return allowed

    # -------------------------------
    # DAY BASED LOGIN RULES
    # -------------------------------
    def is_login_allowed_by_day(self, username):
        uname = username.lower()
        today = datetime.datetime.now().weekday()

        allowed = True

        if uname == "tele":
            allowed = True
        elif "demo" in uname:
            allowed = True
        elif "bd" in uname:
            allowed = today in [4, 5]
        elif uname.startswith("n") or uname.startswith("k"):
            allowed = today in [0, 1, 2, 3]
        elif "p8" in uname:
            allowed = today in [2, 3]

        self.log.info(
            f"[DAY CHECK] user='{username}', weekday={today}, allowed={allowed}"
        )

        return allowed

    # -------------------------------
    # LOGIN CHECK
    # -------------------------------
    async def authenticate(self, handler, data):
        username = data.get("username")

        self.log.info(f"[LOGIN ATTEMPT] username='{username}'")

        if not username:
            raise HTTPError(400, "Username is required")

        if self.is_enrolled_in_al(username):

            self.log.info(f"[LOGIN] {username} is AL student")

            if not self.is_al_time_allowed():
                raise HTTPError(
                    403,
                    "AL students are allowed only between 10:30 AM and 6:00 PM."
                )

        elif not self.is_login_allowed_by_day(username):
            raise HTTPError(
                403,
                f"Login not allowed today for user '{username}'."
            )

        self.log.info(f"[LOGIN SUCCESS] username='{username}'")

        return await super().authenticate(handler, data)

    # -------------------------------
    # SPAWN CHECK
    # -------------------------------
    async def pre_spawn_start(self, user, spawner):

        self.log.info(f"[SPAWN CHECK] user='{user.name}'")

        if self.is_enrolled_in_al(user.name):

            if not self.is_al_time_allowed():
                raise HTTPError(
                    403,
                    "Access denied: AL students allowed only between 10:30 AM and 6:00 PM."
                )
            return

        if not self.is_login_allowed_by_day(user.name):
            raise HTTPError(
                403,
                f"Access denied: User '{user.name}' is not allowed today."
            )
