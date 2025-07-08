Project Context for SkillForge AI Development
1. Mission & Vision
Project Name: SkillForge

Vision: To create an AI-driven platform that moves beyond abstract skill labels and builds a user's professional story through a graph of concrete, verifiable accomplishments. SkillForge maps a user's goals to a personalized learning path of "quests," verifies the work they've done, and issues portable, cryptographic credentials for their accomplishments.

2. Core Architecture: The Accomplishment Graph
SkillForge's architecture is built on an evidence-based model centered on tangible work. We do not use abstract or arbitrary levels for skills. Instead, a user's proficiency is demonstrated by the work they've verifiably completed.

The core graph structure is:

(User) -[:COMPLETED]-> (Accomplishment) -[:DEMONSTRATES]-> (Skill)

How it works:

A user submits proof of work (code, documents, etc.) for an Accomplishment.

Our AI backend analyzes this proof to (1) verify the task was completed and (2) extract the Skills demonstrated by the work.

This creates a rich, factual, and defensible graph of a user's real-world abilities, which powers our recommendation engine for suggesting new "quests."

3. Core Feature: Verifiable Credential (VC) Issuance
The primary product loop of SkillForge culminates in the issuance of a Verifiable Credential. This provides our users with portable, tamper-proof, cryptographic proof of their work.

Technical Implementation:

Standard: We adhere to the W3C Verifiable Credentials Data Model.

Format: VCs are issued as JSON Web Tokens (JWTs), a compact and web-safe standard. The full VC data structure is contained within the vc claim of the JWT.

Cryptography: Credentials are signed using the ES256 algorithm with a JSON Web Key (JWK) belonging to SkillForge (the "Issuer"). This ensures the credential cannot be forged or altered.

Endpoint: The POST /accomplishments/{accomplishment_id}/issue-credential endpoint is used to generate and sign a VC for a specific, verified accomplishment.

4. Current Tech Stack & Deployment
Backend Framework: FastAPI (Python)

Databases:

Application Data: PostgreSQL

Knowledge Graph: Neo4j

AI/LLM: LangChain with gpt-4o-mini and other models.

Cryptography: jwcrypto for key management, python-jose for JWT operations.

Containerization: The entire stack is containerized with Docker and orchestrated with docker-compose.yml.

Deployment: Deployed on Render.

CI/CD: Continuous Integration is handled by GitHub Actions (.github/workflows/ci.yml), which runs pytest on every push to main.

5. Key Code Files & Directories
When given prompts, you will primarily be interacting with the following parts of the codebase located in the api/ directory:

api/main.py: The entry point for the FastAPI application.

api/database.py: Database session and connection logic.

api/schemas.py: All Pydantic schemas.

api/graph_crud.py: All functions that execute Cypher queries against Neo4j.

api/routers/: Directory containing API endpoint definitions.

accomplishments.py: Contains the critical endpoints for submitting accomplishments and issuing Verifiable Credentials.

users.py, skills.py, goals.py: Other related routers.

api/utils/crypto.py: Utility scripts for generating and managing cryptographic keys.