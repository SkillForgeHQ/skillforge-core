# api/ai/qa_service.py
from fastapi.concurrency import run_in_threadpool
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
import re

from ..database import langchain_graph

# --- (No changes to LLM or prompt template) ---
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
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

# --- UPDATED retrieval logic ---
async def retrieve_context(input_dict: dict) -> list:
    """
    Extracts keywords and queries Neo4j using a flexible 'CONTAINS' search.
    Falls back to random skills if no specific keywords are found.
    """
    question = input_dict.get("question", "").lower()

    stop_words = {'a', 'an', 'the', 'is', 'in', 'what', 'with', 'have', 'to', 'do', 'skills', 'graph', 'skill', 'name', 'any', 'some', 'w/'}
    keywords = [word for word in re.findall(r'\b\w+\b', question) if word not in stop_words]

    if not keywords:
        retrieval_query = """
        MATCH (s:Skill)
        RETURN s.name AS skill, s.description AS description
        ORDER BY rand()
        LIMIT 3
        """
        params = {}
    else:
        # This query now uses CONTAINS for a more flexible search
        retrieval_query = """
        UNWIND $keywords AS keyword
        MATCH (s:Skill)
        WHERE toLower(s.name) CONTAINS keyword
        OPTIONAL MATCH (s)-[:DEPENDS_ON*1..2]-(related:Skill)
        RETURN s.name AS skill, s.description AS description, collect(DISTINCT related.name) AS related_skills
        LIMIT 10
        """
        params = {"keywords": keywords}

    context = await run_in_threadpool(
        langchain_graph.query, retrieval_query, params
    )
    return context


# --- (No change to the final RAG chain) ---
rag_chain = (
    {
        "context": RunnableLambda(retrieve_context),
        "question": RunnablePassthrough(),
    }
    | prompt
    | llm
)