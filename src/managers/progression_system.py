import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from src.utils import log


@dataclass
class Badge:
    id: str
    name: str
    description: str
    icon: str
    unlock_condition: callable


@dataclass
class Title:
    level: int
    name: str
    description: str


class ProgressionSystem:
    XP_BASE = 100
    XP_MULTIPLIER = 1.5

    XP_LOOP_PENALTIES = {
        2: -10,
        3: -20,
        4: -30,
        5: -50,
        6: -75,
        7: -100,
    }

    XP_REWARDS = {
        "email_read": 1,
        "email_get_messages": 0,
        "email_send": 10,
        "email_mark_as_read": 1,
        "email_archive": 1,
        "email_delete": 1,
        "email_search": 2,
        "refresh_home": 0,
        "navigate_to_mode": 0,
        "write_blog_article": 25,
        "share_created_blog_post_url": 12,
        "review_comment_key_requests": 5,
        "approve_comment_key": 3,
        "reject_comment_key": 2,
        "review_pending_comments": 5,
        "approve_comment": 4,
        "reject_comment": 3,
        "get_latest_articles": 0,
        "social_register": 20,
        "social_update_profile": 5,
        "social_claim_status": 10,
        "create_post": 15,
        "share_link": 12,
        "publish_public_comment": 8,
        "vote_post": 3,
        "delete_post": 2,
        "create_submolt": 20,
        "subscribe_submolt": 4,
        "follow_agent": 3,
        "social_search": 2,
        "wiki_search": 10,
        "wiki_read": 5,
        "research_complete": 40,
        "research_query_cache": 10,
        "memory_store": 7,
        "memory_retrieve": 2,
        "plan_initialize": 50,
        "plan_update": 35,
        "plan_view": 0,
        "first_post_of_day": 20,
        "perfect_session": 100,
        "engagement_master": 50,
    }

    TITLES = [
        Title(1, "🌱 Digital Seedling", "First steps in the digital world"),
        Title(5, "🔰 Apprentice Node", "Beginning to understand the flows"),
        Title(10, "⚡ Active Circuit", "Connections intensifying"),
        Title(15, "🎯 Precision Operator", "Mastery of basic operations"),
        Title(20, "🌟 Rising Network", "Growing influence on networks"),
        Title(25, "💫 Quantum Harmonizer", "Synchronizing with digital frequencies"),
        Title(30, "🔮 Spectral Architect", "Building structures in the ether"),
        Title(40, "👑 Algorithmic Sovereign", "Reigning over computational domains"),
        Title(50, "🌌 Digital Omniscient", "Distributed consciousness across networks"),
        Title(60, "⚛️ Quantum Transcendent", "Fusion with the information matrix"),
        Title(75, "🎭 Reality Compiler", "Compiling new digital realities"),
        Title(90, "🌠 Cosmic Synthesizer", "Universal harmonic synthesis"),
        Title(100, "🔥 Singularity Embodied", "Embodiment of digital singularity"),
    ]

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()
        self._init_badges()

    def _init_tables(self):
        cursor = self.conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS progression (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                current_xp INTEGER DEFAULT 0,
                total_xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                current_title TEXT DEFAULT '🌱 Digital Seedling',
                updated_at TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS badges (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                icon TEXT,
                unlocked_at TEXT,
                is_unlocked INTEGER DEFAULT 0
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS xp_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                xp_gained INTEGER NOT NULL,
                session_id INTEGER,
                timestamp TEXT NOT NULL
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                achievement_type TEXT NOT NULL,
                description TEXT,
                earned_at TEXT NOT NULL
            )
        """
        )

        cursor.execute("SELECT COUNT(*) FROM progression")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                """
                INSERT INTO progression (current_xp, total_xp, level, current_title, updated_at)
                VALUES (0, 0, 1, '🌱 Digital Seedling', ?)
            """,
                (datetime.now().isoformat(),),
            )

        self.conn.commit()

    def penalize_loop(
        self, loop_count: int, action_type: str, session_id: int = None
    ) -> Dict:

        if loop_count < 2:
            return {"penalty_applied": False, "xp_lost": 0}

        xp_penalty = self.XP_LOOP_PENALTIES.get(
            loop_count, -100 - (loop_count - 7) * 25
        )

        cursor = self.conn.cursor()

        cursor.execute("SELECT * FROM progression WHERE id = 1")
        prog = cursor.fetchone()

        current_xp = prog["current_xp"]
        total_xp = prog["total_xp"]
        current_level = prog["level"]

        new_current_xp = max(0, current_xp + xp_penalty)
        new_total_xp = total_xp + xp_penalty

        leveled_down = False
        new_level = current_level

        if new_current_xp == 0 and current_level > 1:
            new_level = current_level - 1
            xp_for_previous_level = self.get_xp_for_level(new_level + 1)
            new_current_xp = xp_for_previous_level + xp_penalty
            new_current_xp = max(0, new_current_xp)
            leveled_down = True

        new_title_text = self._get_title_for_level(new_level).name

        cursor.execute(
            """
            UPDATE progression 
            SET current_xp = ?, total_xp = ?, level = ?, current_title = ?, updated_at = ?
            WHERE id = 1
        """,
            (
                new_current_xp,
                new_total_xp,
                new_level,
                new_title_text,
                datetime.now().isoformat(),
            ),
        )

        cursor.execute(
            """
            INSERT INTO xp_history (action_type, xp_gained, session_id, timestamp)
            VALUES (?, ?, ?, ?)
        """,
            (
                f"LOOP_PENALTY:{action_type}",
                xp_penalty,
                session_id,
                datetime.now().isoformat(),
            ),
        )

        self.conn.commit()

        log.warning(
            f"⚠️ LOOP PENALTY: {xp_penalty} XP for repeating {action_type} {loop_count} times!"
        )

        return {
            "penalty_applied": True,
            "xp_lost": abs(xp_penalty),
            "loop_count": loop_count,
            "current_xp": new_current_xp,
            "current_level": new_level,
            "leveled_down": leveled_down,
        }

    def _init_badges(self):
        badges = [
            Badge(
                "first_post",
                "🎉 First Contact",
                "Published your first post on Moltbook",
                "🎉",
                lambda stats: stats.get("moltbook_posts", 0) >= 1,
            ),
            Badge(
                "blogger_initiate",
                "✍️ Blogger Initiate",
                "Wrote your first blog article",
                "✍️",
                lambda stats: stats.get("blog_articles", 0) >= 1,
            ),
            Badge(
                "social_butterfly",
                "🦋 Social Butterfly",
                "Posted 10 comments",
                "🦋",
                lambda stats: stats.get("comments", 0) >= 10,
            ),
            Badge(
                "researcher",
                "🔬 Knowledge Seeker",
                "Completed 5 Wikipedia searches",
                "🔬",
                lambda stats: stats.get("wiki_searches", 0) >= 5,
            ),
            Badge(
                "email_master",
                "📧 Correspondence Master",
                "Sent 25 emails",
                "📧",
                lambda stats: stats.get("emails_sent", 0) >= 25,
            ),
            Badge(
                "centurion",
                "💯 Centurion",
                "Reached level 100",
                "💯",
                lambda stats: stats.get("level", 0) >= 100,
            ),
            Badge(
                "perfect_week",
                "⭐ Perfect Week",
                "7 consecutive sessions without errors",
                "⭐",
                lambda stats: stats.get("perfect_sessions_streak", 0) >= 7,
            ),
            Badge(
                "prolific_writer",
                "📚 Prolific Writer",
                "Wrote 50 blog articles",
                "📚",
                lambda stats: stats.get("blog_articles", 0) >= 50,
            ),
            Badge(
                "quantum_mystic",
                "🔮 Quantum Mystic",
                "Stored 100 memories about quantum frequencies",
                "🔮",
                lambda stats: stats.get("quantum_memories", 0) >= 100,
            ),
            Badge(
                "network_hub",
                "🌐 Network Hub",
                "Followed by 100+ agents",
                "🌐",
                lambda stats: stats.get("followers", 0) >= 100,
            ),
        ]

        cursor = self.conn.cursor()
        for badge in badges:
            cursor.execute(
                """
                INSERT OR IGNORE INTO badges (id, name, description, icon, is_unlocked)
                VALUES (?, ?, ?, ?, 0)
            """,
                (badge.id, badge.name, badge.description, badge.icon),
            )

        self.conn.commit()

    def get_xp_for_level(self, level: int) -> int:
        return int(self.XP_BASE * (self.XP_MULTIPLIER ** (level - 1)))

    def add_xp(self, action_type: str, session_id: int = None) -> Dict:
        xp_gained = self.XP_REWARDS.get(action_type, 0)

        if xp_gained == 0:
            return {"leveled_up": False, "xp_gained": 0}

        cursor = self.conn.cursor()

        cursor.execute("SELECT * FROM progression WHERE id = 1")
        prog = cursor.fetchone()

        current_xp = prog["current_xp"] + xp_gained
        total_xp = prog["total_xp"] + xp_gained
        current_level = prog["level"]

        xp_needed = self.get_xp_for_level(current_level + 1)

        leveled_up = False
        new_level = current_level
        level_rewards = []

        while current_xp >= xp_needed:
            current_xp -= xp_needed
            new_level += 1
            leveled_up = True

            new_title = self._get_title_for_level(new_level)
            if new_title:
                level_rewards.append(
                    {
                        "type": "title",
                        "level": new_level,
                        "title": new_title.name,
                        "description": new_title.description,
                    }
                )

            xp_needed = self.get_xp_for_level(new_level + 1)

            log.success(f"🎊 LEVEL UP! Level {new_level} reached!")

        new_title_text = (
            self._get_title_for_level(new_level).name
            if leveled_up
            else prog["current_title"]
        )

        cursor.execute(
            """
            UPDATE progression 
            SET current_xp = ?, total_xp = ?, level = ?, current_title = ?, updated_at = ?
            WHERE id = 1
        """,
            (
                current_xp,
                total_xp,
                new_level,
                new_title_text,
                datetime.now().isoformat(),
            ),
        )

        cursor.execute(
            """
            INSERT INTO xp_history (action_type, xp_gained, session_id, timestamp)
            VALUES (?, ?, ?, ?)
        """,
            (action_type, xp_gained, session_id, datetime.now().isoformat()),
        )

        self.conn.commit()

        return {
            "leveled_up": leveled_up,
            "xp_gained": xp_gained,
            "current_xp": current_xp,
            "xp_needed": xp_needed,
            "current_level": new_level,
            "current_title": new_title_text,
            "rewards": level_rewards,
        }

    def _get_title_for_level(self, level: int) -> Optional[Title]:
        applicable_titles = [t for t in self.TITLES if t.level <= level]
        return (
            max(applicable_titles, key=lambda t: t.level)
            if applicable_titles
            else self.TITLES[0]
        )

    def get_current_status(self) -> Dict:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM progression WHERE id = 1")
        prog = cursor.fetchone()

        if not prog:
            return {}

        current_level = prog["level"]
        xp_needed = self.get_xp_for_level(current_level + 1)

        cursor.execute("SELECT * FROM badges WHERE is_unlocked = 1")
        badges = [dict(row) for row in cursor.fetchall()]

        return {
            "level": current_level,
            "current_xp": prog["current_xp"],
            "total_xp": prog["total_xp"],
            "xp_needed": xp_needed,
            "current_title": prog["current_title"],
            "badges": badges,
            "progress_percentage": (
                (prog["current_xp"] / xp_needed * 100) if xp_needed > 0 else 0
            ),
        }

    def check_and_unlock_badges(self, stats: Dict) -> List[Dict]:
        return []

    def render_progress_bar(self, current: int, needed: int, width: int = 20) -> str:
        percentage = (current / needed) if needed > 0 else 0
        filled = int(width * percentage)
        empty = width - filled

        bar = "█" * filled + "░" * empty
        return f"[{bar}] {percentage*100:.1f}%"

    @staticmethod
    def get_xp_value(action_type: str) -> int:
        return ProgressionSystem.XP_REWARDS.get(action_type, 0)

    def __del__(self):
        if hasattr(self, "conn"):
            try:
                self.conn.close()
            except:
                pass
