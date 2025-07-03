import os
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from .schemas import ParsedGoal

# 1. Set up a parser
parser = PydanticOutputParser(pydantic_object=ParsedGoal)

# 2. Create the Prompt Template
prompt_template = """
You are an expert project manager. A user will provide you with a high-level goal, and your task is to break it down into a series of smaller, actionable sub-tasks.

Return the goal and its sub-tasks formatted as a JSON object that strictly follows the provided schema.

{format_instructions}

User's Goal:
{goal}
"""

prompt = ChatPromptTemplate.from_template(
    template=prompt_template,
    partial_variables={"format_instructions": parser.get_format_instructions()},
)

# 3. Initialize the Language Model
# Ensure your OPENAI_API_KEY is set in your environment
model = ChatOpenAI(temperature=0, model="gpt-4.1-nano")

# 4. Create the Chain using LangChain Expression Language (LCEL)
goal_parser_chain = prompt | model | parser