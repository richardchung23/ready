import os
import json
from dotenv import load_dotenv
import anthropic
from data_tool import fetch_location_data
from analysis_tool import calculate_los

load_dotenv()

class SupervisorAgent:
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

        self.tools = [
            {
                "name": "fetch_location_data",
                "description": "Fetches ground elevation, canopy cover, and canopy height for a given location from the database and raster sources.",
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
                "description": "Calculates if physical obstacles block the 20-degree satellite line of sight. Use this to determine the broadband risk tier.",
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

    def evaluate_location(self, prompt_text: str) -> str:
        print(f"Processing request...")
        messages = [{"role": "user", "content": prompt_text}]

        response = self.client.messages.create(
            model = self.model,
            system = self.prompt,
            max_tokens = 1000,
            tools=self.tools,
            messages = messages
        )

        MAX_ITERATION = 3
        iterations = 0

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

            if tool_name == "fetch_location_data":
                result = fetch_location_data(tool_inputs.get("location_id"))
            elif tool_name == "calculate_los":
                result = calculate_los(**tool_inputs)
            else:
                result = {"error": f"Unknown tool requested: {tool_name}"}

            messages.append({"role": "assistant", "content": response.content})

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

            response = self.client.messages.create(
                model = self.model,
                system = self.prompt,
                max_tokens = 1000,
                tools=self.tools,
                messages = messages
            )    

        if iterations >= MAX_ITERATION:
            return "Analysis failed: Agent reached max number of iterations"
        
        return response.content[0].text


if __name__ == "__main__":
    agent = SupervisorAgent()
    
    test_prompt = (
        "Please run a full  risk assessment for location id: 40023115"
    )
    
    final_assessment = agent.evaluate_location(test_prompt)
    print("================ FINAL OFFICER EXPLANATION ================")
    print(final_assessment)
