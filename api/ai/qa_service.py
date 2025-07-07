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


# --- NEW: Updated retrieval logic ---
async def retrieve_context(input_dict: dict) -> list:
    """
    Extracts keywords and queries Neo4j. If no specific keywords are found,
    it fetches a few random skills as a fallback.
    """
    question = input_dict.get("question", "").lower()

    # Expanded stop words to better handle generic queries
    stop_words = {'a', 'an', 'the', 'is', 'in', 'what', 'with', 'have', 'to', 'do', 'skills', 'graph', 'skill', 'name', 'any', 'some'}
    keywords = [word for word in re.findall(r'\b\w+\b', question) if word not in stop_words]

    # If no useful keywords are left, use a fallback query
    if not keywords:
        retrieval_query = """
        MATCH (s:Skill)
        RETURN s.name AS skill, s.description AS description
        ORDER BY rand()
        LIMIT 3
        """
        params = {}
    else:
        # Otherwise, use the keyword-based query
        retrieval_query = """
        MATCH (s:Skill)
        WHERE toLower(s.name) IN $keywords
        OPTIONAL MATCH (s)-[:DEPENDS_ON*1..2]-(related:Skill)
        RETURN s.name AS skill, s.description AS description, collect(DISTINCT related.name) AS related_skills
        LIMIT 10
        """
        params = {"keywords": keywords}

    # Run the chosen query in a threadpool
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