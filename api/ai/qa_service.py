# api/ai/qa_service.py
from fastapi.concurrency import run_in_threadpool
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
import re

from ..database import langchain_graph
import os  # For TESTING_MODE
from unittest.mock import MagicMock  # For mock llm

# --- LLM Initialization based on TESTING_MODE ---
if os.getenv("TESTING_MODE") == "True":
    llm = MagicMock()
    # If specific attributes or methods of llm are called directly during rag_chain construction
    # (outside of the part that gets mocked in tests), configure them here.
    # For example, if rag_chain construction did `llm.some_property`, then:
    # llm.some_property = MagicMock()
else:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    # _rag_chain_real was part of a previous incorrect approach. Removing it.

# Template and prompt are defined before rag_chain
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
        "skill",
        "name",
        "any",
        "some",
        "w/",
    }
    keywords = [
        word for word in re.findall(r"\b\w+\b", question) if word not in stop_words
    ]

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

    context = await run_in_threadpool(langchain_graph.query, retrieval_query, params)
    return context


# --- rag_chain definition is now conditional ---
if os.getenv("TESTING_MODE") == "True":
    rag_chain = MagicMock(name="mocked_rag_chain_in_service")
    # If rag_chain needs specific attributes for other parts of qa_service.py
    # during import (not typical for just being a chain definition), set them here.
else:
    rag_chain = (
        {
            "context": RunnableLambda(retrieve_context),
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm  # llm is the real ChatOpenAI or a MagicMock based on TESTING_MODE
    )
