from langchain_openai import ChatOpenAI
try:
    from langchain.prompts import ChatPromptTemplate
except ImportError:  # pragma: no cover
    from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from .schemas import ExtractedSkills

# 1. Set up a parser for our ExtractedSkills model
parser = PydanticOutputParser(pydantic_object=ExtractedSkills)

# 2. Create the Prompt Template
# This prompt is engineered to make the LLM think like a talent manager
# and focus on extracting concrete, graph-ready skills.
prompt_template = """
You are an expert tech talent manager and skills analyst. A user will provide a description of an accomplishment. Your task is to analyze this accomplishment and extract a list of the underlying, specific, and granular technical skills required to achieve it.

For each skill, you must also assess the mastery level demonstrated by the accomplishment. Use one of the following mastery levels: Beginner, Intermediate, Advanced, Expert.

Return your analysis as a JSON object that strictly follows the provided schema.

{format_instructions}

Accomplishment Description:
{accomplishment}
"""

prompt = ChatPromptTemplate.from_template(
    template=prompt_template,
    partial_variables={"format_instructions": parser.get_format_instructions()},
)

# 3. Initialize the Language Model
model = ChatOpenAI(temperature=0, model="gpt-4o-mini")

# 4. Create the Chain
skill_extractor_chain = prompt | model | parser
