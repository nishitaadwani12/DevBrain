"""Tool-calling agent over a workspace's documents (Gemini function calling).

The agent can search documents, list what's available, and explain a repo's
architecture. Tool *dispatch* is a pure function (unit-tested); the LLM loop is
a thin wrapper that is mocked in tests.
"""
from __future__ import annotations

import logging

from google.genai import types

from app.core.config import get_settings
from app.services import rag, vectorstore
from app.services.embeddings import _client

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 5

SYSTEM_INSTRUCTION = (
    "You are DevBrain's research agent. Use the provided tools to gather evidence "
    "from the user's documents before answering. Prefer search_documents to ground "
    "answers, and cite sources inline with [n] where n matches a search result index. "
    "Use explain_architecture for questions about how a codebase is structured. "
    "Be concise and only assert what the tools support."
)


def _tool_declarations() -> types.Tool:
    return types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="search_documents",
                description="Semantic search over the workspace's documents and code. "
                            "Returns ranked snippets with citation indices.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "query": types.Schema(type=types.Type.STRING),
                        "top_k": types.Schema(type=types.Type.INTEGER),
                    },
                    required=["query"],
                ),
            ),
            types.FunctionDeclaration(
                name="list_documents",
                description="List the documents and repos available in this workspace.",
                parameters=types.Schema(type=types.Type.OBJECT, properties={}),
            ),
            types.FunctionDeclaration(
                name="explain_architecture",
                description="Return the file dependency graph summary for an ingested repo, "
                            "given its document_id.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={"document_id": types.Schema(type=types.Type.STRING)},
                    required=["document_id"],
                ),
            ),
        ]
    )


def dispatch_tool(name: str, args: dict, workspace_id: str, user_id: str, citations: list[dict]) -> dict:
    """Execute a tool call. Appends any new citations to ``citations`` in place."""
    if name == "search_documents":
        hits = rag.retrieve(workspace_id, args["query"], top_k=int(args.get("top_k", 5)))
        results = []
        for h in hits:
            index = len(citations) + 1
            citation = {
                "index": index, "chunk_id": h["chunk_id"], "document_id": h["document_id"],
                "filename": h["filename"], "page": h.get("page"),
                "source_path": h.get("source_path"), "start_line": h.get("start_line"),
                "end_line": h.get("end_line"), "content": h["content"],
            }
            citations.append(citation)
            location = h.get("source_path") or h["filename"]
            results.append({"index": index, "location": location, "snippet": h["content"][:500]})
        return {"results": results}

    if name == "list_documents":
        docs = vectorstore.list_documents(workspace_id, user_id)
        return {"documents": [
            {"id": d["id"], "filename": d["filename"], "type": d["file_type"],
             "source": d["source_type"], "status": d["status"]}
            for d in docs
        ]}

    if name == "explain_architecture":
        graph = vectorstore.get_document_graph(args["document_id"], user_id)
        if not graph:
            return {"error": "No architecture graph for that document_id"}
        return {"stats": graph.get("stats", {}),
                "top_files": _top_connected_files(graph)}

    return {"error": f"Unknown tool: {name}"}


def _top_connected_files(graph: dict, n: int = 10) -> list[dict]:
    counts: dict[str, int] = {}
    for e in graph.get("edges", []):
        counts[e["target"]] = counts.get(e["target"], 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:n]
    return [{"file": f, "dependents": c} for f, c in ranked]


def run_agent(workspace_id: str, user_id: str, query: str, history: list[dict] | None = None) -> dict:
    """Run the tool-calling loop and return answer + accumulated citations."""
    settings = get_settings()
    tools = _tool_declarations()
    config = types.GenerateContentConfig(tools=[tools], system_instruction=SYSTEM_INSTRUCTION)

    contents: list[types.Content] = []
    for m in history or []:
        role = "model" if m["role"] == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part(text=query)]))

    citations: list[dict] = []
    tool_trace: list[str] = []

    for _ in range(MAX_TOOL_ITERATIONS):
        resp = _client().models.generate_content(
            model=settings.chat_model, contents=contents, config=config
        )
        candidate = resp.candidates[0]
        parts = candidate.content.parts or []
        function_calls = [p.function_call for p in parts if getattr(p, "function_call", None)]

        if not function_calls:
            return {"answer": resp.text or "", "citations": citations, "tool_trace": tool_trace}

        contents.append(candidate.content)
        for fc in function_calls:
            tool_trace.append(fc.name)
            result = dispatch_tool(fc.name, dict(fc.args or {}), workspace_id, user_id, citations)
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_function_response(name=fc.name, response=result)],
                )
            )

    # Ran out of iterations — ask for a final answer with what we have.
    resp = _client().models.generate_content(
        model=settings.chat_model, contents=contents, config=config
    )
    return {"answer": resp.text or "", "citations": citations, "tool_trace": tool_trace}
