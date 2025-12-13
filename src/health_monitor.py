import time
from dataclasses import dataclass
from typing import Optional, Callable
from enum import Enum

from .vision_engine import VisionEngine, FaceLandmarks
from .eye_tracker import EyeTracker, EyeHealthStatus
from .posture_analyzer import PostureAnalyzer, PostureStatus
from .alert_system import AlertSystem, AlertType, AlertSeverity, create_eye_strain_alert, create_posture_alert, create_break_alert
from .screen_time_tracker import ScreenTimeTracker, BreakType
from .data_logger import DataLogger

class OverallHealthStatus(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    NEEDS_ATTENTION = "needs_attention"

@dataclass
class HealthState:
    overall_status: OverallHealthStatus
    overall_score: float
    eye_metrics: dict
    posture_metrics: dict
    screen_time_stats: dict
    active_alerts: list
    is_calibrating: bool
    is_user_present: bool

class HealthMonitor:
    def __init__(self):
        self.vision_engine = VisionEngine()
        self.eye_tracker = EyeTracker()
        self.posture_analyzer = PostureAnalyzer()
        self.alert_system = AlertSystem()
        self.screen_time_tracker = ScreenTimeTracker()
        self.data_logger = DataLogger()
        
        self.is_running = False
        self.last_frame = None
        self.last_landmarks = None
        self.frame_callback: Optional[Callable] = None
        self.alert_callback: Optional[Callable] = None
        
        self.alert_system.register_callback(self._on_alert)
    
    def _on_alert(self, alert):
        if self.alert_callback:
            self.alert_callback(alert)
    
    def start(self, camera_index: int = 0) -> bool:
        if not self.vision_engine.start_camera(camera_index):
            return False
        self.is_running = True
        return True
    
    def stop(self):
        self.is_running = False
        self.vision_engine.stop_camera()
        self.data_logger.save_daily_summary(self.screen_time_tracker.get_daily_summary())
    
    def process_frame(self) -> Optional[HealthState]:
        if not self.is_running:
            return None
        
        frame = self.vision_engine.get_frame()
        if frame is None:
            return None
        
        self.last_frame = frame
        landmarks = self.vision_engine.process_frame(frame)
        self.last_landmarks = landmarks
        
        face_detected = landmarks is not None
        self.screen_time_tracker.update(face_detected)
        
        if not face_detected:
            return HealthState(
                overall_status=OverallHealthStatus.GOOD,
                overall_score=100,
                eye_metrics={},
                posture_metrics={},
                screen_time_stats=self.screen_time_tracker.get_statistics(),
                active_alerts=self.alert_system.get_active_alerts(),
                is_calibrating=False,
                is_user_present=False
            )
        
        left_ear = self.vision_engine.calculate_eye_aspect_ratio(landmarks, "left")
        right_ear = self.vision_engine.calculate_eye_aspect_ratio(landmarks, "right")
        self.eye_tracker.update(left_ear, right_ear)
        
        head_pose = self.vision_engine.calculate_head_pose(landmarks)
        distance = self.vision_engine.estimate_face_distance(landmarks)
        self.posture_analyzer.update(head_pose, distance)
        
        eye_metrics = self.eye_tracker.get_metrics()
        posture_metrics = self.posture_analyzer.get_metrics()
        screen_stats = self.screen_time_tracker.get_statistics()
        
        self._check_and_send_alerts(eye_metrics, posture_metrics, screen_stats)
        
        self._log_data(eye_metrics, posture_metrics, screen_stats)
        
        overall_score = self._calculate_overall_score(eye_metrics, posture_metrics)
        overall_status = self._determine_overall_status(overall_score)
        
        is_calibrating = self.eye_tracker.is_calibrating or self.posture_analyzer.is_calibrating
        
        return HealthState(
            overall_status=overall_status,
            overall_score=overall_score,
            eye_metrics={
                "blink_rate": eye_metrics.blink_rate,
                "eye_strain_score": eye_metrics.eye_strain_score,
                "status": eye_metrics.status.value,
                "time_since_blink": eye_metrics.time_since_last_blink,
                "current_ear": eye_metrics.current_ear
            },
            posture_metrics={
                "posture_score": posture_metrics.posture_score,
                "status": posture_metrics.status.value,
                "distance": posture_metrics.distance_from_screen,
                "head_pitch": posture_metrics.head_pitch,
                "head_roll": posture_metrics.head_roll,
                "issues": posture_metrics.issues,
                "bad_posture_duration": posture_metrics.bad_posture_duration
            },
            screen_time_stats=screen_stats,
            active_alerts=[
                {
                    "type": a.alert_type.value,
                    "severity": a.severity.value,
                    "title": a.title,
                    "message": a.message,
                    "recommendation": a.recommendation
                }
                for a in self.alert_system.get_active_alerts()
            ],
            is_calibrating=is_calibrating,
            is_user_present=True
        )
    
    def _check_and_send_alerts(self, eye_metrics, posture_metrics, screen_stats):
        if eye_metrics.status == EyeHealthStatus.CRITICAL:
            recommendation = self.eye_tracker.get_recommendation()
            alert_data = create_eye_strain_alert(
                AlertSeverity.CRITICAL,
                f"Your eye strain score is {eye_metrics.eye_strain_score:.0f}%",
                recommendation or "Take a break and rest your eyes"
            )
            self.alert_system.create_alert(**alert_data)
        elif eye_metrics.status == EyeHealthStatus.WARNING:
            recommendation = self.eye_tracker.get_recommendation()
            alert_data = create_eye_strain_alert(
                AlertSeverity.WARNING,
                f"Your blink rate is lower than normal ({eye_metrics.blink_rate:.1f} blinks/min)",
                recommendation or "Try to blink more often"
            )
            self.alert_system.create_alert(**alert_data)
        
        if self.posture_analyzer.should_alert():
            recommendation = self.posture_analyzer.get_recommendation()
            severity = AlertSeverity.CRITICAL if posture_metrics.status == PostureStatus.POOR else AlertSeverity.WARNING
            alert_data = create_posture_alert(
                severity,
                f"Poor posture detected for {posture_metrics.bad_posture_duration:.0f} seconds",
                recommendation or "Adjust your sitting position"
            )
            self.alert_system.create_alert(**alert_data)
        
        break_rec = self.screen_time_tracker.get_break_recommendation()
        if break_rec:
            severity = AlertSeverity.WARNING if break_rec.break_type == BreakType.LONG else AlertSeverity.INFO
            alert_data = create_break_alert(
                severity,
                break_rec.reason,
                "\n".join(break_rec.exercises[:3])
            )
            self.alert_system.create_alert(**alert_data)
        
        self.alert_system.check_escalations()
    
    def _log_data(self, eye_metrics, posture_metrics, screen_stats):
        self.data_logger.log_snapshot(
            blink_rate=eye_metrics.blink_rate,
            eye_strain_score=eye_metrics.eye_strain_score,
            posture_score=posture_metrics.posture_score,
            distance=posture_metrics.distance_from_screen,
            head_pitch=posture_metrics.head_pitch,
            head_roll=posture_metrics.head_roll,
            continuous_work_minutes=screen_stats["continuous_work_minutes"],
            is_present=True
        )
    
    def _calculate_overall_score(self, eye_metrics, posture_metrics) -> float:
        eye_score = 100 - eye_metrics.eye_strain_score
        posture_score = posture_metrics.posture_score
        
        overall = (eye_score * 0.5) + (posture_score * 0.5)
        return max(0, min(100, overall))
    
    def _determine_overall_status(self, score: float) -> OverallHealthStatus:
        if score >= 85:
            return OverallHealthStatus.EXCELLENT
        elif score >= 70:
            return OverallHealthStatus.GOOD
        elif score >= 50:
            return OverallHealthStatus.FAIR
        return OverallHealthStatus.NEEDS_ATTENTION
    
    def get_annotated_frame(self):
        if self.last_frame is None:
            return None
        
        if self.last_landmarks:
            return self.vision_engine.draw_landmarks(self.last_frame, self.last_landmarks)
        return self.last_frame
    
    def acknowledge_alert(self, alert_index: int = 0):
        alerts = self.alert_system.get_active_alerts()
        if 0 <= alert_index < len(alerts):
            self.alert_system.acknowledge_alert(alerts[alert_index])
    
    def acknowledge_all_alerts(self):
        self.alert_system.acknowledge_all()
    
    def record_break(self, break_type: BreakType):
        self.screen_time_tracker.record_break_taken(break_type)
    
    def pause_alerts(self, minutes: int):
        self.alert_system.pause_alerts(minutes * 60)
    
    def get_trend_analysis(self, days: int = 7):
        return self.data_logger.get_trend_analysis(days)
    
    def get_baselines(self):
        return self.data_logger.get_baselines()
