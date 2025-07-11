Project Context for SkillForge AI Development
1. Mission & Vision
Project Name: SkillForge

Vision: To create an AI-driven platform that builds a user's professional story through a graph of concrete, verifiable accomplishments. SkillForge maps goals to a personalized path of "quests," verifies completed work, and issues portable, cryptographic credentials for each accomplishment.

2. Core Architecture: The Accomplishment Graph
SkillForge's architecture is built on an evidence-based model centered on tangible work. The final, fully-connected graph structure is:

(u:User)-[:HAS_QUEST]->(q:Quest)
(a:Accomplishment)-[:FULFILLS]->(q:Quest)
(u:User)-[c:COMPLETED]->(a:Accomplishment)
(a:Accomplishment)-[:DEMONSTRATES]->(s:Skill)

Key Features:

Quest Assignment: The POST /goals/parse endpoint uses an LLM to break down a user's goal into :Quest nodes, which are immediately linked to the user via a [:HAS_QUEST] relationship.

Evidence-Based Accomplishments: Users submit work against a quest, creating an :Accomplishment node linked via [:FULFILLS]. User identity is handled exclusively by the auth token.

Verifiable Credential (VC) Issuance: The POST /accomplishments/{id}/issue-credential endpoint generates a signed JWT-based VC. A receipt (vc_id, vc_issuanceDate) is stored as properties on the [:COMPLETED] relationship, creating a complete, auditable trail from assignment to credential.

3. Technology Stack & Deployment
Backend: FastAPI (Python)

Databases: PostgreSQL (for user auth/data), Neo4j (for the knowledge graph)

AI/LLM: LangChain with gpt-4o-mini and other models.

Cryptography: jwcrypto for key management, python-jose for JWTs.

Containerization & Deployment: The full stack is containerized with Docker (docker-compose.yml) and deployed on Render.

4. CI/CD & Testing Environment
Platform: GitHub Actions (.github/workflows/ci.yml).

Services: The CI pipeline runs postgres and neo4j as service containers.

Environment Configuration: Test configuration (database URLs, credentials) is forcefully set within tests/conftest.py using pytest_configure to ensure absolute consistency and override any environment variables from the runner.

Service Lifecycle: The CI workflow includes a dedicated "Wait for services" step that uses nc (netcat) to probe the database ports, ensuring the tests only run after the services are fully accessible. This resolves all previous Connection refused race condition errors.

Test Suite: pytest is used for all tests. The suite includes unit, integration, and end-to-end tests that mock AI services and use dependency overrides (app.dependency_overrides) for testing protected endpoints.