import numpy as np
import mediapipe as mp
import time

mp_pose = mp.solutions.pose

# How many consecutive frames are required to confirm a position/change
CONFIRM_FRAMES_SHORT = 3
CONFIRM_FRAMES_MED = 5


def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0:
        angle = 360 - angle
    return angle


def _set_feedback(state, msg, clr, hex_clr):
    state["msg"] = msg
    state["clr"] = clr
    state["hex_clr"] = hex_clr


def _set_voice(state, voice):
    state["voice"] = voice


def _cooldown(state, seconds):
    state["alert_time"] = time.time() + seconds


def _penalize_frame(state):
    state["correct_frames"] = max(0, state["correct_frames"] - 1)


def _avg_angle(left_a, left_b, left_c, right_a, right_b, right_c):
    return (
        calculate_angle(left_a, left_b, left_c) +
        calculate_angle(right_a, right_b, right_c)
    ) / 2.0


def get_initial_state():
    return {
        "reps": 0,
        "stage": "down",
        "alert_time": 0,
        "msg": "READY TO START",
        "voice": "",
        "clr": (255, 255, 255),
        "hex_clr": "#ffffff",
        "total_frames": 0,
        "correct_frames": 0,
        "hold_count": 0,
    }


# ─────────────────────────────────────────────
# JUMPING JACKS
# ─────────────────────────────────────────────
def jumping_jacks_logic(lm, state):
    try:
        l_sh = lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        r_sh = lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        l_w  = lm[mp_pose.PoseLandmark.LEFT_WRIST.value]
        r_w  = lm[mp_pose.PoseLandmark.RIGHT_WRIST.value]
        l_a  = lm[mp_pose.PoseLandmark.LEFT_ANKLE.value]
        r_a  = lm[mp_pose.PoseLandmark.RIGHT_ANKLE.value]

        leg_dist = abs(l_a.x - r_a.x)
        sh_width = abs(l_sh.x - r_sh.x)
        hands_up = l_w.y < min(l_sh.y, r_sh.y) - 0.02 and r_w.y < min(l_sh.y, r_sh.y) - 0.02
        hands_down = l_w.y > max(l_sh.y, r_sh.y) + 0.02 and r_w.y > max(l_sh.y, r_sh.y) + 0.02
        legs_out = leg_dist > (sh_width * 1.15)
        legs_in = leg_dist < (sh_width * 1.05)
        t = time.time()

        state["total_frames"] += 1
        if t < state["alert_time"]:
            return

        msg, clr, hex_clr = "KEEP PUSHING", (0, 255, 0), "#00ff00"
        state["correct_frames"] += 1

        # stricter multipliers
        legs_out = leg_dist > (sh_width * 1.25)
        legs_in = leg_dist < (sh_width * 1.08)

        # DOWN -> UP transition (open)
        if state["stage"] == "down":
            if hands_up and legs_out:
                state["hold_count"] = state.get("hold_count", 0) + 1
                if state["hold_count"] >= CONFIRM_FRAMES_SHORT:
                    state["stage"] = "up"
                    state["hold_count"] = 0
                    msg, clr, hex_clr = "PERFECT!", (0, 255, 200), "#00ffc8"
                    _set_voice(state, "Perfect jumping jacks")
                else:
                    msg, clr, hex_clr = f"HOLD ({state['hold_count']})", (200, 200, 0), "#ffea00"
            else:
                state["hold_count"] = 0
                if not hands_up and legs_out:
                    msg, clr, hex_clr = "ARMS UP!", (0, 0, 255), "#ff0000"
                    _cooldown(state, 1.2)
                    _penalize_frame(state)
                    _set_voice(state, "Raise both arms up")
                elif hands_up and not legs_out:
                    msg, clr, hex_clr = "WIDER!", (0, 165, 255), "#ffaa00"
                    _cooldown(state, 1.2)
                    _penalize_frame(state)
                    _set_voice(state, "Open your legs wider")
        # UP -> DOWN transition (close) — require more frames to confirm count
        elif state["stage"] == "up":
            if hands_down and legs_in:
                state["hold_count"] = state.get("hold_count", 0) + 1
                if state["hold_count"] >= CONFIRM_FRAMES_MED:
                    state["stage"] = "down"
                    state["reps"] += 1
                    state["hold_count"] = 0
                    msg, clr, hex_clr = "GOOD JOB!", (255, 255, 0), "#ffff00"
                    _cooldown(state, 1.0)
                    _set_voice(state, "Jumping jack counted")
                else:
                    msg, clr, hex_clr = f"HOLD ({state['hold_count']})", (200, 200, 0), "#ffea00"
            else:
                state["hold_count"] = 0

        _set_feedback(state, msg, clr, hex_clr)
    except:
        pass


