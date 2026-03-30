# 🧠 Requirement Knowledge Graph API

A FastAPI-based backend system that converts natural language user input into a structured **knowledge graph** using LLMs and stores it in **Neo4j**.

This system extracts:

* 🎯 Goal
* 🧩 Subgoals
* ⚙️ Constraints
* 🎨 Preferences

…and represents them as a connected graph for downstream use cases like **AI planning, agent orchestration, and decision systems**.

---

## 🚀 Features

* ✅ Natural Language → Structured Data (via LLM)
* ✅ Graph-based storage using Neo4j
* ✅ Session-based context management
* ✅ Graph visualization support
* ✅ CRUD operations for requirements
* ✅ Clean separation: Graph View vs JSON View

---

## 🏗️ Architecture Overview

```
User Input → LLM Extraction → Structured JSON → Neo4j Graph Storage
                                         ↓
                              API (FastAPI Endpoints)
                                         ↓
                      Graph View / JSON View / Updates
```

---

## 🧩 Graph Schema

```
(User)-[:HAS_GOAL]->(Goal)<-[:HAS_CONTEXT]-(Session)

(Goal)-[:HAS_SUBGOAL]->(SubGoal)
(Goal)-[:HAS_CONSTRAINT]->(Constraint)
(Goal)-[:HAS_PREFERENCE]->(Preference)
```

> All nodes are scoped using `session_id` to avoid cross-session conflicts.

---

## ⚙️ Tech Stack

* **FastAPI** – Backend framework
* **Neo4j** – Graph database
* **OpenAI API** – Requirement extraction (LLM)
* **Pydantic** – Data validation

---

## 📦 Installation

### 1. Clone Repo

```bash
git clone https://github.com/pratikbariya/neo4j_crud_with_llm.git
cd neo4j_crud_with_llm
```

### 2. Install Dependencies

```bash
pip install fastapi uvicorn neo4j openai
```

### 3. Setup Environment Variables

```bash
export OPENAI_API_KEY=your_api_key
```

### 4. Start Neo4j

Make sure Neo4j docker is running on:

```
docker run -d --name <db-name:neo4j-poc>
-p 7474:7474 -p 7687:7687 
-e NEO4J_AUTH=<neo4j>/<password> 
neo4j:latest
```

---

## ▶️ Run Application

```bash
python -m uvicorn knowledge_graph:app --reload
```

App runs at:

```
http://127.0.0.1:8000
```

---

## 📡 API Endpoints

### 🔹 1. Create Requirement (Chat)

```http
POST /chat
```

#### Request:

```json
{
  "user_id": "u1",
  "session_id": "s1",
  "message": "Build a fast API for image processing with UI support"
}
```

#### Response:

```json
{
  "status": "stored",
  "data": {
    "goal": "...",
    "subgoals": [],
    "constraints": [],
    "preferences": []
  }
}
```

---

### 🔹 2. Get Requirement (JSON)

```http
GET /requirement/{session_id}
```

👉 Returns structured data (for frontend use)

---

### 🔹 3. Get Requirement (Graph View)

```http
GET /requirement/graph/{session_id}
```

👉 Returns nodes + relationships (for Neo4j visualization)

---

### 🔹 4. Update Requirement (Replace Mode)

```http
PUT /requirement
```

#### Request:

```json
{
  "session_id": "s1",
  "subgoals": ["design", "implement"],
  "constraints": ["fast"],
  "preferences": ["ui"]
}
```

👉 Replaces existing relationships with new ones

---

### 🔹 5. Delete Requirement

```http
DELETE /requirement/{session_id}
```

👉 Deletes the goal node and all connected relationships

---

## 🧠 LLM Behavior

The system uses OpenAI (`gpt-5-mini`) to extract structured data:

```json
{
  "goal": "...",
  "subgoals": [],
  "constraints": [],
  "preferences": []
}
```

Fallback is used if LLM fails.

---

## 🔍 Neo4j Visualization Tips

To visualize graph in Neo4j Browser:

```cypher
MATCH (s:Session {id: "s1"})-[:HAS_CONTEXT]->(g:Goal)
OPTIONAL MATCH (g)-[r]->(n)
RETURN s, g, r, n
```

---

## ⚠️ Important Notes

* Ensure lists (subgoals, constraints, preferences) are not empty for richer graphs
* Nodes are session-scoped using `session_id`
* Update API replaces relationships (not incremental)

---


