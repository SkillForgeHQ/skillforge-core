from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from .schemas import SkillMatch
from typing import List

# 1. Set up a parser for our SkillMatch model
parser = PydanticOutputParser(pydantic_object=SkillMatch)

# 2. Create the Prompt Template
# This prompt is engineered to be very precise about the matching task.
prompt_template = """
You are an expert skills ontologist. Your task is to determine if a new "candidate skill" is a semantic duplicate or a direct subset of any skill from a list of "existing skills".

Your analysis must be strict. The candidate skill should only be considered a duplicate if it represents the same core competency as an existing skill.

Examples:
- "Docker Containerization" IS a duplicate of "Docker".
- "React State Management" IS a duplicate of "React.js".
- "Advanced Python" IS a duplicate of "Python".
- "Frontend Web Development" IS NOT a duplicate of "React.js", as it is a broader category.
- "SQL" IS NOT a duplicate of "PostgreSQL", as it is a broader category.

Return your analysis as a JSON object that strictly follows the provided schema. If no match is found, is_duplicate must be false and existing_skill_name must be null.

{format_instructions}

Candidate Skill:
{candidate_skill}

Existing Skills List:
{existing_skills}
"""

prompt = ChatPromptTemplate.from_template(
    template=prompt_template,
    partial_variables={"format_instructions": parser.get_format_instructions()},
)

# 3. Initialize the Language Model
model = ChatOpenAI(temperature=0, model="gpt-4o-mini")

# 4. Create the Chain
skill_matcher_chain = prompt | model | parser


# 5. Convenience function to invoke the chain
async def find_skill_match(
    candidate_skill: str, existing_skills: List[str]
) -> SkillMatch:
    """
    Invokes the skill matcher chain to find a semantic duplicate for the candidate skill.
    """
    return await skill_matcher_chain.ainvoke(
        {
            "candidate_skill": candidate_skill,
            "existing_skills": ", ".join(
                existing_skills
            ),  # Pass the list as a simple comma-separated string
        }
    )
