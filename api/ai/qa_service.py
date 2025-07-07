# api/ai/qa_service.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnablePassthrough

# Import the langchain_graph object you just created
from ..database import langchain_graph

# 1. Define the Language Model
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 2. Define the Cypher query for context retrieval
# This query finds skills that are similar to the user's question.
# For a more advanced implementation, you could use an LLM to extract keywords first.
retrieval_query = """
MATCH (s:Skill)
WHERE toLower(s.name) CONTAINS toLower($question)
OPTIONAL MATCH (s)-[:DEPENDS_ON]->(dependency)
RETURN s.name AS skill, dependency.name AS depends_on
LIMIT 5
"""

# 3. Create a prompt template
template = """
You are a helpful AI assistant for the SkillForge platform.
Answer the user's question based only on the following context retrieved from the knowledge graph:
---
Context:
{context}
---
Question: {question}
Answer:
"""
prompt = ChatPromptTemplate.from_template(template)

# 4. Build the RAG chain using LangChain Expression Language (LCEL)
rag_chain = (
    {
        "context": lambda x: langchain_graph.query(retrieval_query, {"question": x["question"]}),
        "question": lambda x: x["question"],
    }
    | prompt
    | llm
)