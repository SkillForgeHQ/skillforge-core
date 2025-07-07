# api/ai/qa_service.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnablePassthrough
import re

# Import the langchain_graph object
from ..database import langchain_graph

# 1. Define the Language Model (no change)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 2. Define the NEW Cypher query
# This query now looks for skills where the name is IN a list of keywords.
retrieval_query = """
// Find skills matching any of the keywords
MATCH (s:Skill)
WHERE toLower(s.name) IN $keywords
// Find related skills (dependencies or unlocks) up to 2 hops away
OPTIONAL MATCH (s)-[:DEPENDS_ON|UNLOCKS*1..2]-(related)
RETURN s.name AS skill, s.description AS description, collect(DISTINCT related.name) AS related_skills
LIMIT 10
"""

# 3. Create the NEW context retrieval function
# This function will extract keywords before querying the graph
def retrieve_context(input_dict: dict) -> list:
    """
    Extracts keywords from the user's question, queries the Neo4j graph,
    and formats the results for the LLM.
    """
    question = input_dict.get("question", "")

    # A simple but effective keyword extractor:
    # removes common words and punctuation, keeps meaningful terms.
    stop_words = {'a', 'an', 'the', 'is', 'in', 'what', 'with', 'have', 'to', 'do', 'skills', 'graph'}
    # Use regex to find words, convert to lower case
    words = re.findall(r'\b\w+\b', question.lower())
    keywords = [word for word in words if word not in stop_words]

    if not keywords:
        return [] # Return empty if no keywords are found

    # Query the graph using the extracted keywords
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


# 5. Build the NEW RAG chain
# We replace the simple lambda with our new retrieve_context function
rag_chain = (
    {
        "context": retrieve_context,
        "question": RunnablePassthrough(),
    }
    | prompt
    | llm
)