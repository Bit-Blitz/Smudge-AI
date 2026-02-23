import time
import os
import sys
import logging
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from utils.logger import logger
from utils.database_manager import DatabaseManager
from skills.structured_perception import StructuredPerception
from skills.groq_planner import GroqPlanner
from skills.executor import Executor
from skills.verifier import Verifier
from skills.vision_fallback import VisionFallback
from skills.openclaw_client import OpenClawClient

class Agent:
    def __init__(self):
        logger.info("Initializing Aegis OS Agent...")
        self.perception = StructuredPerception()
        self.db = DatabaseManager()
        self.planner = GroqPlanner()
        self.executor = Executor()
        self.verifier = Verifier()
        self.vision_fallback = VisionFallback()
        self.openclaw = OpenClawClient()
        self.max_steps = 25
        self.history = []

    def run_step(self, goal, context=None):
        """Executes a single step of the agent loop."""
        step_log = {"timestamp": time.time(), "goal": goal}
        
        # 1. Perception
        logger.info("Step 1: Perception")
        current_state = self.perception.capture_state()
        
        # Incorporate Visual Context if requested
        if context and context.get("use_vision"):
            logger.info("Visual context requested. Analyzing screen...")
            visual_description = self.vision_fallback.analyze_screen(
                query=f"Analyze the screen to help achieve this goal: {goal}. Describe active windows, buttons, and layout."
            )
            current_state["visual_context"] = visual_description
            logger.info(f"Visual context added: {visual_description[:100]}...")

        step_log["perception"] = current_state
        
        # 2. Planning
        logger.info("Step 2: Planning")
        # Pass history to planner so it knows what it just did
        plan = self.planner.plan(goal, current_state, history=self.history)

        step_log["plan"] = plan
        
        if not plan or "error" in plan:
            logger.error(f"Planning failed: {plan}")
            return {"status": "error", "message": "Planning failed", "log": step_log}
            
        # Check if plan is to terminate or wait
        if plan.get("action") == "wait" or plan.get("action") == "done":
            logger.info("Plan indicates completion or waiting.")
            # Important: Add to history so future steps know we finished
            self.history.append({"status": "done", "plan": plan})
            return {"status": "done", "message": "Task completed", "log": step_log}

        # CRITICAL: Prevent executing the exact same action twice in a row if it was successful
        if self.history:
            last_step = self.history[-1]
            # FIX: Handle inconsistent history structure (done/failed vs success log)
            # 'success' has plan inside 'log', 'done'/'failed' has plan at top level
            last_plan = last_step.get("plan") or last_step.get("log", {}).get("plan", {})
            last_status = last_step.get("status")
            
            # If action, target, strategy match, and it was successful, assume we are looping
            # Note: We are now looser on content matching because sometimes LLM generates slightly different whitespace
            # or comments, but the INTENT is identical.
            
            # 1. Check strict action/target match
            is_same_action = (
                last_plan.get("action") == plan.get("action") and 
                last_plan.get("target") == plan.get("target")
            )
            
            # 2. If it's a write_file action, check if we JUST did this
            if is_same_action and plan.get("action") == "write_file" and last_status == "success":
                 logger.warning(f"Duplicate write_file action for '{plan.get('target')}' detected! forcing 'done'.")
                 return {"status": "done", "message": "Loop detected (duplicate write), task assumed complete", "log": step_log}
                 
            # 3. If it's a play_media action, check if we JUST did this
            if is_same_action and plan.get("action") == "play_media" and last_status == "success":
                 logger.warning(f"Duplicate play_media action for '{plan.get('target')}' detected! forcing 'done'.")
                 return {"status": "done", "message": "Loop detected (duplicate media play), task assumed complete", "log": step_log}
                 
            # 4. General loop detection for other actions
            if (last_status == "success" and is_same_action and 
                last_plan.get("strategy") == plan.get("strategy")):
                
                logger.warning("Duplicate action detected! Planner is looping. Forcing 'done'.")
                return {"status": "done", "message": "Loop detected, task assumed complete", "log": step_log}

        # 3. Execution
        logger.info("Step 3: Execution")
        execution_result = self.executor.execute_plan(plan)
        step_log["execution"] = execution_result
        
        if not execution_result:
            logger.warning("Execution failed. Triggering Vision Fallback?")
            # Here logic for fallback could be added
            # For now, just return failure
            self.history.append({"status": "failed", "plan": plan})
            return {"status": "failed", "message": "Execution failed", "log": step_log}
            
        # 4. Verification
        logger.info("Step 4: Verification")
        # Wait a bit for UI to update
        time.sleep(1)
        new_state = self.perception.capture_state()
        verified = self.verifier.verify(plan, current_state, new_state)
        step_log["verification"] = verified
        
        if verified:
            logger.info("Action verified successfully.")
            result = {"status": "success", "message": "Step completed", "log": step_log}
        else:
            logger.warning("Verification failed.")
            result = {"status": "retry", "message": "Verification failed", "log": step_log}
            
        # Add to history
        self.history.append(result)
        
        # Log to Database
        self.db.log_step(
            goal=goal,
            plan=plan,
            status=result["status"],
            details=result.get("log")
        )
        
        return result

    def run_loop(self, goal):
        """Runs the agent loop until completion or max steps."""
        logger.info(f"Starting agent loop for goal: {goal}")
        steps = 0
        while steps < self.max_steps:
            logger.info(f"--- Step {steps + 1} ---")
            result = self.run_step(goal)
            # self.history.append(result)  <-- REMOVED: run_step already appends to history!
            
            if result["status"] == "done":
                logger.info("Goal achieved.")
                return "Goal achieved."
            elif result["status"] == "error":
                logger.error("Critical error in loop.")
                return f"Error: {result['message']}"
            elif result["status"] == "failed":
                logger.warning("Step failed, retrying...")
                # Simple retry logic
            
            steps += 1
            time.sleep(1)
            
        return "Max steps reached."

if __name__ == "__main__":
    agent = Agent()
    if len(sys.argv) > 1:
        goal = " ".join(sys.argv[1:])
    else:
        goal = "Open Notepad and type Hello World"
    
    print(agent.run_loop(goal))
