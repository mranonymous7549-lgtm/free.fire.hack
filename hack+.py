import cv2
import numpy as np
import pyautogui
import mss
import time
import threading
from pynput import mouse, keyboard
import win32api
import win32con
import pymem
import pymem.process
from ctypes import wintypes, windll, byref, POINTER
import struct

class FreeFireCheat:
    def __init__(self):
        self.running = False
        self.aimbot_active = False
        self.speedhack_active = False
        self.triggerbot_active = False
        
        # Aimbot settings
        self.fov = 150
        self.sensitivity = 2.0
        self.confidence = 0.7
        
        # Free Fire enemy colors (HSV)
        self.enemy_colors = [
            (np.array([0, 120, 70]), np.array([10, 255, 255])),      # Red1
            (np.array([170, 120, 70]), np.array([180, 255, 255])),  # Red2
            (np.array([130, 100, 100]), np.array([160, 255, 255]))  # Purple glow
        ]
        
        self.sct = mss.mss()
        self.monitor = {"top": 0, "left": 0, "width": 1920, "height": 1080}
        
        # Memory hack setup
        self.pm = None
        self.base_address = None
        self.speed_multiplier = 3.0  # 3x speed
        
        print("Free Fire Aimbot + Speed Hack initialized")
        print("F1: Toggle Aimbot | F2: Toggle Speed Hack | F3: Trigger Bot | F4: Exit")

    def find_free_fire_process(self):
        """Find Free Fire process"""
        for proc in pymem.process.process_list():
            if "FreeFire" in proc.szExeFile.lower() or "ffarene" in proc.szExeFile.lower():
                try:
                    self.pm = pymem.Pymem(proc.szExeFile)
                    self.base_address = self.pm.base_address
                    print(f"Free Fire found: {proc.szExeFile}")
                    return True
                except:
                    continue
        print("Free Fire process not found")
        return False

    def speed_hack(self):
        """Memory-based speed hack using WriteProcessMemory"""
        if not self.pm:
            return
            
        try:
            # Common Free Fire movement speed offsets (these need adjustment)
            # These are example offsets - you'll need to find actual ones with Cheat Engine
            speed_offsets = [0x1A2B3C4, 0x2B4C5D6, 0x3C5D6E7]  # PLACEHOLDER
            
            for offset in speed_offsets:
                try:
                    address = self.pm.base_address + offset
                    original_value = self.pm.read_float(address)
                    new_value = original_value * self.speed_multiplier
                    self.pm.write_float(address, new_value)
                except:
                    continue
                    
            # Alternative: Direct velocity manipulation
            self.write_movement_multipliers()
                    
        except Exception as e:
            print(f"Speed hack error: {e}")

    def write_movement_multipliers(self):
        """Write movement multipliers directly"""
        try:
            # Player movement structure (X, Y, Z velocity)
            player_base = self.find_player_base()
            if player_base:
                # X, Y, Z movement speed
                self.pm.write_float(player_base + 0x40, 15.0)  # X speed
                self.pm.write_float(player_base + 0x44, 15.0)  # Y speed
                self.pm.write_float(player_base + 0x48, 10.0)  # Z speed (jump)
        except:
            pass

    def find_player_base(self):
        """Scan for player base address using AOB pattern"""
        try:
            # Free Fire player object pattern (example)
            pattern = b"\x48\x8B\x05\x00\x00\x00\x00\x48\x85\xC0\x74\x0F\x48\x8B\x40\x08"
            found = self.pm.pattern_scan_module(self.pm.process_handle, pattern)
            return found
        except:
            return None

    def capture_screen(self):
        frame = self.sct.grab(self.monitor)
        img = np.array(frame)
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def detect_enemies(self, frame):
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        targets = []
        
        for lower, upper in self.enemy_colors:
            mask = cv2.inRange(hsv, lower, upper)
            kernel = np.ones((3,3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 300:
                    x, y, w, h = cv2.boundingRect(contour)
                    cx, cy = x + w//2, y + h//2
                    
                    distance = np.sqrt((cx - frame.shape[1]//2)**2 + (cy - frame.shape[0]//2)**2)
                    
                    targets.append({
                        'x': cx, 'y': cy, 'distance': distance, 'size': area,
                        'priority': 1.0 if cy < frame.shape[0]//2 else 0.8
                    })
        
        return sorted(targets, key=lambda x: x['distance'])[:2]

    def smooth_aim(self, target_x, target_y):
        current_x, current_y = pyautogui.position()
        dx = (target_x - current_x) * self.sensitivity * 0.1
        dy = (target_y - current_y) * self.sensitivity * 0.1
        
        max_move = 20
        dx = np.clip(dx, -max_move, max_move)
        dy = np.clip(dy, -max_move, max_move)
        
        steps = 8
        for i in range(steps):
            move_x = current_x + dx * (i+1)/steps + np.random.normal(0, 0.5)
            move_y = current_y + dy * (i+1)/steps + np.random.normal(0, 0.5)
            win32api.SetCursorPos((int(move_x), int(move_y)))
            time.sleep(0.0005)

    def trigger_shot(self):
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.03)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def on_key(self, key):
        try:
            if key == keyboard.Key.f1:
                self.aimbot_active = not self.aimbot_active
                print(f"Aimbot: {'ON' if self.aimbot_active else 'OFF'}")
            elif key == keyboard.Key.f2:
                self.speedhack_active = not self.speedhack_active
                if self.speedhack_active:
                    self.find_free_fire_process()
                print(f"Speed Hack: {'ON' if self.speedhack_active else 'OFF'}")
            elif key == keyboard.Key.f3:
                self.triggerbot_active = not self.triggerbot_active
                print(f"Trigger Bot: {'ON' if self.triggerbot_active else 'OFF'}")
            elif key == keyboard.Key.f4:
                self.running = False
                print("Cheat stopped.")
                return False
        except:
            pass

    def aimbot_thread(self):
        while self.running:
            if self.aimbot_active:
                frame = self.capture_screen()
                targets = self.detect_enemies(frame)
                
                if targets and targets[0]['distance'] < self.fov:
                    target = targets[0]
                    self.smooth_aim(target['x'], target['y'])
                    
                    if self.triggerbot_active:
                        self.trigger_shot()
            time.sleep(0.008)  # ~125 FPS

    def speedhack_thread(self):
        while self.running:
            if self.speedhack_active and self.pm:
                self.speed_hack()
            time.sleep(0.016)  # 60Hz update

    def run(self):
        pyautogui.FAILSAFE = False
        self.running = True
        
        # Start threads
        aim_thread = threading.Thread(target=self.aimbot_thread, daemon=True)
        speed_thread = threading.Thread(target=self.speedhack_thread, daemon=True)
        
        aim_thread.start()
        speed_thread.start()
        
        # Keyboard listener
        listener = keyboard.Listener(on_press=self.on_key)
        listener.start()
        
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.running = False

if __name__ == "__main__":
    cheat = FreeFireCheat()
    cheat.run()