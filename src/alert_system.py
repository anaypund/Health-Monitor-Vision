import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, List, Callable
from enum import Enum
import threading

class AlertType(Enum):
    EYE_STRAIN = "eye_strain"
    POSTURE = "posture"
    BREAK_NEEDED = "break_needed"
    DISTANCE = "distance"
    BLINK_REMINDER = "blink_reminder"

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class Alert:
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    recommendation: str
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False
    escalation_level: int = 0

class AlertSystem:
    COOLDOWN_PERIODS = {
        AlertType.EYE_STRAIN: 120,
        AlertType.POSTURE: 60,
        AlertType.BREAK_NEEDED: 300,
        AlertType.DISTANCE: 30,
        AlertType.BLINK_REMINDER: 45,
    }
    
    MAX_ESCALATION = 3
    ESCALATION_INTERVAL = 60
    
    def __init__(self):
        self.active_alerts: List[Alert] = []
        self.alert_history: deque = deque(maxlen=100)
        self.last_alert_times: dict = {t: 0 for t in AlertType}
        self.escalation_counts: dict = {t: 0 for t in AlertType}
        self.pending_escalations: dict = {}
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        self.is_paused = False
        self.pause_until: Optional[float] = None
        self.alerts_today = 0
        self.last_reset_date = time.strftime("%Y-%m-%d")
        
    def register_callback(self, callback: Callable[[Alert], None]):
        self.alert_callbacks.append(callback)
    
    def _notify_callbacks(self, alert: Alert):
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"Alert callback error: {e}")
    
    def can_send_alert(self, alert_type: AlertType) -> bool:
        if self.is_paused:
            if self.pause_until and time.time() >= self.pause_until:
                self.is_paused = False
                self.pause_until = None
            else:
                return False
        
        current_time = time.time()
        last_time = self.last_alert_times.get(alert_type, 0)
        cooldown = self.COOLDOWN_PERIODS.get(alert_type, 60)
        
        return (current_time - last_time) >= cooldown
    
    def create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        recommendation: str
    ) -> Optional[Alert]:
        if not self.can_send_alert(alert_type):
            return None
        
        current_date = time.strftime("%Y-%m-%d")
        if current_date != self.last_reset_date:
            self.alerts_today = 0
            self.last_reset_date = current_date
        
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            recommendation=recommendation,
            escalation_level=self.escalation_counts.get(alert_type, 0)
        )
        
        self.active_alerts.append(alert)
        self.alert_history.append(alert)
        self.last_alert_times[alert_type] = time.time()
        self.alerts_today += 1
        
        self._notify_callbacks(alert)
        
        if severity in [AlertSeverity.WARNING, AlertSeverity.CRITICAL]:
            self._schedule_escalation(alert_type)
        
        return alert
    
    def _schedule_escalation(self, alert_type: AlertType):
        current_count = self.escalation_counts.get(alert_type, 0)
        if current_count < self.MAX_ESCALATION:
            self.pending_escalations[alert_type] = time.time() + self.ESCALATION_INTERVAL
    
    def check_escalations(self):
        current_time = time.time()
        escalations_to_process = []
        
        for alert_type, escalation_time in list(self.pending_escalations.items()):
            if current_time >= escalation_time:
                unacknowledged = [
                    a for a in self.active_alerts 
                    if a.alert_type == alert_type and not a.acknowledged
                ]
                if unacknowledged:
                    escalations_to_process.append(alert_type)
                del self.pending_escalations[alert_type]
        
        for alert_type in escalations_to_process:
            self.escalation_counts[alert_type] = self.escalation_counts.get(alert_type, 0) + 1
    
    def acknowledge_alert(self, alert: Alert):
        alert.acknowledged = True
        if alert.alert_type in self.pending_escalations:
            del self.pending_escalations[alert.alert_type]
        self.escalation_counts[alert.alert_type] = 0
        
        self.active_alerts = [a for a in self.active_alerts if a != alert]
    
    def acknowledge_all(self):
        for alert in self.active_alerts:
            alert.acknowledged = True
        self.active_alerts = []
        self.pending_escalations = {}
        for alert_type in self.escalation_counts:
            self.escalation_counts[alert_type] = 0
    
    def pause_alerts(self, duration_seconds: int):
        self.is_paused = True
        self.pause_until = time.time() + duration_seconds
    
    def resume_alerts(self):
        self.is_paused = False
        self.pause_until = None
    
    def get_active_alerts(self) -> List[Alert]:
        return [a for a in self.active_alerts if not a.acknowledged]
    
    def get_alert_summary(self) -> dict:
        return {
            "total_today": self.alerts_today,
            "active_count": len(self.get_active_alerts()),
            "is_paused": self.is_paused,
            "pause_remaining": max(0, (self.pause_until or 0) - time.time()) if self.is_paused else 0,
            "by_type": {
                t.value: len([a for a in self.alert_history if a.alert_type == t])
                for t in AlertType
            }
        }


def create_eye_strain_alert(severity: AlertSeverity, message: str, recommendation: str) -> dict:
    titles = {
        AlertSeverity.INFO: "Eye Care Reminder",
        AlertSeverity.WARNING: "Eye Strain Detected",
        AlertSeverity.CRITICAL: "High Eye Strain Warning"
    }
    return {
        "alert_type": AlertType.EYE_STRAIN,
        "severity": severity,
        "title": titles[severity],
        "message": message,
        "recommendation": recommendation
    }


def create_posture_alert(severity: AlertSeverity, message: str, recommendation: str) -> dict:
    titles = {
        AlertSeverity.INFO: "Posture Tip",
        AlertSeverity.WARNING: "Posture Check",
        AlertSeverity.CRITICAL: "Posture Alert"
    }
    return {
        "alert_type": AlertType.POSTURE,
        "severity": severity,
        "title": titles[severity],
        "message": message,
        "recommendation": recommendation
    }


def create_break_alert(severity: AlertSeverity, message: str, recommendation: str) -> dict:
    return {
        "alert_type": AlertType.BREAK_NEEDED,
        "severity": severity,
        "title": "Break Reminder",
        "message": message,
        "recommendation": recommendation
    }
