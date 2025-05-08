"""
Base Agent class for the multi-agent recommendation system
"""

import sys
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable

# Add the parent directory to the system path
sys.path.append(str(Path(__file__).parent.parent.parent))
from smartshop.utils.database import Database
from smartshop.utils.llm import OllamaClient

class Agent:
    """Base Agent class for the multi-agent recommendation system."""
    
    def __init__(self, agent_id: str, name: str, description: str):
        """Initialize an agent.
        
        Args:
            agent_id: Unique identifier for the agent
            name: Descriptive name of the agent
            description: Description of the agent's purpose
        """
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.db = Database()
        self.llm = OllamaClient()
        self.tools = {}  # Dictionary of available tools
        self.memory_types = ["experiences", "observations", "plans", "reflections"]
        self.system_prompt = f"""You are {name}, an AI agent designed to {description}.
Your goal is to provide accurate and helpful responses based on your knowledge and tools.
Always think step-by-step and consider the context and history of the conversation."""
    
    def register_tool(self, name: str, func: Callable, description: str) -> None:
        """Register a tool that the agent can use.
        
        Args:
            name: Name of the tool
            func: Function to call when the tool is invoked
            description: Description of what the tool does
        """
        self.tools[name] = {
            "function": func,
            "description": description
        }
    
    def use_tool(self, tool_name: str, **kwargs) -> Any:
        """Use a registered tool.
        
        Args:
            tool_name: Name of the tool to use
            **kwargs: Arguments to pass to the tool
            
        Returns:
            The result of the tool execution
        """
        if tool_name not in self.tools:
            return f"Tool '{tool_name}' is not available."
        
        try:
            result = self.tools[tool_name]["function"](**kwargs)
            return result
        except Exception as e:
            return f"Error using tool '{tool_name}': {str(e)}"
    
    def store_memory(self, memory_type: str, memory_value: str, memory_key: Optional[str] = None) -> None:
        """Store a memory in the agent's memory.
        
        Args:
            memory_type: Type of memory (experiences, observations, plans, reflections)
            memory_value: Content of the memory
            memory_key: Optional key to identify the memory
        """
        if memory_type not in self.memory_types:
            raise ValueError(f"Invalid memory type: {memory_type}")
        
        if memory_key is None:
            memory_key = str(uuid.uuid4())
        
        # Get embedding for the memory
        embedding = self.llm.get_embedding(memory_value)
        
        # Store in database
        self.db.store_memory(
            agent_id=self.agent_id,
            memory_type=memory_type,
            memory_key=memory_key,
            memory_value=memory_value,
            embedding=json.dumps(embedding)
        )
    
    def retrieve_memory(self, memory_type: str, memory_key: Optional[str] = None) -> Any:
        """Retrieve memories from the agent's memory.
        
        Args:
            memory_type: Type of memory to retrieve
            memory_key: Optional key to identify a specific memory
            
        Returns:
            The retrieved memory or memories
        """
        if memory_type not in self.memory_types:
            raise ValueError(f"Invalid memory type: {memory_type}")
        
        result = self.db.retrieve_memory(
            agent_id=self.agent_id,
            memory_type=memory_type,
            memory_key=memory_key
        )
        
        return result
    
    def reflect(self, observations: str) -> str:
        """Reflect on observations and generate insights.
        
        Args:
            observations: Observations to reflect on
            
        Returns:
            The agent's reflections
        """
        prompt = f"""
        Based on the following observations, please reflect and generate insights:
        
        {observations}
        
        Think carefully about what these observations mean and what conclusions or actions might be appropriate.
        """
        
        reflection = self.llm.generate(prompt, system_prompt=self.system_prompt)
        
        # Store the reflection in memory
        self.store_memory("reflections", reflection)
        
        return reflection
    
    def plan(self, task: str) -> str:
        """Create a plan for a given task.
        
        Args:
            task: Task to plan for
            
        Returns:
            The agent's plan
        """
        prompt = f"""
        Please create a detailed step-by-step plan for the following task:
        
        {task}
        
        Think carefully about the best approach and break it down into clear, actionable steps.
        """
        
        plan = self.llm.generate(prompt, system_prompt=self.system_prompt)
        
        # Store the plan in memory
        self.store_memory("plans", plan, task)
        
        return plan
    
    def process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Process a message and generate a response.
        
        Args:
            message: Message to process
            context: Optional context information
            
        Returns:
            The agent's response
        """
        if context is None:
            context = {}
        
        # Format the message with context
        formatted_message = f"""
        Message: {message}
        
        Context: {json.dumps(context) if context else 'No additional context.'}
        
        Please respond to this message based on your expertise and the provided context.
        """
        
        # Generate a response using the LLM
        response = self.llm.generate(formatted_message, system_prompt=self.system_prompt)
        
        # Store the interaction in memory
        memory_value = f"User: {message}\nResponse: {response}"
        self.store_memory("experiences", memory_value)
        
        return response
    
    def process_with_tools(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Process a message with the option to use tools and generate a response.
        
        Args:
            message: Message to process
            context: Optional context information
            
        Returns:
            The agent's response
        """
        if context is None:
            context = {}
        
        # Create a string describing available tools
        tools_description = ""
        for name, tool in self.tools.items():
            tools_description += f"- {name}: {tool['description']}\n"
        
        # Format the message with context and tools
        formatted_message = f"""
        Message: {message}
        
        Context: {json.dumps(context) if context else 'No additional context.'}
        
        Available tools:
        {tools_description}
        
        First, decide if you need to use any tools to respond to this message.
        If you need to use a tool, output your response in the following format:
        USE_TOOL: <tool_name>
        PARAMETERS: <parameters in JSON format>
        
        If you don't need to use a tool, simply provide your response directly.
        """
        
        # Generate a response using the LLM
        initial_response = self.llm.generate(formatted_message, system_prompt=self.system_prompt)
        
        # Check if the response indicates a tool should be used
        if initial_response.strip().startswith("USE_TOOL:"):
            try:
                # Parse the tool name and parameters
                lines = initial_response.strip().split('\n')
                tool_name = lines[0].replace("USE_TOOL:", "").strip()
                params_line = lines[1].replace("PARAMETERS:", "").strip()
                
                # Parse the JSON parameters
                parameters = json.loads(params_line)
                
                # Use the tool
                tool_result = self.use_tool(tool_name, **parameters)
                
                # Get a final response that incorporates the tool result
                final_prompt = f"""
                Message: {message}
                
                Context: {json.dumps(context) if context else 'No additional context.'}
                
                I used the tool "{tool_name}" with the following result:
                {tool_result}
                
                Please provide a helpful response that incorporates this information.
                """
                
                final_response = self.llm.generate(final_prompt, system_prompt=self.system_prompt)
                
                # Store the interaction in memory
                memory_value = f"User: {message}\nTool used: {tool_name}\nTool result: {tool_result}\nResponse: {final_response}"
                self.store_memory("experiences", memory_value)
                
                return final_response
                
            except Exception as e:
                # If there's an error parsing or using the tool, fall back to the initial response
                print(f"Error processing tool usage: {e}")
                return initial_response
        
        # If no tool is needed, return the initial response
        memory_value = f"User: {message}\nResponse: {initial_response}"
        self.store_memory("experiences", memory_value)
        
        return initial_response
    
    def __str__(self) -> str:
        """Return a string representation of the agent."""
        return f"{self.name} ({self.agent_id}) - {self.description}" 