# ─────────────────────────────────────────────
# LUNGES
# ─────────────────────────────────────────────
def lunges_logic(lm, state):
    try:
        nose = [lm[mp_pose.PoseLandmark.NOSE.value].x, lm[mp_pose.PoseLandmark.NOSE.value].y]
        l_hip = [lm[mp_pose.PoseLandmark.LEFT_HIP.value].x,        lm[mp_pose.PoseLandmark.LEFT_HIP.value].y]
        l_kne = [lm[mp_pose.PoseLandmark.LEFT_KNEE.value].x,       lm[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
        l_ank = [lm[mp_pose.PoseLandmark.LEFT_ANKLE.value].x,      lm[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
        r_hip = [lm[mp_pose.PoseLandmark.RIGHT_HIP.value].x,       lm[mp_pose.PoseLandmark.RIGHT_HIP.value].y]
        r_kne = [lm[mp_pose.PoseLandmark.RIGHT_KNEE.value].x,      lm[mp_pose.PoseLandmark.RIGHT_KNEE.value].y]
        r_ank = [lm[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x,     lm[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y]
        l_sh  = [lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,   lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y, lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].z]
        r_sh  = [lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x,  lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y, lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].z]
        l_toe = [lm[mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value].x,  lm[mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value].y]
        r_toe = [lm[mp_pose.PoseLandmark.RIGHT_FOOT_INDEX.value].x, lm[mp_pose.PoseLandmark.RIGHT_FOOT_INDEX.value].y]

        knee_angle = min(
            calculate_angle(l_hip, l_kne, l_ank),
            calculate_angle(r_hip, r_kne, r_ank),
        )
        shoulder_center_x = (l_sh[0] + r_sh[0]) / 2.0
        hip_center_x = (l_hip[0] + r_hip[0]) / 2.0
        # Estimate torso lean using horizontal offset (fallback) and use z-difference
        back_tilt  = abs(shoulder_center_x - hip_center_x)
        # z-difference between shoulders indicates how rotated the body is (side vs facing)
        sh_z_diff = abs(l_sh[2] - r_sh[2])
        t = time.time()

        state["total_frames"] += 1
        if t < state["alert_time"]:
            return

        # If user is facing the camera, ask to turn sideways.
        # Use both z-difference and width checks to avoid false counts from head movement.
        sh_width = abs(l_sh[0] - r_sh[0])
        hip_width = abs(l_hip[0] - r_hip[0]) if abs(l_hip[0] - r_hip[0]) > 1e-6 else 1e-6
        hip_z_diff = abs(l_hip[2] - r_hip[2]) if len(l_hip) > 2 and len(r_hip) > 2 else 0.0
        face_center_offset = abs(nose[0] - shoulder_center_x)
        facing_camera = (
            sh_z_diff < 0.08 and
            hip_z_diff < 0.08 and
            sh_width < (hip_width * 1.05)
        )
        face_front = face_center_offset < (sh_width * 0.18)
        if facing_camera or face_front:
            _set_feedback(state, "TURN SIDEWAYS", (255, 100, 0), "#ff6400")
            _penalize_frame(state)
            _set_voice(state, "Please turn sideways to the camera")
            return

        msg, clr, hex_clr = "KEEP GOING", (0, 255, 0), "#00ff00"
        state["correct_frames"] += 1

        # Use the foot that is actually stepping forward for this rep.
        front_toe = l_toe if abs(l_toe[0] - hip_center_x) >= abs(r_toe[0] - hip_center_x) else r_toe
        front_knee = l_kne if front_toe is l_toe else r_kne

        # Require a real split stance: both ankles should be separated enough.
        ankle_sep = abs(l_ank[0] - r_ank[0])
        if ankle_sep < 0.06:
            _set_feedback(state, "WIDEN STANCE", (200, 140, 0), "#ff9900")
            _penalize_frame(state)
            _set_voice(state, "Widen your stance before lunging")
            return

        # Require the front foot to be stepped forward enough relative to hips.
        # Keep it easy, but not so loose that head movement can trigger counts.
        toe_forward = abs(front_toe[0] - hip_center_x) > 0.04
        if not toe_forward:
            _set_feedback(state, "STEP FORWARD", (200, 140, 0), "#ff9900")
            _penalize_frame(state)
            _set_voice(state, "Step your foot forward more")
            return

        if back_tilt > 0.12:
            msg, clr, hex_clr = "STRAIGHT BACK", (0, 165, 255), "#ffaa00"
            _penalize_frame(state)
            _set_voice(state, "Keep your back straight")
        elif front_knee[0] > front_toe[0] + 0.04:
            msg, clr, hex_clr = "KNEE OVER TOE", (0, 0, 255), "#ff0000"
            _penalize_frame(state)
            _set_voice(state, "Keep your knee behind your toe")

        # UP region detected (leg extended) — keep a small buffer so only clear lunge stances pass
        if knee_angle > 158:
            state["hold_count"] = state.get("hold_count", 0) + 1
            if state["hold_count"] >= CONFIRM_FRAMES_SHORT:
                if state["stage"] == "down":
                    state["stage"] = "up"
                    _set_voice(state, "Step and drop down")
                msg, clr, hex_clr = "STEP & DROP", (0, 255, 0), "#00ff00"
                state["hold_count"] = 0
        # MID depth — encourage deeper, but allow regular lunge depth
        elif 122 < knee_angle <= 158:
            state["hold_count"] = 0
            msg, clr, hex_clr = "GO DEEPER", (0, 255, 255), "#00ffff"
            _set_voice(state, "Go a little deeper")
        # DOWN position (deep lunge) — count when clearly deep but not overly strict
        elif knee_angle <= 122:
            state["hold_count"] = state.get("hold_count", 0) + 1
            if state["hold_count"] >= CONFIRM_FRAMES_SHORT:
                if state["stage"] == "up":
                    state["reps"] += 1
                    _cooldown(state, 1.0)
                    _set_voice(state, "Lunge counted")
                state["stage"] = "down"
                msg, clr, hex_clr = "PERFECT LUNGE", (255, 255, 0), "#ffff00"
                state["hold_count"] = 0

        _set_feedback(state, msg, clr, hex_clr)
    except:
        pass


# ─────────────────────────────────────────────
# PUSH UPS
# ─────────────────────────────────────────────
def pushups_logic(lm, state):
    try:
        nose = [lm[mp_pose.PoseLandmark.NOSE.value].x, lm[mp_pose.PoseLandmark.NOSE.value].y]
        l_sh = [lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y, lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].z]
        l_el = [lm[mp_pose.PoseLandmark.LEFT_ELBOW.value].x, lm[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
        l_wr = [lm[mp_pose.PoseLandmark.LEFT_WRIST.value].x, lm[mp_pose.PoseLandmark.LEFT_WRIST.value].y]
        l_hip = [lm[mp_pose.PoseLandmark.LEFT_HIP.value].x, lm[mp_pose.PoseLandmark.LEFT_HIP.value].y, lm[mp_pose.PoseLandmark.LEFT_HIP.value].z]
        l_ank = [lm[mp_pose.PoseLandmark.LEFT_ANKLE.value].x, lm[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
        r_sh = [lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x, lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y, lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].z]
        r_el = [lm[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x, lm[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]
        r_wr = [lm[mp_pose.PoseLandmark.RIGHT_WRIST.value].x, lm[mp_pose.PoseLandmark.RIGHT_WRIST.value].y]
        r_hip = [lm[mp_pose.PoseLandmark.RIGHT_HIP.value].x, lm[mp_pose.PoseLandmark.RIGHT_HIP.value].y, lm[mp_pose.PoseLandmark.RIGHT_HIP.value].z]
        r_ank = [lm[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x, lm[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y]
        l_kne = [lm[mp_pose.PoseLandmark.LEFT_KNEE.value].x, lm[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
        r_kne = [lm[mp_pose.PoseLandmark.RIGHT_KNEE.value].x, lm[mp_pose.PoseLandmark.RIGHT_KNEE.value].y]

        elbow_angle = _avg_angle(l_sh, l_el, l_wr, r_sh, r_el, r_wr)
        body_angle = _avg_angle(l_sh, l_hip, l_ank, r_sh, r_hip, r_ank)
        t = time.time()

        state["total_frames"] += 1
        if t < state["alert_time"]:
            return

        state["correct_frames"] += 1

        # track recent shoulder vertical movement to distinguish real pushups from head nods
        shoulder_center_y = (l_sh[1] + r_sh[1]) / 2.0
        # use a simple EMA to smooth shoulder y and reduce jitter
        prev_sh_ema = state.get("prev_sh_y", shoulder_center_y)
        alpha = 0.4
        smoothed_sh_y = (alpha * shoulder_center_y) + ((1 - alpha) * prev_sh_ema)
        sh_y_delta = prev_sh_ema - smoothed_sh_y
        # update EMA storage
        state["prev_sh_y"] = smoothed_sh_y
        # positive delta means shoulders moved up (body rose)
        # detect smaller real shoulder rises with a lower threshold
        if sh_y_delta > 0.002:
            state["last_sh_move"] = time.time()
        # store for debug
        state["sh_y_delta"] = sh_y_delta

        # track elbow angle delta as an alternate movement signal (helps when shoulders are noisy)
        prev_elbow = state.get("prev_elbow_angle", elbow_angle)
        elbow_delta = elbow_angle - prev_elbow
        state["prev_elbow_angle"] = elbow_angle

        # Block counting if user is facing the camera or head is centered/forward
        sh_width = abs(l_sh[0] - r_sh[0])
        shoulder_center_x = (l_sh[0] + r_sh[0]) / 2.0
        sh_z_diff = abs(l_sh[2] - r_sh[2])
        hip_z_diff = abs(l_hip[2] - r_hip[2]) if len(l_hip) > 2 and len(r_hip) > 2 else 1.0
        face_center_offset = abs(nose[0] - shoulder_center_x)

        # block obvious upright/front-facing poses by checking shoulder vs hip vertical offset
        hip_center_y = (l_hip[1] + r_hip[1]) / 2.0
        vert_torso_offset = abs(shoulder_center_y - hip_center_y)
        # store for debug
        state["vert_torso_offset"] = vert_torso_offset
        if vert_torso_offset > 0.12:
            _set_feedback(state, "ASSUME PUSHUP POSITION", (255, 100, 0), "#ff6400")
            _penalize_frame(state)
            _set_voice(state, "Get into pushup position")
            return

        # Consider face-front only when shoulders and hips indicate frontal pose and nose is centered.
        face_front = (sh_z_diff < 0.06) and (hip_z_diff < 0.06) and (face_center_offset < (sh_width * 0.22))
        # store for debug
        state["face_front"] = face_front
        if face_front:
            _set_feedback(state, "TURN AWAY", (255, 100, 0), "#ff6400")
            _penalize_frame(state)
            _set_voice(state, "Please turn away or align your body")
            return

        # Detect bent knees (knees-on-ground) by checking knee joint angle.
        # If knees are noticeably bent, treat as modified pushup and do not count.
        try:
            knee_leg_angle = min(
                calculate_angle(l_hip, l_kne, l_ank),
                calculate_angle(r_hip, r_kne, r_ank),
            )
        except:
            knee_leg_angle = 180.0

        # If knee angle indicates bent legs (less than 150 deg), ask to straighten legs.
        if knee_leg_angle < 150:
            _set_feedback(state, "STRAIGHTEN LEGS", (0, 0, 255), "#ff0000")
            _penalize_frame(state)
            _set_voice(state, "Keep your legs straight for a proper push up")
            return

        if body_angle < 170:
            _set_feedback(state, "KEEP BODY STRAIGHT", (0, 0, 255), "#ff0000")
            _penalize_frame(state)
            _set_voice(state, "Keep your body straight")

        # DOWN -> UP (push) — require a few frames to confirm
        if elbow_angle > 140:
            state["hold_count"] = state.get("hold_count", 0) + 1
            # make upward confirmation easier: allow 1 frame
            if state["hold_count"] >= 1:
                # require torso reasonably straight for a valid count
                # and ensure shoulders moved recently or elbows opened (prevents head-only counts)
                recent_sh_move = (time.time() - state.get("last_sh_move", 0)) < 2.5
                elbow_movement = elbow_delta > 4.0
                movement_confirmed = recent_sh_move or elbow_movement
                # also avoid double-counting: ignore if last pushup rep was very recent
                recent_rep = (time.time() - state.get("last_pushup_rep", 0)) < 0.5
                # relax body angle requirement slightly to accept more camera setups
                if body_angle >= 150 and movement_confirmed and not recent_rep:
                    if state["stage"] == "down":
                        state["reps"] += 1
                        _cooldown(state, 1.2)
                        state["last_pushup_rep"] = time.time()
                        _set_voice(state, "Push up counted")
                    state["stage"] = "up"
                    _set_feedback(state, "GO DOWN", (0, 255, 0), "#00ff00")
                    state["hold_count"] = 0
                else:
                    _set_feedback(state, "KEEP BODY STRAIGHT", (0, 0, 255), "#ff0000")
                    _penalize_frame(state)
                    _set_voice(state, "Keep your body straight")
                    state["hold_count"] = 0
            else:
                _set_feedback(state, f"HOLD ({state['hold_count']})", (200, 200, 0), "#ffea00")
        # UP -> DOWN (bottom) — require shorter confirmation
        elif elbow_angle < 110:
            state["hold_count"] = state.get("hold_count", 0) + 1
            if state["hold_count"] >= CONFIRM_FRAMES_SHORT:
                state["stage"] = "down"
                _set_feedback(state, "PERFECT FORM", (255, 255, 0), "#ffff00")
                _set_voice(state, "Perfect push up form")
                state["hold_count"] = 0
        else:
            state["hold_count"] = 0
            _set_feedback(state, "KEEP GOING", (0, 200, 255), "#00c8ff")
        
        # Store debug metrics for tuning (available via WebSocket response)
        state["debug"] = {
            "elbow_angle": round(elbow_angle, 2),
            "body_angle": round(body_angle, 2),
            "sh_y_delta": round(state.get("sh_y_delta", 0), 4),
            "vert_torso_offset": round(state.get("vert_torso_offset", 0), 4),
            "face_front": state.get("face_front", False),
            "elbow_delta": round(elbow_delta, 2),
            "hold_count": state.get("hold_count", 0),
            "stage": state.get("stage", "unknown"),
        }
    except:
        pass


# ─────────────────────────────────────────────
# SQUATS
# ─────────────────────────────────────────────
def squats_logic(lm, state):
    try:
        l_sh  = [lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x,  lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
        r_sh  = [lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x, lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
        l_hip = [lm[mp_pose.PoseLandmark.LEFT_HIP.value].x,       lm[mp_pose.PoseLandmark.LEFT_HIP.value].y]
        r_hip = [lm[mp_pose.PoseLandmark.RIGHT_HIP.value].x,      lm[mp_pose.PoseLandmark.RIGHT_HIP.value].y]
        l_kn  = [lm[mp_pose.PoseLandmark.LEFT_KNEE.value].x,      lm[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
        r_kn  = [lm[mp_pose.PoseLandmark.RIGHT_KNEE.value].x,     lm[mp_pose.PoseLandmark.RIGHT_KNEE.value].y]
        l_ank = [lm[mp_pose.PoseLandmark.LEFT_ANKLE.value].x,     lm[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
        r_ank = [lm[mp_pose.PoseLandmark.RIGHT_ANKLE.value].x,    lm[mp_pose.PoseLandmark.RIGHT_ANKLE.value].y]
        rw    = [lm[mp_pose.PoseLandmark.RIGHT_WRIST.value].x,    lm[mp_pose.PoseLandmark.RIGHT_WRIST.value].y]
        lw    = [lm[mp_pose.PoseLandmark.LEFT_WRIST.value].x,     lm[mp_pose.PoseLandmark.LEFT_WRIST.value].y]

        knee_angle = (
            calculate_angle(l_hip, l_kn, l_ank) +
            calculate_angle(r_hip, r_kn, r_ank)
        ) / 2.0
        hip_center_y = (l_hip[1] + r_hip[1]) / 2.0
        knee_center_y = (l_kn[1] + r_kn[1]) / 2.0
        t = time.time()

        state["total_frames"] += 1
        if t < state["alert_time"]:
            return

        hand_dist = np.sqrt((rw[0] - lw[0]) ** 2 + (rw[1] - lw[1]) ** 2)
        # Require both wrists to be roughly at chest height (between shoulders and hips)
        is_at_chest = (
            rw[1] < max(l_hip[1], r_hip[1]) and rw[1] > min(l_sh[1], r_sh[1]) and
            lw[1] < max(l_hip[1], r_hip[1]) and lw[1] > min(l_sh[1], r_sh[1])
        )

        state["correct_frames"] += 1

        # If hands aren't correctly positioned, penalize and do NOT proceed to counting.
        if hand_dist > 0.12 or not is_at_chest:
            _set_feedback(state, "STRAIGHT HANDS", (0, 0, 255), "#ff0000")
            _penalize_frame(state)
            _set_voice(state, "Keep your hands straight and close")
            return

        # Stop counting if the hips drop too low and are effectively touching the floor.
        # This is a too-deep squat / sitting position, not a valid rep.
        too_deep = hip_center_y > knee_center_y + 0.06 or hip_center_y > min(l_ank[1], r_ank[1]) - 0.02
        if too_deep:
            state["hold_count"] = 0
            if not state.get("too_deep_blocked", False):
                _set_feedback(state, "TOO DEEP", (255, 100, 0), "#ff6400")
                _penalize_frame(state)
                _set_voice(state, "Do not go that low")
                state["too_deep_blocked"] = True
            state["debug"] = {
                "knee_angle": round(knee_angle, 2),
                "hand_dist": round(hand_dist, 3),
                "is_at_chest": is_at_chest,
                "hold_count": state.get("hold_count", 0),
                "stage": state.get("stage", "unknown"),
            }
            return

        # Clear the block once the user comes back up out of the too-deep pose.
        if knee_angle > 165:
            state["too_deep_blocked"] = False

        # UP detection (standing)
        if knee_angle > 165:
            state["hold_count"] = state.get("hold_count", 0) + 1
            if state["hold_count"] >= CONFIRM_FRAMES_SHORT:
                if state["stage"] == "down":
                    state["stage"] = "up"
                    _set_voice(state, "Bend your knees")
                _set_feedback(state, "BEND YOUR KNEES", (0, 255, 0), "#00ff00")
                state["hold_count"] = 0
        # MID range — encourage lower
        elif 135 < knee_angle <= 165:
            state["hold_count"] = 0
            _set_feedback(state, "GO DOWN", (0, 255, 255), "#00ffff")
            _set_voice(state, "Go down")
        # DEEP squat — confirm before counting
        elif knee_angle <= 135 and not too_deep and not state.get("too_deep_blocked", False):
            state["hold_count"] = state.get("hold_count", 0) + 1
            if state["hold_count"] >= CONFIRM_FRAMES_MED:
                if state["stage"] == "up":
                    state["reps"] += 1
                    _cooldown(state, 1.2)
                    _set_voice(state, "Squat counted")
                state["stage"] = "down"
                _set_feedback(state, "EXCELLENT DEPTH", (255, 255, 0), "#ffff00")
                state["hold_count"] = 0
        # Expose debug metrics for squats to help diagnose false counts
        state["debug"] = {
            "knee_angle": round(knee_angle, 2),
            "hand_dist": round(hand_dist, 3),
            "is_at_chest": is_at_chest,
            "hold_count": state.get("hold_count", 0),
            "stage": state.get("stage", "unknown"),
        }
    except:
        pass


# ─────────────────────────────────────────────
# ROUTER — exercise name → logic function
# ─────────────────────────────────────────────
EXERCISE_LOGIC_MAP = {
    'jumping_jacks': jumping_jacks_logic,
    'lunges':        lunges_logic,
    'pushups':       pushups_logic,
    'squats':        squats_logic,
}

EXERCISE_META = {
    'jumping_jacks': {
        'display_name': 'Jumping Jacks',
        'icon': '🏃',
        'description': 'Full body cardio workout',
        'muscles': 'Full Body, Cardio',
        'difficulty': 'Beginner',
        'initial_stage': 'down',
    },
    'lunges': {
        'display_name': 'Lunges',
        'icon': '🦵',
        'description': 'Lower body strength exercise',
        'muscles': 'Quads, Glutes, Hamstrings',
        'difficulty': 'Intermediate',
        'initial_stage': 'up',
    },
    'pushups': {
        'display_name': 'Push Ups',
        'icon': '💪',
        'description': 'Upper body strength exercise',
        'muscles': 'Chest, Triceps, Shoulders',
        'difficulty': 'Intermediate',
        'initial_stage': 'up',
    },
    'squats': {
        'display_name': 'Squats',
        'icon': '🏋️',
        'description': 'Lower body power exercise',
        'muscles': 'Quads, Glutes, Core',
        'difficulty': 'Beginner',
        'initial_stage': 'up',
    },
}


def run_exercise_logic(exercise_key, lm, state):
    fn = EXERCISE_LOGIC_MAP.get(exercise_key)
    if fn:
        fn(lm, state)
