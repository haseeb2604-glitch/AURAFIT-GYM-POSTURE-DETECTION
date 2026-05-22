import json
import base64
import asyncio
import time
import threading
import cv2
import numpy as np
import mediapipe as mp
from channels.generic.websocket import AsyncWebsocketConsumer
from .gym_logic import EXERCISE_LOGIC_MAP, EXERCISE_META, get_initial_state, run_exercise_logic

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

mp_pose_module = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils


def speak_async(text):
    if not text or pyttsx3 is None:
        return

    def talk():
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 175)
            engine.say(text)
            engine.runAndWait()
        except Exception:
            pass

    threading.Thread(target=talk, daemon=True).start()


class WorkoutConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer — browser sends base64 JPEG frames,
    server runs MediaPipe + exercise logic, sends back:
      { reps, stage, msg, hex_clr, efficiency, frame_b64 }
    """

    async def connect(self):
        self.exercise_key = self.scope['url_route']['kwargs']['exercise_key']
        if self.exercise_key not in EXERCISE_LOGIC_MAP:
            await self.close()
            return

        meta = EXERCISE_META[self.exercise_key]
        self.state = get_initial_state()
        self.state['stage'] = meta['initial_stage']
        self.last_voice = ''

        self.pose = mp_pose_module.Pose(
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
        )
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, 'pose'):
            self.pose.close()

    async def receive(self, text_data=None, bytes_data=None):
        try:
            data = json.loads(text_data)
            frame_b64 = data.get('frame', '')
            if not frame_b64:
                return

            # Decode base64 → numpy frame
            img_bytes = base64.b64decode(frame_b64)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None:
                return

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(rgb)

            if results.pose_landmarks:
                run_exercise_logic(
                    self.exercise_key,
                    results.pose_landmarks.landmark,
                    self.state,
                )

                voice_text = (self.state.get('voice') or '').strip()
                if voice_text and voice_text != self.last_voice:
                    speak_async(voice_text)
                    self.last_voice = voice_text

                # Draw skeleton on frame
                mp_drawing.draw_landmarks(
                    frame,
                    results.pose_landmarks,
                    mp_pose_module.POSE_CONNECTIONS,
                    mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=1, circle_radius=2),
                    mp_drawing.DrawingSpec(color=self.state['clr'], thickness=2),
                )

            # Compute efficiency
            eff = 0
            if self.state['total_frames'] > 0:
                eff = min(int(self.state['correct_frames'] / self.state['total_frames'] * 100), 100)

            # Draw HUD overlay on frame
            h, w = frame.shape[:2]
            clr = self.state['clr']

            # Top HUD removed to allow full-frame (zoomed-out) display

            # Efficiency overlay removed (no bottom bar or text)

            # Encode processed frame back to base64
            _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            frame_out = base64.b64encode(buf).decode('utf-8')

            response = {
                'reps':        self.state['reps'],
                'stage':       self.state['stage'],
                'msg':         self.state['msg'],
                'hex_clr':     self.state['hex_clr'],
                'efficiency':  eff,
                'frame':       frame_out,
            }
            
            await self.send(json.dumps(response))

        except Exception as e:
            pass  # keep connection alive on frame errors
