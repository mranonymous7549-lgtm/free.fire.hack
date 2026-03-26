import cv2
import numpy as np
import pyautogui
import mss
import time
import threading
from pynput import mouse, keyboard
import win32api
import win32con

class FreeFireAimbot:
    def __init__(self):
        self.running = False
        self.triggered = False
        self.fov = 150  # Field of view in pixels
        self.sensitivity = 2.0  # Aiming speed multiplier
        self.headshot_threshold = 0.85
        self.confidence = 0.7
        
        # Free Fire enemy color range (head/body detection)
        # These HSV ranges target enemy outlines and heads
        self.lower_red1 = np.array([0, 120, 70])
        self.upper_red1 = np.array([10, 255, 255])
        self.lower_red2 = np.array([170, 120, 70])
        self.upper_red2 = np.array([180, 255, 255])
        
        self.lower_purple = np.array([130, 100, 100])  # Character glow
        self.upper_purple = np.array([160, 255, 255])
        
        # Screen capture setup
        self.sct = mss.mss()
        self.monitor = {"top": 0, "left": 0, "width": 1920, "height": 1080}
        
        # Load Free Fire specific templates (you'll need to capture these)
        self.head_template = self.load_template("head_template.png")
        self.body_template = self.load_template("body_template.png")
        
        print("Free Fire Aimbot initialized. Press F1 to toggle, F2 to exit.")

    def load_template(self, filename):
        """Load template images for matching"""
        try:
            template = cv2.imread(filename, 0)
            return template
        except:
            # Create dummy template if file not found
            print(f"Template {filename} not found. Using color detection only.")
            return None

    def capture_screen(self):
        """Fast screen capture using mss"""
        screenshot = self.sct.grab(self.monitor)
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img

    def detect_enemies(self, frame):
        """Detect enemies using color + template matching"""
        targets = []
        
        # Convert to HSV for better color detection
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Enemy color masks (Free Fire specific)
        mask1 = cv2.inRange(hsv, self.lower_red1, self.upper_red1)
        mask2 = cv2.inRange(hsv, self.lower_red2, self.upper_red2)
        mask3 = cv2.inRange(hsv, self.lower_purple, self.upper_purple)
        
        mask = mask1 + mask2 + mask3
        
        # Morphological operations to clean up noise
        kernel = np.ones((3,3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        screen_center_x, screen_center_y = frame.shape[1]//2, frame.shape[0]//2
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 200:  # Filter small noise
                x, y, w, h = cv2.boundingRect(contour)
                center_x = x + w//2
                center_y = y + h//2
                
                # Calculate distance from crosshair
                distance = np.sqrt((center_x - screen_center_x)**2 + (center_y - screen_center_y)**2)
                
                # Prioritize head level (upper body)
                if center_y < screen_center_y + 100:  # Head/upper body priority
                    priority = 1.0
                else:
                    priority = 0.8
                
                targets.append({
                    'x': center_x,
                    'y': center_y,
                    'distance': distance,
                    'size': area,
                    'priority': priority
                })
        
        # Template matching backup (if templates available)
        if self.head_template is not None:
            targets.extend(self.template_match(frame, self.head_template, "head"))
        if self.body_template is not None:
            targets.extend(self.template_match(frame, self.body_template, "body"))
        
        return sorted(targets, key=lambda x: x['distance'])[:3]  # Top 3 closest

    def template_match(self, frame, template, target_type):
        """Template matching for precise detection"""
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        res = cv2.matchTemplate(gray_frame, template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= self.confidence)
        
        targets = []
        for pt in zip(*loc[::-1]):
            center_x = pt[0] + template.shape[1]//2
            center_y = pt[1] + template.shape[0]//2
            distance = np.sqrt((center_x - frame.shape[1]//2)**2 + 
                             (center_y - frame.shape[0]//2)**2)
            priority = 1.0 if target_type == "head" else 0.9
            targets.append({
                'x': center_x, 'y': center_y, 'distance': distance,
                'size': template.shape[0]*template.shape[1],
                'priority': priority
            })
        return targets

    def smooth_aim(self, target_x, target_y):
        """Smooth mouse movement to avoid detection"""
        current_x, current_y = pyautogui.position()
        
        dx = (target_x - current_x) * self.sensitivity
        dy = (target_y - current_y) * self.sensitivity
        
        # Limit max movement per frame
        max_move = 15
        dx = np.clip(dx, -max_move, max_move)
        dy = np.clip(dy, -max_move, max_move)
        
        # Human-like curve movement
        steps = int(max(abs(dx), abs(dy)) / 3) + 1
        for i in range(steps):
            move_x = current_x + dx * (i+1)/steps + np.random.normal(0, 1)
            move_y = current_y + dy * (i+1)/steps + np.random.normal(0, 1)
            win32api.SetCursorPos((int(move_x), int(move_y)))
            time.sleep(0.001)

    def trigger_bot(self):
        """Auto-fire when on target"""
        if self.triggered:
            # Simulate left mouse hold (Free Fire ADS)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def on_key(self, key):
        """Keyboard controls"""
        try:
            if key == keyboard.Key.f1:
                self.running = not self.running
                status = "ON" if self.running else "OFF"
                print(f"Aimbot {status}")
            elif key == keyboard.Key.f2:
                self.running = False
                self.triggered = False
                print("Aimbot stopped.")
                return False
            elif key == keyboard.Key.f3:
                self.triggered = not self.triggered
                status = "ON" if self.triggered else "OFF"
                print(f"Trigger bot {status}")
        except:
            pass

    def run(self):
        """Main aimbot loop"""
        listener = keyboard.Listener(on_press=self.on_key)
        listener.start()
        
        while True:
            if not self.running:
                time.sleep(0.01)
                continue
                
            frame = self.capture_screen()
            targets = self.detect_enemies(frame)
            
            if targets:
                best_target = targets[0]
                
                # FOV check
                center_x, center_y = frame.shape[1]//2, frame.shape[0]//2
                if best_target['distance'] < self.fov:
                    self.smooth_aim(best_target['x'], best_target['y'])
                    
                    # Trigger bot
                    if self.triggered:
                        self.trigger_bot()
            
            time.sleep(0.01)  # 100 FPS loop

if __name__ == "__main__":
    # Disable PyAutoGUI failsafe
    pyautogui.FAILSAFE = False
    
    aimbot = FreeFireAimbot()
    aimbot.run()