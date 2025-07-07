# api/ai/qa_service.py
from fastapi.concurrency import run_in_threadpool
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
import re

# Import the langchain_graph object
from ..database import langchain_graph

# 1. Define the Language Model (no change)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 2. Define the Cypher query (no change)
retrieval_query = """
MATCH (s:Skill)
WHERE toLower(s.name) IN $keywords
OPTIONAL MATCH (s)-[:DEPENDS_ON*1..2]-(related:Skill)
RETURN s.name AS skill, s.description AS description, collect(DISTINCT related.name) AS related_skills
LIMIT 10
"""


# 3. Create the ASYNCHRONOUS context retrieval function using run_in_threadpool
# This is the key change to fix the deployment error.
async def retrieve_context(input_dict: dict) -> list:
    """
    Extracts keywords and queries Neo4j in a non-blocking way.
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

    # This runs the synchronous 'query' method in a separate thread,
    # preventing it from blocking the async event loop.
    context = await run_in_threadpool(
        langchain_graph.query, retrieval_query, {"keywords": keywords}
    )
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
        "context": RunnableLambda(retrieve_context),
        "question": RunnablePassthrough(),
    }
    | prompt
    | llm
)
