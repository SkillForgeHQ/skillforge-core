Project Context for SkillForge AI Development
1. Mission & Vision
Project Name: SkillForge

Vision: To create an AI-driven platform that moves beyond abstract skill labels and builds a user's professional story through a graph of concrete, verifiable accomplishments. SkillForge maps a user's goals to a personalized learning path of "quests," verifies the work they've done, and issues portable, cryptographic credentials for their accomplishments.

2. Core Architecture: The Accomplishment Graph
SkillForge's architecture is built on an evidence-based model centered on tangible work. A user's proficiency is demonstrated by the work they've verifiably completed.

The core graph structure is:
(User)-[:HAS_QUEST]->(Quest)<-[:FULFILLS]-(Accomplishment)<-[:COMPLETED {vc_id, vc_issuanceDate}]-(User)

How it works:

A user's high-level goal is parsed into a series of concrete Quest nodes, which are assigned to the user via a [:HAS_QUEST] relationship.

The user submits proof of work as an Accomplishment, which is linked to the [:Quest] it fulfills.

Upon issuing a Verifiable Credential (VC), a receipt is stored as properties on the [:COMPLETED] relationship, creating a full, auditable trail.

3. Core Feature: Verifiable Credential (VC) Issuance
The primary product loop culminates in the issuance of a Verifiable Credential. This provides our users with portable, tamper-proof, cryptographic proof of their work.

Technical Implementation:

Standard: W3C Verifiable Credentials Data Model.

Format: VCs are issued as JSON Web Tokens (JWTs).

Cryptography: Credentials are signed using the ES256 algorithm.

4. Current Tech Stack & Deployment
Backend Framework: FastAPI (Python)

Databases:

Application Data: PostgreSQL

Knowledge Graph: Neo4j

AI/LLM: LangChain with gpt-4o-mini.

Cryptography: jwcrypto for key management, python-jose for JWT operations.

Deployment: The full stack is containerized with Docker and deployed on Render.

5. Key Code Files & Directories
api/main.py: The entry point for the FastAPI application.

api/schemas.py: All Pydantic schemas.

api/graph_crud.py: All functions that execute Cypher queries against Neo4j.

api/routers/: Directory containing API endpoint definitions.

goals.py: Contains the POST /goals/parse endpoint which now creates and assigns :Quest nodes.

accomplishments.py: Contains endpoints for submitting accomplishments and issuing VCs.