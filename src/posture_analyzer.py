import time
from collections import deque
from dataclasses import dataclass
from typing import Optional, Tuple, List
from enum import Enum
import numpy as np

class PostureStatus(Enum):
    GOOD = "good"
    WARNING = "warning"
    POOR = "poor"

@dataclass
class PostureMetrics:
    head_pitch: float
    head_yaw: float
    head_roll: float
    distance_from_screen: float
    posture_score: float
    status: PostureStatus
    issues: List[str]
    bad_posture_duration: float

class PostureAnalyzer:
    IDEAL_DISTANCE_MIN = 30
    IDEAL_DISTANCE_MAX = 50
    WARNING_DISTANCE_MIN = 20
    CRITICAL_DISTANCE_MIN = 10
    HEAD_TILT_WARNING = 20
    HEAD_TILT_CRITICAL = 25
    FORWARD_HEAD_WARNING = 20
    FORWARD_HEAD_CRITICAL = 35
    HEAD_ROLL_WARNING = 15
    HEAD_ROLL_CRITICAL = 25
    BAD_POSTURE_ALERT_THRESHOLD = 30
    
    def __init__(self):
        self.pitch_history: deque = deque(maxlen=30)
        self.yaw_history: deque = deque(maxlen=30)
        self.roll_history: deque = deque(maxlen=30)
        self.distance_history: deque = deque(maxlen=30)
        self.baseline_pitch: Optional[float] = None
        self.baseline_yaw: Optional[float] = None
        self.baseline_distance: Optional[float] = None
        self.calibration_data: List[Tuple[float, float, float, float]] = []
        self.is_calibrating = True
        self.calibration_start_time = time.time()
        self.calibration_duration = 30
        self.bad_posture_start_time: Optional[float] = None
        self.current_bad_posture_duration = 0.0
        self.total_bad_posture_time = 0.0
        
    def update(self, head_pose: Tuple[float, float, float], distance: float):
        pitch, yaw, roll = head_pose
        current_time = time.time()
        
        self.pitch_history.append(pitch)
        self.yaw_history.append(yaw)
        self.roll_history.append(roll)
        self.distance_history.append(distance)
        
        if self.is_calibrating:
            self.calibration_data.append((pitch, yaw, roll, distance))
            if current_time - self.calibration_start_time >= self.calibration_duration:
                self._complete_calibration()
        
        status = self.get_status()
        if status != PostureStatus.GOOD:
            if self.bad_posture_start_time is None:
                self.bad_posture_start_time = current_time
            self.current_bad_posture_duration = current_time - self.bad_posture_start_time
        else:
            if self.bad_posture_start_time:
                self.total_bad_posture_time += self.current_bad_posture_duration
            self.bad_posture_start_time = None
            self.current_bad_posture_duration = 0.0
    
    def _complete_calibration(self):
        if len(self.calibration_data) >= 10:
            pitches = [d[0] for d in self.calibration_data]
            yaws = [d[1] for d in self.calibration_data]
            distances = [d[3] for d in self.calibration_data]
            
            self.baseline_pitch = float(np.median(pitches))
            self.baseline_yaw = float(np.median(yaws))
            self.baseline_distance = float(np.median(distances))
        
        self.is_calibrating = False
        self.calibration_data = []
    
    def get_smoothed_values(self) -> Tuple[float, float, float, float]:
        pitch = float(np.mean(list(self.pitch_history))) if self.pitch_history else 0.0
        yaw = float(np.mean(list(self.yaw_history))) if self.yaw_history else 0.0
        roll = float(np.mean(list(self.roll_history))) if self.roll_history else 0.0
        distance = float(np.mean(list(self.distance_history))) if self.distance_history else 50.0
        
        return pitch, yaw, roll, distance
    
    def calculate_posture_score(self) -> float:
        pitch, yaw, roll, distance = self.get_smoothed_values()
        score = 100.0
        
        pitch_deviation = abs(pitch - (self.baseline_pitch or 0))
        if pitch_deviation > self.FORWARD_HEAD_CRITICAL:
            score -= 30
        elif pitch_deviation > self.FORWARD_HEAD_WARNING:
            score -= 15
        
        roll_deviation = abs(roll)
        if roll_deviation > self.HEAD_ROLL_CRITICAL:
            score -= 25
        elif roll_deviation > self.HEAD_ROLL_WARNING:
            score -= 12
        
        yaw_deviation = abs(yaw - (self.baseline_yaw or 0))
        if yaw_deviation > self.HEAD_TILT_CRITICAL:
            score -= 20
        elif yaw_deviation > self.HEAD_TILT_WARNING:
            score -= 10
        
        if distance < self.CRITICAL_DISTANCE_MIN:
            score -= 30
        elif distance < self.WARNING_DISTANCE_MIN:
            score -= 15
        elif distance < self.IDEAL_DISTANCE_MIN:
            score -= 5
        elif distance > self.IDEAL_DISTANCE_MAX + 30:
            score -= 10
        
        if self.current_bad_posture_duration > 120:
            score -= 15
        elif self.current_bad_posture_duration > 60:
            score -= 8
        
        return max(0, score)
    
    def get_issues(self) -> List[str]:
        pitch, yaw, roll, distance = self.get_smoothed_values()
        issues = []
        
        pitch_deviation = pitch - (self.baseline_pitch or 0)
        if pitch_deviation > self.FORWARD_HEAD_WARNING:
            issues.append("Forward head posture detected")
        elif pitch_deviation < -self.FORWARD_HEAD_WARNING:
            issues.append("Head tilted back too far")
        
        if abs(roll) > self.HEAD_ROLL_WARNING:
            direction = "right" if roll > 0 else "left"
            issues.append(f"Head tilted to the {direction}")
        
        yaw_deviation = abs(yaw - (self.baseline_yaw or 0))
        if yaw_deviation > self.HEAD_TILT_WARNING:
            direction = "right" if yaw > 0 else "left"
            issues.append(f"Head turned to the {direction}")
        
        if distance < self.WARNING_DISTANCE_MIN:
            issues.append(f"Too close to screen ({distance:.0f}cm)")
        elif distance < self.IDEAL_DISTANCE_MIN:
            issues.append(f"Consider moving back slightly ({distance:.0f}cm)")
        
        if self.current_bad_posture_duration > 60:
            issues.append(f"Poor posture for {self.current_bad_posture_duration:.0f} seconds")
        
        return issues
    
    def get_status(self) -> PostureStatus:
        score = self.calculate_posture_score()
        
        if score >= 70:
            return PostureStatus.GOOD
        elif score >= 40:
            return PostureStatus.WARNING
        return PostureStatus.POOR
    
    def get_metrics(self) -> PostureMetrics:
        pitch, yaw, roll, distance = self.get_smoothed_values()
        
        return PostureMetrics(
            head_pitch=pitch,
            head_yaw=yaw,
            head_roll=roll,
            distance_from_screen=distance,
            posture_score=self.calculate_posture_score(),
            status=self.get_status(),
            issues=self.get_issues(),
            bad_posture_duration=self.current_bad_posture_duration
        )
    
    def get_recommendation(self) -> Optional[str]:
        metrics = self.get_metrics()
        
        if metrics.status == PostureStatus.POOR:
            if metrics.distance_from_screen < self.WARNING_DISTANCE_MIN:
                return "You're too close to the screen. Move back to at least 50cm for better eye and posture health."
            if "Forward head posture" in str(metrics.issues):
                return "Your head is leaning forward. Sit back and align your ears with your shoulders."
            if metrics.bad_posture_duration > 60:
                return "You've had poor posture for over a minute. Take a moment to sit up straight and reset your position."
            return "Your posture needs attention. Sit up straight with your back against the chair."
        
        elif metrics.status == PostureStatus.WARNING:
            issues = metrics.issues
            if issues:
                return f"Minor posture issue: {issues[0]}. Make a small adjustment."
        
        return None
    
    def should_alert(self) -> bool:
        return (
            self.current_bad_posture_duration >= self.BAD_POSTURE_ALERT_THRESHOLD and
            self.get_status() != PostureStatus.GOOD
        )
