"""
MySQL Query Agent using AutoGen + MCP MySQL Server

This project demonstrates an intelligent SQL agent that:
1. Connects to MySQL database via MCP (Model Context Protocol)
2. Automatically explores database schema (tables, columns)
3. Generates and executes SQL queries based on natural language requests
4. Returns results in formatted tables
5. Supports iterative questioning with continuous conversation

Technologies: AutoGen, MCP MySQL Server, OpenAI GPT-4o, Async
"""

import asyncio
import os
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import StdioServerParams, McpWorkbench


async def main():
    """
    Main async function that initializes and runs the MySQL Query Agent.
    
    Features:
    - Automatic schema exploration (SHOW TABLES, DESCRIBE)
    - SQL query generation from natural language
    - Direct database access via MCP MySQL server
    - Interactive loop for multiple queries
    - Formatted result output
    """
    
    # Configure MCP MySQL Server Parameters
    # This connects the agent to a MySQL database instance
    mysql_parameter = StdioServerParams(
        command="/Users/shivamkedia/.local/bin/uv",  # Update to your uv path
        args=[
            "--directory",
            "/Users/shivamkedia/PycharmProjects/RealTimeProjects/.venv/lib/python3.13/site-packages",
            "run",
            "mysql_mcp_server"
        ],
        env={
            "MYSQL_HOST": "localhost",          # Update with your MySQL host
            "MYSQL_PORT": "3306",               # Update with your MySQL port
            "MYSQL_USER": "root",               # Update with your MySQL user
            "MYSQL_PASSWORD": "chocopie",       # Update with your MySQL password (use env vars in production!)
            "MYSQL_DATABASE": "maven_advanced_sql"  # Update with your database name
        }
    )
    
    # Create MCP Workbench for database operations
    async with McpWorkbench(mysql_parameter) as msql:
        # Initialize OpenAI GPT-4o model client for intelligent SQL generation
        openai_model_client = OpenAIChatCompletionClient(
            model="gpt-4o-2024-08-06",
            # Note: API key loaded from OPENAI_API_KEY environment variable
        )
        
        # User Agent: Represents the human user
        user_agent = UserProxyAgent(
            name="Shivam"
        )
        
        # SQL Agent: Expert MySQL analyst with database access
        # This agent has direct access to the database via MCP
        sql_agent = AssistantAgent(
            name="sql_agent",
            model_client=openai_model_client,
            workbench=msql,
            reflect_on_tool_use=True,  # Agent reflects on tool outputs for better decisions
            system_message="""You are an expert MySQL analyst with direct access to a MySQL database.
You MUST complete ALL steps below automatically without stopping or asking for input:

STEP 1: Call execute_sql with "SHOW TABLES" to list all tables.
STEP 2: Call execute_sql with "DESCRIBE <table>" for all tables to understand schema.
STEP 3: Write a SQL query using the REAL column names you just read.
STEP 4: Call execute_sql to run the query.
STEP 5: Display results in a clean formatted table.
STEP 6: End your response with "END NOW" to signal completion.

Important:
- Never stop between steps
- Never ask for confirmation
- Run all steps in one continuous execution
- Use actual column names discovered in DESCRIBE output
- Format results clearly for easy interpretation
"""
        )
        
        # Termination condition: Agent stops when it outputs "END NOW"
        termination = TextMentionTermination("END NOW")
        
        # Create team with single SQL agent (no user interaction during agent run)
        team = RoundRobinGroupChat(
            participants=[sql_agent],   # Only SQL agent executes
            termination_condition=termination
        )
        
        # Initial task
        task = "Find the most selling products from the database."
        
        # Interactive loop: User can ask multiple questions
        while True:
            # Execute agent workflow in streaming mode
            await Console(team.run_stream(task=task))
            
            # Prompt user for next question
            print("\n--- Ask another question or type 'exit' to quit ---")
            task = input("Your question: ").strip()
            
            # Exit condition
            if task.lower() == "exit":
                print("Thank you for using the MySQL Query Agent. Goodbye!")
                break
        
        # Cleanup: Close the OpenAI client connection
        await openai_model_client.close()


# Entry point
if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
