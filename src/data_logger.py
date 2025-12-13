import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
import pandas as pd
from pathlib import Path

@dataclass
class HealthSnapshot:
    timestamp: str
    blink_rate: float
    eye_strain_score: float
    posture_score: float
    distance_from_screen: float
    head_pitch: float
    head_roll: float
    continuous_work_minutes: float
    is_user_present: bool

class DataLogger:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.snapshots_dir = self.data_dir / "snapshots"
        self.snapshots_dir.mkdir(exist_ok=True)
        
        self.summaries_dir = self.data_dir / "summaries"
        self.summaries_dir.mkdir(exist_ok=True)
        
        self.current_day_snapshots: List[HealthSnapshot] = []
        self.last_snapshot_time = 0
        self.snapshot_interval = 60
        
        self.baseline_data = self._load_baselines()
    
    def _get_today_filename(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")
    
    def _load_baselines(self) -> Dict[str, Any]:
        baseline_file = self.data_dir / "baselines.json"
        if baseline_file.exists():
            try:
                with open(baseline_file, "r") as f:
                    return json.load(f)
            except:
                pass
        return {
            "blink_rate": None,
            "posture_baseline": None,
            "typical_distance": None,
            "samples_count": 0
        }
    
    def _save_baselines(self):
        baseline_file = self.data_dir / "baselines.json"
        with open(baseline_file, "w") as f:
            json.dump(self.baseline_data, f, indent=2)
    
    def log_snapshot(
        self,
        blink_rate: float,
        eye_strain_score: float,
        posture_score: float,
        distance: float,
        head_pitch: float,
        head_roll: float,
        continuous_work_minutes: float,
        is_present: bool
    ):
        import time
        current_time = time.time()
        
        if current_time - self.last_snapshot_time < self.snapshot_interval:
            return
        
        snapshot = HealthSnapshot(
            timestamp=datetime.now().isoformat(),
            blink_rate=blink_rate,
            eye_strain_score=eye_strain_score,
            posture_score=posture_score,
            distance_from_screen=distance,
            head_pitch=head_pitch,
            head_roll=head_roll,
            continuous_work_minutes=continuous_work_minutes,
            is_user_present=is_present
        )
        
        self.current_day_snapshots.append(snapshot)
        self.last_snapshot_time = current_time
        
        self._update_baselines(snapshot)
        
        if len(self.current_day_snapshots) % 10 == 0:
            self._save_current_day()
    
    def _update_baselines(self, snapshot: HealthSnapshot):
        if not snapshot.is_user_present:
            return
        
        count = self.baseline_data["samples_count"]
        
        if self.baseline_data["blink_rate"] is None:
            self.baseline_data["blink_rate"] = snapshot.blink_rate
        else:
            old_rate = self.baseline_data["blink_rate"]
            self.baseline_data["blink_rate"] = (old_rate * count + snapshot.blink_rate) / (count + 1)
        
        if self.baseline_data["typical_distance"] is None:
            self.baseline_data["typical_distance"] = snapshot.distance_from_screen
        else:
            old_dist = self.baseline_data["typical_distance"]
            self.baseline_data["typical_distance"] = (old_dist * count + snapshot.distance_from_screen) / (count + 1)
        
        self.baseline_data["samples_count"] = count + 1
        
        if count % 100 == 0:
            self._save_baselines()
    
    def _save_current_day(self):
        if not self.current_day_snapshots:
            return
        
        filename = self.snapshots_dir / f"{self._get_today_filename()}.json"
        
        data = [asdict(s) for s in self.current_day_snapshots]
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
    
    def save_daily_summary(self, summary: Dict[str, Any]):
        self._save_current_day()
        
        filename = self.summaries_dir / f"{self._get_today_filename()}_summary.json"
        with open(filename, "w") as f:
            json.dump(summary, f, indent=2)
    
    def get_historical_data(self, days: int = 7) -> pd.DataFrame:
        all_data = []
        
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            filename = self.snapshots_dir / f"{date.strftime('%Y-%m-%d')}.json"
            
            if filename.exists():
                try:
                    with open(filename, "r") as f:
                        data = json.load(f)
                        all_data.extend(data)
                except:
                    pass
        
        if self.current_day_snapshots:
            all_data.extend([asdict(s) for s in self.current_day_snapshots])
        
        if not all_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df.sort_values("timestamp")
    
    def get_trend_analysis(self, days: int = 7) -> Dict[str, Any]:
        df = self.get_historical_data(days)
        
        if df.empty:
            return {"status": "insufficient_data", "message": "Not enough data for trend analysis"}
        
        df["date"] = df["timestamp"].dt.date
        
        daily_stats = df.groupby("date").agg({
            "blink_rate": "mean",
            "eye_strain_score": "mean",
            "posture_score": "mean",
            "distance_from_screen": "mean"
        }).reset_index()
        
        trends = {}
        
        for col in ["blink_rate", "eye_strain_score", "posture_score"]:
            if len(daily_stats) >= 3:
                recent = daily_stats[col].iloc[-3:].mean()
                older = daily_stats[col].iloc[:-3].mean() if len(daily_stats) > 3 else recent
                
                change = ((recent - older) / older * 100) if older != 0 else 0
                
                if col == "eye_strain_score":
                    trend = "improving" if change < -5 else "declining" if change > 5 else "stable"
                else:
                    trend = "improving" if change > 5 else "declining" if change < -5 else "stable"
                
                trends[col] = {
                    "current_average": recent,
                    "previous_average": older,
                    "change_percent": change,
                    "trend": trend
                }
        
        return {
            "status": "success",
            "days_analyzed": len(daily_stats),
            "trends": trends,
            "daily_averages": daily_stats.to_dict(orient="records")
        }
    
    def get_baselines(self) -> Dict[str, Any]:
        return self.baseline_data.copy()
    
    def cleanup_old_data(self, keep_days: int = 30):
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        
        for directory in [self.snapshots_dir, self.summaries_dir]:
            for file in directory.glob("*.json"):
                try:
                    file_date_str = file.stem.split("_")[0]
                    file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
                    if file_date < cutoff_date:
                        file.unlink()
                except:
                    pass
