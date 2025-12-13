import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum
import json
from datetime import datetime, timedelta

class BreakType(Enum):
    MICRO = "micro"
    SHORT = "short"
    LONG = "long"

@dataclass
class WorkSession:
    start_time: float
    end_time: Optional[float] = None
    breaks_taken: int = 0
    
    @property
    def duration(self) -> float:
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def duration_minutes(self) -> float:
        return self.duration / 60

@dataclass
class BreakRecommendation:
    break_type: BreakType
    duration_seconds: int
    reason: str
    exercises: List[str]

class ScreenTimeTracker:
    MICRO_BREAK_INTERVAL = 20 * 60
    SHORT_BREAK_INTERVAL = 45 * 60
    LONG_BREAK_INTERVAL = 90 * 60
    MICRO_BREAK_DURATION = 20
    SHORT_BREAK_DURATION = 5 * 60
    LONG_BREAK_DURATION = 15 * 60
    IDLE_THRESHOLD = 30
    ACTIVE_THRESHOLD = 5
    
    def __init__(self):
        self.current_session: Optional[WorkSession] = None
        self.sessions_today: List[WorkSession] = []
        self.last_activity_time = time.time()
        self.is_user_present = False
        self.continuous_work_time = 0.0
        self.last_micro_break = time.time()
        self.last_short_break = time.time()
        self.last_long_break = time.time()
        self.total_screen_time_today = 0.0
        self.last_reset_date = datetime.now().date()
        self.idle_periods: deque = deque(maxlen=50)
        self.break_compliance_history: deque = deque(maxlen=20)
        
    def update(self, face_detected: bool):
        current_time = time.time()
        
        self._check_daily_reset()
        
        if face_detected:
            if not self.is_user_present:
                self._start_session()
            self.is_user_present = True
            self.last_activity_time = current_time
            
            if self.current_session:
                time_since_start = current_time - self.current_session.start_time
                self.continuous_work_time = time_since_start
        else:
            idle_time = current_time - self.last_activity_time
            if idle_time >= self.IDLE_THRESHOLD:
                if self.is_user_present:
                    self._end_session()
                    self.idle_periods.append({
                        "start": self.last_activity_time,
                        "duration": idle_time
                    })
                self.is_user_present = False
    
    def _check_daily_reset(self):
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.sessions_today = []
            self.total_screen_time_today = 0.0
            self.last_reset_date = today
    
    def _start_session(self):
        if self.current_session:
            self._end_session()
        
        self.current_session = WorkSession(start_time=time.time())
        self.continuous_work_time = 0.0
    
    def _end_session(self):
        if self.current_session:
            self.current_session.end_time = time.time()
            self.sessions_today.append(self.current_session)
            self.total_screen_time_today += self.current_session.duration
            self.current_session = None
    
    def record_break_taken(self, break_type: BreakType):
        current_time = time.time()
        
        if break_type == BreakType.MICRO:
            self.last_micro_break = current_time
        elif break_type == BreakType.SHORT:
            self.last_short_break = current_time
            self.last_micro_break = current_time
        else:
            self.last_long_break = current_time
            self.last_short_break = current_time
            self.last_micro_break = current_time
        
        if self.current_session:
            self.current_session.breaks_taken += 1
        
        self.break_compliance_history.append({
            "type": break_type.value,
            "timestamp": current_time,
            "work_duration": self.continuous_work_time
        })
        
        self.continuous_work_time = 0.0
    
    def get_break_recommendation(self) -> Optional[BreakRecommendation]:
        current_time = time.time()
        
        time_since_long = current_time - self.last_long_break
        if time_since_long >= self.LONG_BREAK_INTERVAL:
            return BreakRecommendation(
                break_type=BreakType.LONG,
                duration_seconds=self.LONG_BREAK_DURATION,
                reason=f"You've been working for {time_since_long/60:.0f} minutes. Time for a longer break.",
                exercises=[
                    "Stand up and stretch your whole body",
                    "Take a short walk",
                    "Do some light exercises or yoga",
                    "Get a healthy snack and water",
                    "Look out a window at distant objects"
                ]
            )
        
        time_since_short = current_time - self.last_short_break
        if time_since_short >= self.SHORT_BREAK_INTERVAL:
            return BreakRecommendation(
                break_type=BreakType.SHORT,
                duration_seconds=self.SHORT_BREAK_DURATION,
                reason=f"You've been working for {time_since_short/60:.0f} minutes. Take a short break.",
                exercises=[
                    "Stand up and stretch your arms overhead",
                    "Roll your shoulders backwards 10 times",
                    "Tilt your head side to side gently",
                    "Take 5 deep breaths",
                    "Walk around for a minute"
                ]
            )
        
        time_since_micro = current_time - self.last_micro_break
        if time_since_micro >= self.MICRO_BREAK_INTERVAL:
            return BreakRecommendation(
                break_type=BreakType.MICRO,
                duration_seconds=self.MICRO_BREAK_DURATION,
                reason="Time for the 20-20-20 rule: Look at something 20 feet away for 20 seconds.",
                exercises=[
                    "Look at a distant object for 20 seconds",
                    "Blink 20 times slowly",
                    "Close your eyes and take 3 deep breaths"
                ]
            )
        
        return None
    
    def get_statistics(self) -> dict:
        current_session_time = 0
        if self.current_session:
            current_session_time = self.current_session.duration
        
        total_today = self.total_screen_time_today + current_session_time
        
        session_durations = [s.duration_minutes for s in self.sessions_today]
        if self.current_session:
            session_durations.append(self.current_session.duration_minutes)
        
        avg_session = sum(session_durations) / len(session_durations) if session_durations else 0
        
        total_breaks = sum(s.breaks_taken for s in self.sessions_today)
        if self.current_session:
            total_breaks += self.current_session.breaks_taken
        
        return {
            "total_screen_time_today_minutes": total_today / 60,
            "current_session_minutes": current_session_time / 60,
            "continuous_work_minutes": self.continuous_work_time / 60,
            "sessions_count": len(self.sessions_today) + (1 if self.current_session else 0),
            "average_session_minutes": avg_session,
            "breaks_taken_today": total_breaks,
            "is_user_present": self.is_user_present,
            "time_until_micro_break": max(0, self.MICRO_BREAK_INTERVAL - (time.time() - self.last_micro_break)),
            "time_until_short_break": max(0, self.SHORT_BREAK_INTERVAL - (time.time() - self.last_short_break)),
            "time_until_long_break": max(0, self.LONG_BREAK_INTERVAL - (time.time() - self.last_long_break))
        }
    
    def get_daily_summary(self) -> dict:
        stats = self.get_statistics()
        
        compliance_rate = 0
        if self.break_compliance_history:
            recent = list(self.break_compliance_history)
            on_time = sum(1 for b in recent if b["work_duration"] < self.SHORT_BREAK_INTERVAL * 1.2)
            compliance_rate = on_time / len(recent) * 100
        
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total_hours": stats["total_screen_time_today_minutes"] / 60,
            "sessions": stats["sessions_count"],
            "breaks_taken": stats["breaks_taken_today"],
            "break_compliance_rate": compliance_rate,
            "recommendations": self._generate_daily_recommendations(stats)
        }
    
    def _generate_daily_recommendations(self, stats: dict) -> List[str]:
        recommendations = []
        
        if stats["total_screen_time_today_minutes"] > 480:
            recommendations.append("You've had a long screen day. Consider ending work soon and resting your eyes.")
        
        if stats["average_session_minutes"] > 60:
            recommendations.append("Your average session length is quite long. Try taking more frequent breaks.")
        
        if stats["breaks_taken_today"] < stats["total_screen_time_today_minutes"] / 30:
            recommendations.append("You could benefit from more frequent breaks throughout the day.")
        
        return recommendations
