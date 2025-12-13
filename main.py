import tkinter as tk
from tkinter import ttk, messagebox
import cv2
from PIL import Image, ImageTk
from src.health_monitor import HealthMonitor, OverallHealthStatus
from src.screen_time_tracker import BreakType

class HealthMonitorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Health Monitor - Vision-Based Wellness Assistant")
        self.root.geometry("1200x800")
        self.root.configure(bg="#1a1a2e")
        
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.configure_styles()
        
        self.monitor = HealthMonitor()
        self.monitor.alert_callback = self.on_alert
        
        self.is_running = False
        self.current_frame = None
        
        self.create_widgets()
        
    def configure_styles(self):
        self.style.configure("TFrame", background="#1a1a2e")
        self.style.configure("TLabel", background="#1a1a2e", foreground="#eaeaea", font=("Segoe UI", 10))
        self.style.configure("Title.TLabel", font=("Segoe UI", 24, "bold"), foreground="#00d9ff")
        self.style.configure("Subtitle.TLabel", font=("Segoe UI", 14), foreground="#888888")
        self.style.configure("Status.TLabel", font=("Segoe UI", 12, "bold"))
        self.style.configure("Metric.TLabel", font=("Segoe UI", 11))
        self.style.configure("TButton", font=("Segoe UI", 10), padding=10)
        self.style.configure("Start.TButton", background="#00d9ff", foreground="#000000")
        self.style.configure("Stop.TButton", background="#ff4757", foreground="#ffffff")
        self.style.configure("TLabelframe", background="#1a1a2e")
        self.style.configure("TLabelframe.Label", background="#1a1a2e", foreground="#00d9ff", font=("Segoe UI", 11, "bold"))
        
    def create_widgets(self):
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        header = ttk.Frame(main_container)
        header.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(header, text="Health Monitor", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(header, text="Vision-Based Wellness Assistant", style="Subtitle.TLabel").pack(side=tk.LEFT, padx=(20, 0))
        
        content = ttk.Frame(main_container)
        content.pack(fill=tk.BOTH, expand=True)
        
        left_panel = ttk.Frame(content)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        self.video_frame = tk.Canvas(left_panel, width=640, height=480, bg="#2d2d44", highlightthickness=2, highlightbackground="#00d9ff")
        self.video_frame.pack(pady=(0, 10))
        
        self.video_frame.create_text(320, 240, text="Camera Preview\nClick 'Start Monitoring' to begin", fill="#888888", font=("Segoe UI", 14), justify=tk.CENTER)
        
        controls = ttk.Frame(left_panel)
        controls.pack(fill=tk.X)
        
        self.start_btn = ttk.Button(controls, text="Start Monitoring", command=self.start_monitoring, style="Start.TButton")
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(controls, text="Stop Monitoring", command=self.stop_monitoring, style="Stop.TButton", state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(controls, text="Take Break", command=self.take_break).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls, text="Dismiss Alerts", command=self.dismiss_alerts).pack(side=tk.LEFT, padx=5)
        
        right_panel = ttk.Frame(content, width=400)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        right_panel.pack_propagate(False)
        
        self.create_status_panel(right_panel)
        self.create_metrics_panel(right_panel)
        self.create_alerts_panel(right_panel)
        
    def create_status_panel(self, parent):
        status_frame = ttk.LabelFrame(parent, text="Overall Status", padding=15)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ttk.Label(status_frame, text="Not Running", style="Status.TLabel", foreground="#888888")
        self.status_label.pack()
        
        self.score_label = ttk.Label(status_frame, text="Health Score: --", style="Metric.TLabel")
        self.score_label.pack(pady=(5, 0))
        
        self.calibration_label = ttk.Label(status_frame, text="", style="Metric.TLabel", foreground="#ffcc00")
        self.calibration_label.pack(pady=(5, 0))
        
    def create_metrics_panel(self, parent):
        eye_frame = ttk.LabelFrame(parent, text="Eye Health", padding=15)
        eye_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.blink_rate_label = ttk.Label(eye_frame, text="Blink Rate: -- blinks/min", style="Metric.TLabel")
        self.blink_rate_label.pack(anchor=tk.W)
        
        self.eye_strain_label = ttk.Label(eye_frame, text="Eye Strain: --%", style="Metric.TLabel")
        self.eye_strain_label.pack(anchor=tk.W)
        
        self.eye_status_label = ttk.Label(eye_frame, text="Status: --", style="Metric.TLabel")
        self.eye_status_label.pack(anchor=tk.W)
        
        posture_frame = ttk.LabelFrame(parent, text="Posture", padding=15)
        posture_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.posture_score_label = ttk.Label(posture_frame, text="Posture Score: --%", style="Metric.TLabel")
        self.posture_score_label.pack(anchor=tk.W)
        
        self.distance_label = ttk.Label(posture_frame, text="Distance: -- cm", style="Metric.TLabel")
        self.distance_label.pack(anchor=tk.W)
        
        self.posture_status_label = ttk.Label(posture_frame, text="Status: --", style="Metric.TLabel")
        self.posture_status_label.pack(anchor=tk.W)
        
        self.posture_issues_label = ttk.Label(posture_frame, text="", style="Metric.TLabel", foreground="#ff4757", wraplength=350)
        self.posture_issues_label.pack(anchor=tk.W, pady=(5, 0))
        
        time_frame = ttk.LabelFrame(parent, text="Screen Time", padding=15)
        time_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.session_time_label = ttk.Label(time_frame, text="Current Session: -- min", style="Metric.TLabel")
        self.session_time_label.pack(anchor=tk.W)
        
        self.total_time_label = ttk.Label(time_frame, text="Today Total: -- min", style="Metric.TLabel")
        self.total_time_label.pack(anchor=tk.W)
        
        self.next_break_label = ttk.Label(time_frame, text="Next Break: -- min", style="Metric.TLabel")
        self.next_break_label.pack(anchor=tk.W)
        
    def create_alerts_panel(self, parent):
        alerts_frame = ttk.LabelFrame(parent, text="Active Alerts", padding=15)
        alerts_frame.pack(fill=tk.BOTH, expand=True)
        
        self.alerts_text = tk.Text(alerts_frame, height=8, bg="#2d2d44", fg="#eaeaea", font=("Segoe UI", 10), wrap=tk.WORD, state=tk.DISABLED)
        self.alerts_text.pack(fill=tk.BOTH, expand=True)
        
    def start_monitoring(self):
        if self.monitor.start():
            self.is_running = True
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.status_label.config(text="Initializing...", foreground="#ffcc00")
            
            self.schedule_update()
        else:
            messagebox.showerror("Error", "Could not access camera. Please check if a camera is connected and not in use by another application.")
    
    def stop_monitoring(self):
        self.is_running = False
        self.monitor.stop()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Stopped", foreground="#888888")
        
        self.video_frame.delete("all")
        self.video_frame.create_text(320, 240, text="Camera Preview\nClick 'Start Monitoring' to begin", fill="#888888", font=("Segoe UI", 14), justify=tk.CENTER)
    
    def schedule_update(self):
        if not self.is_running:
            return
        
        try:
            health_state = self.monitor.process_frame()
            
            if health_state:
                self.update_display(health_state)
            
            frame = self.monitor.get_annotated_frame()
            if frame is not None:
                self.current_frame = frame
                self.update_video()
        except Exception as e:
            print(f"Update error: {e}")
        
        if self.is_running:
            self.root.after(33, self.schedule_update)
    
    def update_video(self):
        if self.current_frame is not None and self.is_running:
            frame_rgb = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            img = img.resize((640, 480), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            
            self.video_frame.delete("all")
            self.video_frame.create_image(0, 0, anchor=tk.NW, image=photo)
            self.video_frame.image = photo
    
    def update_display(self, health_state):
        if not health_state.is_user_present:
            self.status_label.config(text="User Away", foreground="#888888")
            return
        
        status_colors = {
            OverallHealthStatus.EXCELLENT: "#00ff88",
            OverallHealthStatus.GOOD: "#00d9ff",
            OverallHealthStatus.FAIR: "#ffcc00",
            OverallHealthStatus.NEEDS_ATTENTION: "#ff4757"
        }
        
        status_text = health_state.overall_status.value.replace("_", " ").title()
        self.status_label.config(text=status_text, foreground=status_colors.get(health_state.overall_status, "#888888"))
        self.score_label.config(text=f"Health Score: {health_state.overall_score:.0f}%")
        
        if health_state.is_calibrating:
            self.calibration_label.config(text="Calibrating your baselines...")
        else:
            self.calibration_label.config(text="")
        
        eye = health_state.eye_metrics
        if eye:
            self.blink_rate_label.config(text=f"Blink Rate: {eye.get('blink_rate', 0):.1f} blinks/min")
            self.eye_strain_label.config(text=f"Eye Strain: {eye.get('eye_strain_score', 0):.0f}%")
            
            eye_status = eye.get('status', 'unknown')
            eye_color = {"healthy": "#00ff88", "warning": "#ffcc00", "critical": "#ff4757"}.get(eye_status, "#888888")
            self.eye_status_label.config(text=f"Status: {eye_status.title()}", foreground=eye_color)
        
        posture = health_state.posture_metrics
        if posture:
            self.posture_score_label.config(text=f"Posture Score: {posture.get('posture_score', 0):.0f}%")
            self.distance_label.config(text=f"Distance: {posture.get('distance', 0):.0f} cm")
            
            posture_status = posture.get('status', 'unknown')
            posture_color = {"good": "#00ff88", "warning": "#ffcc00", "poor": "#ff4757"}.get(posture_status, "#888888")
            self.posture_status_label.config(text=f"Status: {posture_status.title()}", foreground=posture_color)
            
            issues = posture.get('issues', [])
            if issues:
                self.posture_issues_label.config(text=" | ".join(issues[:2]))
            else:
                self.posture_issues_label.config(text="")
        
        screen = health_state.screen_time_stats
        if screen:
            self.session_time_label.config(text=f"Current Session: {screen.get('current_session_minutes', 0):.0f} min")
            self.total_time_label.config(text=f"Today Total: {screen.get('total_screen_time_today_minutes', 0):.0f} min")
            
            next_break = min(
                screen.get('time_until_micro_break', 9999),
                screen.get('time_until_short_break', 9999),
                screen.get('time_until_long_break', 9999)
            )
            self.next_break_label.config(text=f"Next Break: {next_break/60:.0f} min")
        
        self.update_alerts(health_state.active_alerts)
    
    def update_alerts(self, alerts):
        self.alerts_text.config(state=tk.NORMAL)
        self.alerts_text.delete(1.0, tk.END)
        
        if not alerts:
            self.alerts_text.insert(tk.END, "No active alerts. Keep up the good work!")
        else:
            for alert in alerts:
                severity_emoji = {"info": "INFO", "warning": "WARNING", "critical": "CRITICAL"}
                self.alerts_text.insert(tk.END, f"[{severity_emoji.get(alert['severity'], '?')}] {alert['title']}\n")
                self.alerts_text.insert(tk.END, f"{alert['message']}\n")
                self.alerts_text.insert(tk.END, f"Tip: {alert['recommendation']}\n\n")
        
        self.alerts_text.config(state=tk.DISABLED)
    
    def on_alert(self, alert):
        try:
            from plyer import notification
            notification.notify(
                title=alert.title,
                message=alert.message[:256],
                app_name="Health Monitor",
                timeout=10
            )
        except Exception as e:
            print(f"Notification error: {e}")
    
    def take_break(self):
        if self.is_running:
            self.monitor.record_break(BreakType.SHORT)
            messagebox.showinfo("Break Recorded", "Great job taking a break! Your break timer has been reset.\n\nSuggested activities:\n- Look at something 20 feet away\n- Stretch your arms and shoulders\n- Take a few deep breaths")
    
    def dismiss_alerts(self):
        if self.is_running:
            self.monitor.acknowledge_all_alerts()
    
    def on_closing(self):
        self.is_running = False
        if self.monitor:
            self.monitor.stop()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = HealthMonitorGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
