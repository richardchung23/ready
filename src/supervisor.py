import os
import json
from dotenv import load_dotenv
import anthropic
from data_tool import calculate_los

load_dotenv()

class SupervisorAgent:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_KEY"))
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
                "name": "calculate_los",
                "description": "Calculates if physical obstacles block the 20-degree satellite line of sight. Use this to determine the broadband risk tier.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "dish_elev": {"type": "number", "description": "Ground elevation at the dish location in meters."},
                        "obstruction_elev": {"type": "number", "description": "Ground elevation of the nearest obstacle in meters."},
                        "canopy_height": {"type": "number", "description": "Height of the tree canopy in meters."},
                        "obstruction_dist": {"type": "number", "description": "Distance from the dish to the obstacle in meters."}
                    },
                    "required": ["dish_elev", "obstruction_elev", "canopy_height", "obstruction_dist"]
                }
            }
        ]

    def evaluate_loc(self, prompt_text: str) -> str:
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

            if tool_name == "calculate_los":
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
        
        return result.content[0].text


if __name__ == "__main__":
    agent = SupervisorAgent()
