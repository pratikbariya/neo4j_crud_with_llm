from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from neo4j import GraphDatabase
import json
import os
from openai import OpenAI


USE_LLM = True


class Neo4jService:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "password")
        )

    def run_query(self, query, params=None):
        with self.driver.session() as session:
            result = session.run(query, params or {})
            return [record.data() for record in result]


db = Neo4jService()


class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    message: str


class RequirementUpdate(BaseModel):
    session_id: str
    subgoals: Optional[List[str]] = []
    constraints: Optional[List[str]] = []
    preferences: Optional[List[str]] = []



client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_requirement(text: str):
    if not USE_LLM:
        return {
            "goal": text,
            "subgoals": ["analyze", "compute"],
            "constraints": ["fast"],
            "preferences": ["step_by_step"]
        }

    system_prompt = """
    Extract structured requirement:
    goal, subgoals, constraints, preferences

    Return ONLY valid JSON.
    """

    user_prompt = f"""
    Input: "{text}"

    Output:
    {{
        "goal": "...",
        "subgoals": [],
        "constraints": [],
        "preferences": []
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        return {
            "goal": data.get("goal", ""),
            "subgoals": data.get("subgoals", []),
            "constraints": data.get("constraints", []),
            "preferences": data.get("preferences", [])
        }

    except Exception as e:
        print("LLM ERROR:", e)

        return {
            "goal": text,
            "subgoals": [],
            "constraints": [],
            "preferences": []
        }


def validate(data):
    return {
        "goal": data.get("goal", ""),
        "subgoals": data.get("subgoals", []),
        "constraints": data.get("constraints", []),
        "preferences": data.get("preferences", [])
    }


# ==============================
# 🔹 GRAPH REPOSITORY
# ==============================
def create_requirement(user_id, session_id, data):
    query = """
    MERGE (u:User {id: $user_id})
    MERGE (s:Session {id: $session_id})

    MERGE (g:Goal {name: $goal, session_id: $session_id})

    MERGE (u)-[:HAS_GOAL]->(g)
    MERGE (s)-[:HAS_CONTEXT]->(g)

    WITH g, $subgoals AS subgoals
    UNWIND subgoals AS sg
        MERGE (sub:SubGoal {name: sg, session_id: $session_id})
        MERGE (g)-[:HAS_SUBGOAL]->(sub)

    WITH g, $constraints AS constraints
    UNWIND constraints AS c
        MERGE (con:Constraint {name: c, session_id: $session_id})
        MERGE (g)-[:HAS_CONSTRAINT]->(con)

    WITH g, $preferences AS preferences
    UNWIND preferences AS p
        MERGE (pref:Preference {name: p, session_id: $session_id})
        MERGE (g)-[:HAS_PREFERENCE]->(pref)
    """

    db.run_query(query, {
        "user_id": user_id,
        "session_id": session_id,
        "goal": data["goal"],
        "subgoals": data["subgoals"],
        "constraints": data["constraints"],
        "preferences": data["preferences"]
    })


# ✅ FIXED: Graph-friendly query
def get_requirement_graph(session_id):
    query = """
    MATCH (s:Session {id: $session_id})-[:HAS_CONTEXT]->(g:Goal)

    OPTIONAL MATCH (g)-[r1:HAS_SUBGOAL]->(sg:SubGoal)
    OPTIONAL MATCH (g)-[r2:HAS_CONSTRAINT]->(c:Constraint)
    OPTIONAL MATCH (g)-[r3:HAS_PREFERENCE]->(p:Preference)

    RETURN s, g, sg, c, p, r1, r2, r3
    """

    return db.run_query(query, {"session_id": session_id})


# ✅ Structured JSON (for API)
def get_requirement_json(session_id):
    query = """
    MATCH (s:Session {id: $session_id})-[:HAS_CONTEXT]->(g:Goal)
    OPTIONAL MATCH (g)-[:HAS_SUBGOAL]->(sg:SubGoal)
    OPTIONAL MATCH (g)-[:HAS_CONSTRAINT]->(c:Constraint)
    OPTIONAL MATCH (g)-[:HAS_PREFERENCE]->(p:Preference)

    RETURN g.name AS goal,
           collect(DISTINCT sg.name) AS subgoals,
           collect(DISTINCT c.name) AS constraints,
           collect(DISTINCT p.name) AS preferences
    """

    return db.run_query(query, {"session_id": session_id})


def update_requirement(session_id, subgoals, constraints, preferences):
    query = """
    MATCH (g:Goal {session_id: $session_id})

    OPTIONAL MATCH (g)-[r1:HAS_SUBGOAL]->(:SubGoal {session_id: $session_id})
    DELETE r1

    OPTIONAL MATCH (g)-[r2:HAS_CONSTRAINT]->(:Constraint {session_id: $session_id})
    DELETE r2

    OPTIONAL MATCH (g)-[r3:HAS_PREFERENCE]->(:Preference {session_id: $session_id})
    DELETE r3

    WITH g, $subgoals AS subgoals
    UNWIND subgoals AS sg
        MERGE (s:SubGoal {name: sg, session_id: $session_id})
        MERGE (g)-[:HAS_SUBGOAL]->(s)

    WITH g, $constraints AS constraints
    UNWIND constraints AS c
        MERGE (con:Constraint {name: c, session_id: $session_id})
        MERGE (g)-[:HAS_CONSTRAINT]->(con)

    WITH g, $preferences AS preferences
    UNWIND preferences AS p
        MERGE (pref:Preference {name: p, session_id: $session_id})
        MERGE (g)-[:HAS_PREFERENCE]->(pref)
    """

    db.run_query(query, {
        "session_id": session_id,
        "subgoals": subgoals or [],
        "constraints": constraints or [],
        "preferences": preferences or []
    })


def delete_requirement(session_id):
    query = """
    MATCH (g:Goal {session_id: $session_id})
    DETACH DELETE g
    """

    db.run_query(query, {"session_id": session_id})



app = FastAPI()


@app.post("/chat")
def create(req: ChatRequest):
    data = validate(extract_requirement(req.message))
    create_requirement(req.user_id, req.session_id, data)

    return {
        "status": "stored",
        "data": data
    }


# GRAPH VIEW (for Neo4j visualization)
@app.get("/requirement/graph/{session_id}")
def read_graph(session_id: str):
    return get_requirement_graph(session_id)


# JSON VIEW (for frontend/API)
@app.get("/requirement/{session_id}")
def read_json(session_id: str):
    return get_requirement_json(session_id)


@app.put("/requirement")
def update(req: RequirementUpdate):
    update_requirement(
        req.session_id,
        req.subgoals,
        req.constraints,
        req.preferences
    )
    return {"status": "updated"}


@app.delete("/requirement/{session_id}")
def delete(session_id: str):
    delete_requirement(session_id)
    return {"status": "deleted"}