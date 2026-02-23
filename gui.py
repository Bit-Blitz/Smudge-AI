import customtkinter as ctk
import threading
import queue
import time
import os
import sys
import speech_recognition as sr
import uiautomation as auto
from PIL import Image
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from main import Agent
from utils.logger import logger

# --- Configuration ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class AegisApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("Aegis OS - Autonomous Desktop Agent")
        self.geometry("1100x700")
        
        # Configure Grid Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Initialize Agent
        self.agent = Agent()
        self.msg_queue = queue.Queue()
        self.is_running = False

        # --- Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="🛡️ Aegis OS", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.status_label = ctk.CTkLabel(self.sidebar_frame, text="Status: IDLE", text_color="gray")
        self.status_label.grid(row=1, column=0, padx=20, pady=10)

        # Toggles
        self.voice_var = ctk.BooleanVar(value=False)
        self.voice_switch = ctk.CTkSwitch(self.sidebar_frame, text="Voice Input", variable=self.voice_var, command=self.toggle_voice_ui)
        self.voice_switch.grid(row=2, column=0, padx=20, pady=10, sticky="w")

        self.vision_var = ctk.BooleanVar(value=False)
        self.vision_switch = ctk.CTkSwitch(self.sidebar_frame, text="Screen Vision", variable=self.vision_var)
        self.vision_switch.grid(row=3, column=0, padx=20, pady=10, sticky="w")

        # Stop Button
        self.stop_button = ctk.CTkButton(self.sidebar_frame, text="Stop Agent", fg_color="red", hover_color="darkred", command=self.stop_agent)
        self.stop_button.grid(row=4, column=0, padx=20, pady=20)

        # --- Main Chat Area ---
        self.chat_frame = ctk.CTkScrollableFrame(self, corner_radius=15)
        self.chat_frame.grid(row=0, column=1, padx=20, pady=(20, 0), sticky="nsew")

        # --- Input Area ---
        self.input_frame = ctk.CTkFrame(self, corner_radius=15)
        self.input_frame.grid(row=1, column=1, padx=20, pady=20, sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkEntry(self.input_frame, placeholder_text="Type your command here...", height=40, font=("Arial", 14))
        self.entry.grid(row=0, column=0, padx=(10, 10), pady=10, sticky="ew")
        self.entry.bind("<Return>", self.on_enter_pressed)

        self.send_button = ctk.CTkButton(self.input_frame, text="🚀 Send", width=100, height=40, command=self.send_command)
        self.send_button.grid(row=0, column=1, padx=(0, 10), pady=10)

        self.mic_button = ctk.CTkButton(self.input_frame, text="🎤", width=40, height=40, command=self.listen_voice)
        # Initially hidden if voice is off
        if self.voice_var.get():
             self.mic_button.grid(row=0, column=2, padx=(0, 10), pady=10)

        # Start checking queue for updates
        self.check_queue()
        
        # Welcome Message
        self.add_message("System", "Welcome to Aegis OS. I am ready to assist you.")

    def toggle_voice_ui(self):
        if self.voice_var.get():
            self.mic_button.grid(row=0, column=2, padx=(0, 10), pady=10)
        else:
            self.mic_button.grid_forget()

    def on_enter_pressed(self, event):
        self.send_command()

    def send_command(self):
        text = self.entry.get()
        if not text.strip():
            return
        
        self.entry.delete(0, "end")
        self.process_command(text)

    def listen_voice(self):
        if not self.voice_var.get():
            return
            
        self.status_label.configure(text="Status: LISTENING...", text_color="#3B8ED0")
        
        def listen_thread():
            r = sr.Recognizer()
            try:
                with sr.Microphone() as source:
                    # Adjust for ambient noise
                    r.adjust_for_ambient_noise(source, duration=0.5)
                    audio = r.listen(source, timeout=5, phrase_time_limit=10)
                    text = r.recognize_google(audio)
                    self.msg_queue.put(("voice_input", text))
            except sr.WaitTimeoutError:
                 self.msg_queue.put(("error", "Listening timed out."))
            except Exception as e:
                self.msg_queue.put(("error", f"Voice error: {e}"))
                
        threading.Thread(target=listen_thread, daemon=True).start()

    def process_command(self, text):
        self.add_message("User", text)
        self.is_running = True
        self.status_label.configure(text="Status: RUNNING", text_color="#2CC985")
        
        # Prepare context
        context = {}
        if self.vision_var.get():
            context["use_vision"] = True
            self.add_message("System", "👁️ Capturing screen context...")

        # Run in thread
        threading.Thread(target=self.run_agent_thread, args=(text, context), daemon=True).start()

    def run_agent_thread(self, text, context):
        try:
            with auto.UIAutomationInitializerInThread(debug=False):
                goal = text
                steps = 0
                max_steps = 15
                
                while self.is_running and steps < max_steps:
                    result = self.agent.run_step(goal, context=context)
                    
                    # Log result
                    if isinstance(result, dict) and "status" in result:
                         status = result["status"]
                         self.msg_queue.put(("agent_response", result))
                         
                         if status == "done":
                             self.msg_queue.put(("info", "Goal achieved successfully."))
                             # IMPORTANT: Break the loop on success to avoid repetition
                             break
                         elif status == "error":
                             self.msg_queue.put(("error", "Agent encountered an error."))
                             break
                    else:
                        # Fallback if result isn't structured as expected
                        self.msg_queue.put(("agent_response", str(result)))
                        
                    steps += 1
                    time.sleep(1)
                
                self.is_running = False # Ensure flag is reset
                self.msg_queue.put(("status_update", "IDLE"))
                
        except Exception as e:
            self.msg_queue.put(("error", str(e)))

    def stop_agent(self):
        self.is_running = False
        self.status_label.configure(text="Status: STOPPING...", text_color="orange")
        self.add_message("System", "Stopping agent after current step...")

    def check_queue(self):
        try:
            while True:
                msg_type, content = self.msg_queue.get_nowait()
                
                if msg_type == "agent_response":
                    # Parse result
                    if isinstance(content, dict):
                        message = content.get("message", str(content))
                        status = content.get("status", "unknown")
                        self.add_message("Aegis", f"[{status.upper()}] {message}")
                        
                        if "log" in content and "plan" in content["log"]:
                            plan = content["log"]["plan"]
                            if isinstance(plan, dict):
                                plan_action = plan.get("action", "unknown")
                                self.add_message("Debug", f"Executed: {plan_action}", is_debug=True)
                    else:
                        self.add_message("Aegis", str(content))

                elif msg_type == "status_update":
                    if content == "IDLE":
                        self.is_running = False
                        self.status_label.configure(text="Status: IDLE", text_color="gray")

                elif msg_type == "info":
                     self.add_message("System", str(content))
                        
                elif msg_type == "voice_input":
                    self.process_command(content)
                    
                elif msg_type == "error":
                    self.is_running = False
                    self.status_label.configure(text="Status: ERROR", text_color="red")
                    self.add_message("Error", str(content))
                    
        except queue.Empty:
            pass
            
        self.after(100, self.check_queue)

    def add_message(self, sender, text, is_debug=False):
        # Create a frame for the message
        msg_frame = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        msg_frame.pack(fill="x", pady=5, padx=10)
        
        if sender == "User":
            bubble_color = "#2b2d42" # Dark Blue
            align = "e" # East (Right)
            text_color = "white"
            anchor = "e"
        elif sender == "Aegis":
            bubble_color = "#3d348b" # Purple
            align = "w" # West (Left)
            text_color = "white"
            anchor = "w"
        elif sender == "System":
            bubble_color = "#212529" # Dark Gray
            align = "center"
            text_color = "#adb5bd"
            anchor = "center"
        elif sender == "Error":
            bubble_color = "#721c24" # Red
            align = "center"
            text_color = "#f8d7da"
            anchor = "center"
        else: # Debug
            bubble_color = "transparent"
            align = "w"
            text_color = "gray"
            anchor = "w"

        if is_debug:
            label = ctk.CTkLabel(msg_frame, text=f"[{sender}] {text}", text_color="gray", font=("Consolas", 10), wraplength=600, justify="left")
            label.pack(anchor="w")
        else:
            # Bubble
            bubble = ctk.CTkLabel(
                msg_frame, 
                text=f"{text}", 
                fg_color=bubble_color, 
                text_color=text_color, 
                corner_radius=15,
                padx=15, 
                pady=10,
                wraplength=500,
                justify="left",
                font=("Arial", 14) if sender in ["User", "Aegis"] else ("Arial", 12)
            )
            # Alignment trick
            if align == "e":
                bubble.pack(anchor="e")
            elif align == "center":
                bubble.pack(anchor="center")
            else:
                bubble.pack(anchor="w")
            
            # Sender label (tiny)
            if sender in ["User", "Aegis"]:
                sender_lbl = ctk.CTkLabel(msg_frame, text=sender, font=("Arial", 10), text_color="gray")
                if align == "e":
                    sender_lbl.pack(anchor="e", padx=5)
                else:
                    sender_lbl.pack(anchor="w", padx=5)

        # Auto-scroll to bottom
        # CTkScrollableFrame doesn't have easy programmatic scroll, but packing new items usually pushes it down.
        # Ideally we'd scroll to bottom here.
        # self.chat_frame._parent_canvas.yview_moveto(1.0) # Hacky way for CTk
        
if __name__ == "__main__":
    app = AegisApp()
    app.mainloop()
