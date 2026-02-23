import threading
import time
import json
import os
from pynput import mouse, keyboard
from utils.logger import logger
import collections

class ShadowModeRecorder:
    def __init__(self, history_len=20, match_threshold=3):
        self.action_history = collections.deque(maxlen=history_len)
        self.match_threshold = match_threshold
        self.is_recording = False
        self.listener_thread = None
        self.mouse_listener = None
        self.keyboard_listener = None
        self.last_action_time = time.time()
        
        # Buffer for detecting patterns
        # Stores sequences of (ActionType, Target/Details)
        self.pattern_buffer = [] 
        
    def start(self):
        if self.is_recording:
            return
            
        logger.info("Starting Shadow Mode Recorder...")
        self.is_recording = True
        
        self.mouse_listener = mouse.Listener(on_click=self.on_click)
        self.keyboard_listener = keyboard.Listener(on_release=self.on_release)
        
        self.mouse_listener.start()
        self.keyboard_listener.start()
        
    def stop(self):
        if not self.is_recording:
            return
            
        logger.info("Stopping Shadow Mode Recorder...")
        self.is_recording = False
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
            
    def on_click(self, x, y, button, pressed):
        if not pressed:
            return
        
        action = {"type": "click", "x": x, "y": y, "button": str(button), "time": time.time()}
        self._record_action(action)
        
    def on_release(self, key):
        try:
            k = key.char
        except AttributeError:
            k = str(key)
            
        action = {"type": "keypress", "key": k, "time": time.time()}
        self._record_action(action)

    def _record_action(self, action):
        # Debounce
        if time.time() - self.last_action_time < 0.1:
            return
        self.last_action_time = time.time()

        self.action_history.append(action)
        self._detect_patterns()

    def _detect_patterns(self):
        # Simplified pattern detection:
        # Check if the last N actions match the previous N actions
        # This is a naive implementation for the prototype
        
        history = list(self.action_history)
        if len(history) < 6:
            return

        # Check for simple repetition of last 3 actions
        last_3 = history[-3:]
        prev_3 = history[-6:-3]
        
        # Approximate matching (ignore exact timestamps)
        if self._actions_match(last_3, prev_3):
            logger.info("Shadow Mode: Repetitive task detected! (3x pattern)")
            # In a real app, this would trigger a UI notification
            # For now, we log it heavily
            logger.info(f"SUGGESTION: I've learned how to do this sequence: {[a['type'] for a in last_3]}. Want me to take over?")

    def _actions_match(self, seq1, seq2):
        if len(seq1) != len(seq2):
            return False
        
        for a, b in zip(seq1, seq2):
            if a['type'] != b['type']:
                return False
            # For clicks, allow some pixel tolerance
            if a['type'] == 'click':
                if abs(a['x'] - b['x']) > 50 or abs(a['y'] - b['y']) > 50:
                    return False
            # For keys, must be exact
            if a['type'] == 'keypress':
                if a['key'] != b['key']:
                    return False
        return True

if __name__ == "__main__":
    recorder = ShadowModeRecorder()
    recorder.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        recorder.stop()
