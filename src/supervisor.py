# supervisor.py
#
# Agentic Orchestration Layer
# This file acts as cognitive engine for interactive pipeline. It uses Claude 
# LLM to parse natural language requests, autonomously decide which technical 
# tools to use, and synthesize raw database and mathematical outputs into 
# plain-English risk assessments. It maintains a strict boundary between LLM 
# reasoning and deterministic code execution.

import os
import json
from dotenv import load_dotenv
import anthropic
from data_tool import fetch_location_data
from analysis_tool import calculate_los

# Safely resolve environment variables relative to this script's directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

# Autonomous reasoning agent that manages the LOS evaluation workflow
class SupervisorAgent:
    # Initializes Anthropic client, sets system prompt boundaries, and explicitly
    # defines JSON schemas for tool usage to prevent LLM hallucinations.
    def __init__(self):
        self.client = anthropic.Anthropic()
        self.model = "claude-haiku-4-5-20251001"

        self.prompt = """
        You are the primary Superviser Agent for a state broadband risk pipeline.
        Your goal is to determine if a location is at risk of environmental obstruction.
        You manage a sequence of specialized tools. Do not hallucinate data.
        Base all final assessments stricly on the outputs from the tools. 
        Finally, translate the final risk tier and mathematical reason into a 
        plain English explanation suitable for a non-technical state broadband officer.
        """

        # Tool definitions: these schemas force LLM to provide exact inputs
        self.tools = [
            {
                "name": "fetch_location_data",
                "description": "Retrieves pre-computed geospatial evaluation parameters for a given location UUID from the database, including ground elevation, tree canopy cover percentage, and total obstruction height.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location_id": {"type": "string"}
                    },
                    "required": ["location_id"]
                }
            },
            {
                "name": "calculate_los",
                "description": (
                    "Calculates if physical obstacles block the 20-degree satellite line of sight. "
                    "CRITICAL: Map the outputs from fetch_location_data to this tool's parameters exactly as follows: "
                    "1. Map 'elevation' to 'dish_elev'. "
                    "2. Map 'obstruction_height' to 'obstruction_elev'. "
                    "3. Always set 'canopy_height' to 0 (since tree height is already integrated into obstruction_elev). "
                    "4. Always default 'obstruction_dist' to 15.0 unless explicitly told otherwise."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "dish_elev": {"type": "number", "description": "Ground elevation at the dish location in meters."},
                        "obstruction_elev": {"type": "number", "description": "Ground elevation of the nearest obstacle in meters."},
                        "obstruction_dist": {"type": "number", "description": "Distance from the dish to the obstacle in meters."},
                        "canopy_height": {"type": "number", "description": "Height of the tree canopy in meters."}
                    },
                    "required": ["dish_elev", "obstruction_elev", "obstruction_dist", "canopy_height"]
                }
            }
        ]

    # Executes core reasoning loop. Routes user prompt to LLM, intercepts tool
    # requests, invokes Python functions, and feeds data back to LLM for a 
    # conversational synthesis
    #
    # Args:
    #   - prompt_text: Natural language query from user
    #
    # Returns:
    #   - str: Final assessment by LLM in plain English
    def evaluate_location(self, prompt_text: str) -> str:
        print(f"Processing request...")
        messages = [{"role": "user", "content": prompt_text}]

        # Initial call to LLM to interpret user's request
        response = self.client.messages.create(
            model = self.model,
            system = self.prompt,
            max_tokens = 1000,
            tools=self.tools,
            messages = messages
        )

        MAX_ITERATION = 3
        iterations = 0

        # Reasoning loop: Continue intercepting while LLM wants to use tools
        while response.stop_reason == "tool_use" and iterations < MAX_ITERATION:
            iterations += 1
            tool_use = next((block for block in response.content if block.type == "tool_use"), None)
            if tool_use is None:
                print("Warning: stop_reason was 'tool_use' but no tool block was found")
                break

            tool_name = tool_use.name
            tool_inputs = tool_use.input

            print(f"Supervisor routed to tool: {tool_name}")
            print(f"Inputs extracted: {json.dumps(tool_inputs)}\n")

            # Route to appropiate Python adapter based on LLM's request
            if tool_name == "fetch_location_data":
                result = fetch_location_data(tool_inputs.get("location_id"))
            elif tool_name == "calculate_los":
                result = calculate_los(**tool_inputs)
            else:
                result = {"error": f"Unknown tool requested: {tool_name}"}

            # Append LLM's tool requests to conversation history
            messages.append({"role": "assistant", "content": response.content})

            # Append actual result back so LLM can read it
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": json.dumps(result)
                    }
                ]
            })

            # Fire updated context back to LLM
            response = self.client.messages.create(
                model = self.model,
                system = self.prompt,
                max_tokens = 1000,
                tools=self.tools,
                messages = messages
            )    

        # Failsafe to prevent infinite API loops
        if iterations >= MAX_ITERATION:
            return "Analysis failed: Agent reached max number of iterations"
        
        return response.content[0].text


if __name__ == "__main__":
    agent = SupervisorAgent()
    print("==================================================")
    print(" READY BROADBAND RISK SUPERVISOR INITIALIZED")
    print(" Type 'exit' or 'quit' to close the application.")
    print("==================================================")

    while True:
        # Wait for user input
        user_input = input("\nEnter a Location ID to evaluate: ").strip()
        
        # Allow a clean exit
        if user_input.lower() in ['exit', 'quit']:
            print("Shutting down supervisor...")
            break
            
        # Guard against empty input
        if not user_input:
            continue
            
        # Wrap your input in the required context
        dynamic_prompt = f"Please run a full risk assessment for location id: {user_input}"
        
        # Run the agent and print the result
        final_assessment = agent.evaluate_location(dynamic_prompt)
        print("\n================ FINAL OFFICER EXPLANATION ================")
        print(final_assessment)
