# api/ai/qa_service.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnablePassthrough
import re

# Import the langchain_graph object
from ..database import langchain_graph

# 1. Define the Language Model (no change)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 2. Define the CORRECTED Cypher query
# This version removes the non-existent "UNLOCKS" relationship.
retrieval_query = """
MATCH (s:Skill)
WHERE toLower(s.name) IN $keywords
// CORRECTED: Only use the :DEPENDS_ON relationship
OPTIONAL MATCH (s)-[:DEPENDS_ON*1..2]-(related:Skill)
RETURN s.name AS skill, s.description AS description, collect(DISTINCT related.name) AS related_skills
LIMIT 10
"""


# 3. Create the context retrieval function (no change)
def retrieve_context(input_dict: dict) -> list:
    """
    Extracts keywords from the user's question, queries the Neo4j graph,
    and formats the results for the LLM.
    """
    question = input_dict.get("question", "")

    stop_words = {
        "a",
        "an",
        "the",
        "is",
        "in",
        "what",
        "with",
        "have",
        "to",
        "do",
        "skills",
        "graph",
    }
    words = re.findall(r"\b\w+\b", question.lower())
    keywords = [word for word in words if word not in stop_words]

    if not keywords:
        return []

    context = langchain_graph.query(retrieval_query, {"keywords": keywords})
    return context


# 4. Create a prompt template (no change)
template = """
You are a helpful AI assistant for the SkillForge platform.
Answer the user's question based ONLY on the following context retrieved from the knowledge graph.
The context contains a list of skills, their descriptions, and other skills they are related to.
---
Context:
{context}
---
Question: {question}
Answer:
"""
prompt = ChatPromptTemplate.from_template(template)


# 5. Build the RAG chain (no change)
rag_chain = (
    {
        "context": retrieve_context,
        "question": RunnablePassthrough(),
    }
    | prompt
    | llm
)
