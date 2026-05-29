import os
import json
from dotenv import load_dotenv
import anthropic

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
        """

    def evaluate_loc(self, lat: float, lon: float):
        pass

if __name__ == "__main__":
    agent = SupervisorAgent()
