import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from enum import Enum

class EyeHealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"

@dataclass
class BlinkEvent:
    timestamp: float
    duration: float

@dataclass
class EyeHealthMetrics:
    blink_rate: float
    avg_blink_duration: float
    eye_strain_score: float
    status: EyeHealthStatus
    time_since_last_blink: float
    current_ear: float

class EyeTracker:
    HEALTHY_BLINK_RATE_MIN = 12
    HEALTHY_BLINK_RATE_MAX = 20
    WARNING_BLINK_RATE = 8
    CRITICAL_BLINK_RATE = 5
    EAR_BLINK_THRESHOLD = 0.21
    MIN_BLINK_DURATION = 0.05
    MAX_BLINK_DURATION = 0.5
    BLINK_HISTORY_WINDOW = 60
    
    def __init__(self):
        self.blink_history: deque = deque(maxlen=100)
        self.ear_history: deque = deque(maxlen=30)
        self.is_eye_closed = False
        self.eye_close_start_time: Optional[float] = None
        self.last_blink_time: float = time.time()
        self.baseline_blink_rate: Optional[float] = None
        self.calibration_blinks: List[float] = []
        self.is_calibrating = True
        self.calibration_start_time = time.time()
        self.calibration_duration = 120
        
    def update(self, left_ear: float, right_ear: float) -> Optional[BlinkEvent]:
        current_time = time.time()
        avg_ear = (left_ear + right_ear) / 2
        self.ear_history.append(avg_ear)
        
        blink_event = None
        
        if avg_ear < self.EAR_BLINK_THRESHOLD:
            if not self.is_eye_closed:
                self.is_eye_closed = True
                self.eye_close_start_time = current_time
        else:
            if self.is_eye_closed and self.eye_close_start_time:
                blink_duration = current_time - self.eye_close_start_time
                
                if self.MIN_BLINK_DURATION <= blink_duration <= self.MAX_BLINK_DURATION:
                    blink_event = BlinkEvent(
                        timestamp=current_time,
                        duration=blink_duration
                    )
                    self.blink_history.append(blink_event)
                    self.last_blink_time = current_time
                    
                    if self.is_calibrating:
                        self.calibration_blinks.append(current_time)
                
                self.is_eye_closed = False
                self.eye_close_start_time = None
        
        if self.is_calibrating:
            if current_time - self.calibration_start_time >= self.calibration_duration:
                self._complete_calibration()
        
        return blink_event
    
    def _complete_calibration(self):
        if len(self.calibration_blinks) >= 5:
            duration_minutes = self.calibration_duration / 60
            self.baseline_blink_rate = len(self.calibration_blinks) / duration_minutes
        self.is_calibrating = False
        self.calibration_blinks = []
    
    def get_current_blink_rate(self) -> float:
        current_time = time.time()
        window_start = current_time - self.BLINK_HISTORY_WINDOW
        
        recent_blinks = [b for b in self.blink_history if b.timestamp >= window_start]
        
        if len(recent_blinks) < 2:
            return 0.0
        
        duration_minutes = self.BLINK_HISTORY_WINDOW / 60
        return len(recent_blinks) / duration_minutes
    
    def calculate_eye_strain_score(self) -> float:
        blink_rate = self.get_current_blink_rate()
        time_since_blink = time.time() - self.last_blink_time
        avg_ear = sum(self.ear_history) / len(self.ear_history) if self.ear_history else 0.25
        
        score = 0.0
        
        if blink_rate < self.CRITICAL_BLINK_RATE:
            score += 40
        elif blink_rate < self.WARNING_BLINK_RATE:
            score += 25
        elif blink_rate < self.HEALTHY_BLINK_RATE_MIN:
            score += 10
        
        if time_since_blink > 30:
            score += 30
        elif time_since_blink > 15:
            score += 15
        elif time_since_blink > 10:
            score += 5
        
        if avg_ear < 0.22:
            score += 20
        elif avg_ear < 0.24:
            score += 10
        
        if self.baseline_blink_rate:
            rate_deviation = (self.baseline_blink_rate - blink_rate) / self.baseline_blink_rate
            if rate_deviation > 0.5:
                score += 15
            elif rate_deviation > 0.3:
                score += 8
        
        return min(100, score)
    
    def get_health_status(self) -> EyeHealthStatus:
        score = self.calculate_eye_strain_score()
        
        if score >= 60:
            return EyeHealthStatus.CRITICAL
        elif score >= 30:
            return EyeHealthStatus.WARNING
        return EyeHealthStatus.HEALTHY
    
    def get_metrics(self) -> EyeHealthMetrics:
        blink_rate = self.get_current_blink_rate()
        
        recent_blinks = list(self.blink_history)[-20:]
        avg_duration = sum(b.duration for b in recent_blinks) / len(recent_blinks) if recent_blinks else 0.0
        
        avg_ear = sum(self.ear_history) / len(self.ear_history) if self.ear_history else 0.25
        
        return EyeHealthMetrics(
            blink_rate=blink_rate,
            avg_blink_duration=avg_duration,
            eye_strain_score=self.calculate_eye_strain_score(),
            status=self.get_health_status(),
            time_since_last_blink=time.time() - self.last_blink_time,
            current_ear=avg_ear
        )
    
    def get_recommendation(self) -> Optional[str]:
        metrics = self.get_metrics()
        
        if metrics.status == EyeHealthStatus.CRITICAL:
            if metrics.time_since_last_blink > 20:
                return "You haven't blinked in a while. Please blink now and consider the 20-20-20 rule: look at something 20 feet away for 20 seconds."
            return "Your eyes are showing signs of strain. Take a short break and look away from the screen."
        
        elif metrics.status == EyeHealthStatus.WARNING:
            if metrics.blink_rate < self.WARNING_BLINK_RATE:
                return "Your blink rate is lower than normal. Try to blink more consciously."
            return "Your eyes may be getting tired. Consider resting them soon."
        
        return None
