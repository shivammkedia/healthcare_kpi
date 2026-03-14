"""
Healthcare KPI Extraction using Multi-Agent AutoGen + MCP Filesystem

This project demonstrates a multi-agent agentic AI workflow where:
1. An Excel Reader Agent reads healthcare datasets using MCP Filesystem
2. A KPI Analysis Agent identifies and extracts key performance indicators
3. Agents collaborate asynchronously to derive business insights

Technologies: AutoGen, MCP (Model Context Protocol), OpenAI GPT-4o, Async
"""

import asyncio
import sys
import pandas as pd
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.base import TerminationCondition
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import StdioServerParams, McpWorkbench
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_agentchat.ui import Console
from autogen_core import FunctionCall
import json


# Define a custom tool function to read Excel files
async def read_excel_file(file_path: str) -> str:
    """
    Read Excel file and return column information.
    
    Args:
        file_path: Path to the Excel file
        
    Returns:
        String containing file schema and structure information
    """
    try:
        df = pd.read_excel(file_path)
        columns_info = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            non_null_count = df[col].notna().sum()
            columns_info.append(f"  - {col}: {dtype} (non-null: {non_null_count})")

        summary = f"Excel file '{file_path}' has {len(df)} rows and {len(df.columns)} columns:\n"
        summary += "\n".join(columns_info)
        return summary
    except Exception as e:
        return f"Error reading file: {str(e)}"


async def healthcare_app():
    """
    Main async function that orchestrates multi-agent workflow for healthcare KPI extraction.
    
    Workflow:
    1. Excel Reader Agent connects to filesystem via MCP
    2. Reads healthcare_dataset.xlsx
    3. Extracts schema and column information
    4. KPI Agent analyzes structure and identifies top KPIs
    5. Process terminates when KPI Agent says "Thank You"
    """
    
    # Initialize OpenAI model client for LLM-powered agents
    openai_model_client = OpenAIChatCompletionClient(
        model="gpt-4o-2024-08-06"
        # Note: API key loaded from OPENAI_API_KEY environment variable
    )

    # Configure MCP Filesystem Server Parameters
    file_system = StdioServerParams(
        command="npx",
        args=[
            "-y",
            "@modelcontextprotocol/server-filesystem",
            "E:/python_files"  # Update this to your data directory
        ],
        read_timeout_seconds=60
    )

    # Create MCP Workbench for filesystem operations
    fs_workbench = McpWorkbench(file_system)

    async with fs_workbench as fs_wb:
        # Agent 1: Excel Reader Agent
        # Responsible for reading and analyzing Excel file structure
        file_system_agent = AssistantAgent(
            name="excel_reader",
            model_client=openai_model_client,
            system_message="You are an Excel File Reader. Your task:\n"
                           "1. Read the healthcare_dataset.xlsx file from E:/python_files\n"
                           "2. Extract the column names and data types from the file\n"
                           "3. Provide a detailed summary of the schema to the KPI_agent\n"
                           "Use your tools to read and analyze the Excel file.",
            workbench=fs_wb
        )

        # Agent 2: KPI Analysis Agent
        # Analyzes the dataset structure and identifies key performance indicators
        agent2 = AssistantAgent(
            name="KPI_agent",
            model_client=openai_model_client,
            system_message="You are a KPI expert. Your task:\n"
                           "1. Receive the column information from excel_reader\n"
                           "2. Analyze the dataset structure\n"
                           "3. Identify and return the top 5 KPIs that can be extracted from the healthcare dataset\n"
                           "4. Provide brief explanations for each KPI\n"
                           "5. End your response with 'Thank You' to complete the task"
        )

        # Termination condition: stops when "Thank You" is mentioned
        terminate_ = TextMentionTermination("Thank You")
        
        # User proxy agent for human interaction
        user_agent = UserProxyAgent(name="User")

        # Create RoundRobin team with all participants
        team = RoundRobinGroupChat(
            participants=[file_system_agent, agent2, user_agent],
            termination_condition=terminate_
        )

        # Execute the team's streaming workflow
        await Console(team.run_stream(
            task="Read the healthcare_dataset.xlsx file from E:/python_files. Extract and analyze the column names and data types. Then identify the top 10 KPIs that can be derived from this dataset."))

    # Cleanup: Close the OpenAI client connection
    await openai_model_client.close()


if __name__ == "__main__":
    # Run the async healthcare app
    asyncio.run(healthcare_app())
