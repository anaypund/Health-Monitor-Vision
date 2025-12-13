import cv2
import mediapipe as mp
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple, List

@dataclass
class FaceLandmarks:
    landmarks: List[Tuple[float, float, float]]
    image_width: int
    image_height: int
    
    def get_landmark(self, index: int) -> Tuple[int, int]:
        lm = self.landmarks[index]
        return (int(lm[0] * self.image_width), int(lm[1] * self.image_height))
    
    def get_landmark_3d(self, index: int) -> Tuple[float, float, float]:
        lm = self.landmarks[index]
        return (lm[0] * self.image_width, lm[1] * self.image_height, lm[2])

class VisionEngine:
    LEFT_EYE_INDICES = [362, 385, 387, 263, 373, 380]
    RIGHT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
    LEFT_EYE_TOP = 386
    LEFT_EYE_BOTTOM = 374
    RIGHT_EYE_TOP = 159
    RIGHT_EYE_BOTTOM = 145
    NOSE_TIP = 1
    CHIN = 152
    LEFT_EYE_OUTER = 263
    RIGHT_EYE_OUTER = 33
    LEFT_MOUTH = 61
    RIGHT_MOUTH = 291
    FOREHEAD = 10
    LEFT_SHOULDER_APPROX = 234
    RIGHT_SHOULDER_APPROX = 454
    
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        self.cap = None
        self.is_running = False
        
    def start_camera(self, camera_index: int = 0) -> bool:
        try:
            self.cap = cv2.VideoCapture(camera_index)
            if not self.cap.isOpened():
                return False
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.is_running = True
            return True
        except Exception as e:
            print(f"Camera initialization failed: {e}")
            return False
    
    def stop_camera(self):
        self.is_running = False
        if self.cap:
            self.cap.release()
            self.cap = None
    
    def get_frame(self) -> Optional[np.ndarray]:
        if not self.cap or not self.is_running:
            return None
        ret, frame = self.cap.read()
        if not ret:
            return None
        return cv2.flip(frame, 1)
    
    def process_frame(self, frame: np.ndarray) -> Optional[FaceLandmarks]:
        if frame is None:
            return None
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_frame)
        
        if not results.multi_face_landmarks:
            return None
        
        face_landmarks = results.multi_face_landmarks[0]
        landmarks = [(lm.x, lm.y, lm.z) for lm in face_landmarks.landmark]
        
        return FaceLandmarks(
            landmarks=landmarks,
            image_width=frame.shape[1],
            image_height=frame.shape[0]
        )
    
    def draw_landmarks(self, frame: np.ndarray, face_landmarks: FaceLandmarks) -> np.ndarray:
        if face_landmarks is None:
            return frame
        
        annotated_frame = frame.copy()
        
        for idx in self.LEFT_EYE_INDICES + self.RIGHT_EYE_INDICES:
            point = face_landmarks.get_landmark(idx)
            cv2.circle(annotated_frame, point, 2, (0, 255, 0), -1)
        
        nose = face_landmarks.get_landmark(self.NOSE_TIP)
        cv2.circle(annotated_frame, nose, 3, (255, 0, 0), -1)
        
        chin = face_landmarks.get_landmark(self.CHIN)
        cv2.circle(annotated_frame, chin, 3, (255, 0, 0), -1)
        
        forehead = face_landmarks.get_landmark(self.FOREHEAD)
        cv2.circle(annotated_frame, forehead, 3, (255, 0, 0), -1)
        
        cv2.line(annotated_frame, forehead, chin, (255, 255, 0), 1)
        
        return annotated_frame
    
    def calculate_eye_aspect_ratio(self, face_landmarks: FaceLandmarks, eye: str = "left") -> float:
        if eye == "left":
            top = face_landmarks.get_landmark(self.LEFT_EYE_TOP)
            bottom = face_landmarks.get_landmark(self.LEFT_EYE_BOTTOM)
            outer = face_landmarks.get_landmark(self.LEFT_EYE_INDICES[3])
            inner = face_landmarks.get_landmark(self.LEFT_EYE_INDICES[0])
        else:
            top = face_landmarks.get_landmark(self.RIGHT_EYE_TOP)
            bottom = face_landmarks.get_landmark(self.RIGHT_EYE_BOTTOM)
            outer = face_landmarks.get_landmark(self.RIGHT_EYE_INDICES[3])
            inner = face_landmarks.get_landmark(self.RIGHT_EYE_INDICES[0])
        
        vertical_dist = np.sqrt((top[0] - bottom[0])**2 + (top[1] - bottom[1])**2)
        horizontal_dist = np.sqrt((outer[0] - inner[0])**2 + (outer[1] - inner[1])**2)
        
        if horizontal_dist == 0:
            return 0.0
        
        ear = vertical_dist / horizontal_dist
        return ear
    
    def calculate_head_pose(self, face_landmarks: FaceLandmarks) -> Tuple[float, float, float]:
        nose = face_landmarks.get_landmark_3d(self.NOSE_TIP)
        chin = face_landmarks.get_landmark_3d(self.CHIN)
        forehead = face_landmarks.get_landmark_3d(self.FOREHEAD)
        left_eye = face_landmarks.get_landmark_3d(self.LEFT_EYE_OUTER)
        right_eye = face_landmarks.get_landmark_3d(self.RIGHT_EYE_OUTER)
        
        eye_center_x = (left_eye[0] + right_eye[0]) / 2
        eye_center_y = (left_eye[1] + right_eye[1]) / 2
        
        dx = right_eye[0] - left_eye[0]
        dy = right_eye[1] - left_eye[1]
        roll = np.degrees(np.arctan2(dy, dx))
        
        vertical_dx = chin[0] - forehead[0]
        vertical_dy = chin[1] - forehead[1]
        pitch = np.degrees(np.arctan2(vertical_dx, vertical_dy))
        
        face_center_x = (left_eye[0] + right_eye[0]) / 2
        frame_center = face_landmarks.image_width / 2
        yaw = ((face_center_x - frame_center) / frame_center) * 30
        
        return (pitch, yaw, roll)
    
    def estimate_face_distance(self, face_landmarks: FaceLandmarks) -> float:
        left_eye = face_landmarks.get_landmark(self.LEFT_EYE_OUTER)
        right_eye = face_landmarks.get_landmark(self.RIGHT_EYE_OUTER)
        
        eye_distance_px = np.sqrt(
            (left_eye[0] - right_eye[0])**2 + 
            (left_eye[1] - right_eye[1])**2
        )
        
        AVERAGE_EYE_DISTANCE_CM = 6.3
        FOCAL_LENGTH_ESTIMATE = 600
        
        if eye_distance_px > 0:
            distance_cm = (AVERAGE_EYE_DISTANCE_CM * FOCAL_LENGTH_ESTIMATE) / eye_distance_px
            return distance_cm
        return 0.0
    
    def __del__(self):
        self.stop_camera()
