# LangGraph Concepts in the Bluesky Feed Agent

This document explains every LangGraph concept used in this repository in detail, with references to the relevant source files.

---

## Table of Contents

1. [What is LangGraph?](#1-what-is-langgraph)
2. [StateGraph](#2-stategraph)
3. [State Schema (BlueskyFeedState)](#3-state-schema-blueskyfeedstate)
4. [Nodes](#4-nodes)
5. [Edges](#5-edges)
6. [Conditional Edges & Routing](#6-conditional-edges--routing)
7. [Entry Point](#7-entry-point)
8. [END – Terminal Node](#8-end--terminal-node)
9. [Graph Compilation](#9-graph-compilation)
10. [Graph Invocation](#10-graph-invocation)
11. [State Pruning Pattern](#11-state-pruning-pattern)
12. [Chunking / Map-Reduce Pattern](#12-chunking--map-reduce-pattern)
13. [LangChain Integration](#13-langchain-integration)
14. [Deployment Configuration (langgraph.json)](#14-deployment-configuration-langgraphjson)
15. [Full Data-Flow Diagram](#15-full-data-flow-diagram)

---

## 1. What is LangGraph?

[LangGraph](https://github.com/langchain-ai/langgraph) is a library for building stateful, multi-step applications with LLMs. It models an application as a **directed graph** where:

- Each **node** is a Python function that reads and writes a shared state object.
- Each **edge** defines the order in which nodes execute.
- A **conditional edge** inspects the current state and routes execution to one of several downstream nodes.

This agent uses LangGraph to build a reliable, linear pipeline that fetches posts from Bluesky, formats them, and generates an AI-powered summary—with clean error handling at each step.

**Relevant files**:
- `src/bluesky_feed_agent/agent/graph.py` – graph construction and node implementations
- `src/bluesky_feed_agent/states/state.py` – state schema

---

## 2. StateGraph

**Source**: `src/bluesky_feed_agent/agent/graph.py`, lines 181–196

```python
from langgraph.graph import END, StateGraph
from src.bluesky_feed_agent.states import BlueskyFeedState

def create_agent_graph() -> StateGraph:
    graph = StateGraph(BlueskyFeedState)   # ← StateGraph takes the state schema
    ...
    return graph.compile()
```

`StateGraph` is the core LangGraph class. It accepts a **state schema** (a Python class) as its only argument and keeps a single instance of that schema as execution flows through the graph.

Key responsibilities of `StateGraph`:
- Stores the registered nodes and their connections.
- Validates that each node function accepts and returns the declared state type.
- Produces a compiled, executable graph via `.compile()`.

---

## 3. State Schema (BlueskyFeedState)


**Source**: `src/bluesky_feed_agent/states/state.py`

```python
from typing import Optional
from pydantic import BaseModel

class BlueskyFeedState(BaseModel):
    posts: list[dict] = []          # Raw posts fetched from Bluesky
    raw_feed_text: Optional[str] = None  # Formatted text for the LLM
    summary: Optional[str] = None   # Final AI-generated summary
    error: Optional[str] = None     # Error message from any failed step
    user_handle: str = ""           # Target handle ("" = home feed)
```

The state schema is a [Pydantic](https://docs.pydantic.dev/) `BaseModel`. LangGraph passes a **single instance** of this class through every node. Key design choices:

| Field | Set By | Cleared By | Purpose |
|-------|--------|------------|---------|
| `posts` | `fetch_feed_node` | `format_feed_node` | Holds raw API response dicts |
| `raw_feed_text` | `format_feed_node` | `summarize_feed_node` | Holds formatted LLM-ready text |
| `summary` | `summarize_feed_node` | — | Final output |
| `error` | Any node | — | Signals failure to downstream routing |
| `user_handle` | Caller (initial state) | — | Controls home vs. user feed |

Using Pydantic provides:
- **Automatic validation** of field types on assignment.
- **Default values** so callers only need to supply non-default fields.
- **Serialization** support required for LangGraph's internal checkpointing.

The file also defines `AgentState`, a higher-level schema that wraps `BlueskyFeedState` alongside a `messages` list for chat history. This illustrates how LangGraph state schemas can be composed.

---

## 4. Nodes

**Source**: `src/bluesky_feed_agent/agent/graph.py`, lines 55–196

A **node** is any Python function with the signature:

```python
def node_name(state: StateSchema) -> StateSchema:
    ...
    return state
```

Nodes are registered on the graph with `graph.add_node(name, function)`. This agent defines **four nodes**:

### 4.1 `fetch_feed_node`

```python
graph.add_node("fetch_feed", fetch_feed_node)
```

- **Purpose**: Authenticate with Bluesky via ATProto and retrieve posts.
- **Reads**: `state.user_handle`
- **Writes**: `state.posts` (list of dicts), or `state.error` on failure
- **Logic**:
  - If `user_handle` is set → calls `client.get_user_feed()`.
  - Otherwise → calls `client.get_home_feed()` (filters replies, enforces `min_likes=50`).
  - `POST_LIMIT` env var overrides the default of 20 posts.
  - Any exception is caught and written to `state.error` so the graph can route gracefully.

### 4.2 `format_feed_node`

```python
graph.add_node("format_feed", format_feed_node)
```

- **Purpose**: Clean, deduplicate, and serialise raw post dicts into a plain-text string for the LLM.
- **Reads**: `state.posts`
- **Writes**: `state.raw_feed_text`, then **clears** `state.posts = []`
- **Logic**: Delegates to `format_posts_for_llm()` which:
  - Removes posts shorter than `MIN_POST_LENGTH` (15 chars).
  - Removes URL-only / spam posts.
  - Deduplicates using Jaccard word-set similarity (threshold 0.85).
  - Formats each post with author, timestamp, like count, and separator lines.

### 4.3 `summarize_feed_node`

```python
graph.add_node("summarize", summarize_feed_node)
```

- **Purpose**: Call the LLM (Gemini 2.5 Flash) to produce the final summary.
- **Reads**: `state.raw_feed_text`
- **Writes**: `state.summary`, then **clears** `state.raw_feed_text = None`
- **Logic**: Implements a map-reduce chunking strategy for large feeds (see [Section 12](#12-chunking--map-reduce-pattern)).

### 4.4 `error_handler_node`

```python
graph.add_node("error_handler", error_handler_node)
```

- **Purpose**: Log the error and allow the graph to finish cleanly.
- **Reads**: `state.error`
- **Writes**: Nothing (state is returned unchanged)
- **Logic**: Simply emits a structured `logger.error(...)` line; downstream callers inspect `response["error"]` to decide what to display.

---

## 5. Edges

**Source**: `src/bluesky_feed_agent/agent/graph.py`, lines 192–194

A **direct edge** unconditionally connects two nodes:

```python
graph.add_edge("format_feed", "summarize")
graph.add_edge("summarize", END)
graph.add_edge("error_handler", END)
```

Once `format_feed_node` finishes, LangGraph always calls `summarize_feed_node` next. There is no branching on a direct edge. Similarly, both `summarize` and `error_handler` always terminate the graph by routing to the special `END` sentinel.

---

## 6. Conditional Edges & Routing

**Source**: `src/bluesky_feed_agent/agent/graph.py`, lines 172–176 and 191

A **conditional edge** evaluates a router function at runtime and branches to one of several possible next nodes:

```python
graph.add_conditional_edges("fetch_feed", should_summarize)
```

The router function:

```python
def should_summarize(state: BlueskyFeedState) -> str:
    if state.error or not state.posts:
        return "error_handler"   # ← name of the target node
    return "format_feed"
```

LangGraph calls `should_summarize(state)` immediately after `fetch_feed_node` completes. The returned string is matched against registered node names:

| Condition | Returned value | Next node |
|-----------|---------------|-----------|
| `state.error` is set OR `state.posts` is empty | `"error_handler"` | `error_handler_node` |
| Posts were fetched successfully | `"format_feed"` | `format_feed_node` |

This keeps error handling **inside the graph** rather than in the caller, making the workflow self-contained and testable.

---

## 7. Entry Point

**Source**: `src/bluesky_feed_agent/agent/graph.py`, line 190

```python
graph.set_entry_point("fetch_feed")
```

`set_entry_point` designates which node receives the initial state when the graph is invoked. In this pipeline there is only one entry point (`fetch_feed`), but LangGraph also supports multiple entry points for more complex workflows.

---

## 8. END – Terminal Node

**Source**: `src/bluesky_feed_agent/agent/graph.py`, line 9 (import) and lines 193–194

```python
from langgraph.graph import END, StateGraph

graph.add_edge("summarize", END)
graph.add_edge("error_handler", END)
```

`END` is a LangGraph built-in constant that acts as a virtual terminal node. Any edge that targets `END` signals that execution should stop and the final state should be returned to the caller. It is not a real node—it is a routing sentinel that the compiled graph uses to detect graph completion.

---

## 9. Graph Compilation

**Source**: `src/bluesky_feed_agent/agent/graph.py`, line 196

```python
return graph.compile()
```

`.compile()` converts the `StateGraph` definition into an executable `CompiledStateGraph`. During compilation LangGraph:

1. **Validates** that all referenced node names exist.
2. **Validates** that every node is reachable from the entry point.
3. **Resolves** the routing map for conditional edges.
4. **Returns** a compiled object whose `.invoke()` and `.stream()` methods can run the graph.

The compiled graph is what callers use—never the raw `StateGraph` builder.

---

## 10. Graph Invocation

**Source**: `src/bluesky_feed_agent/agent/graph.py`, lines 212–216

```python
agent = create_agent_graph()                         # compiled graph
initial_state = BlueskyFeedState(user_handle=user_handle or "")
result = agent.invoke(initial_state)                 # synchronous execution
```

`agent.invoke(initial_state)` runs every node sequentially according to the graph's edges and returns the **final state** after the graph reaches `END`.

The return value (`result`) can be either:
- A **`BlueskyFeedState` object** – returned as-is when no checkpointer is configured.
- A **`dict`** – returned by some LangGraph configurations.

The helper `_build_response(result)` in `graph.py` (lines 310–335) normalises both cases into a consistent response dictionary:

```python
response = {
    "posts":        result.posts or result.get("posts"),
    "raw_feed":     result.raw_feed_text or result.get("raw_feed_text"),
    "summary":      result.summary or result.get("summary"),
    "error":        result.error or result.get("error"),
}
```

---

## 11. State Pruning Pattern

**Source**: `src/bluesky_feed_agent/agent/graph.py`, lines 94 and 156

LangGraph passes the **same mutable state object** through every node. As each stage completes its work, the node deliberately clears the field it consumed:

```python
# format_feed_node – after building raw_feed_text, drop the raw post dicts
state.posts = []

# summarize_feed_node – after building summary, drop the formatted text
state.raw_feed_text = None
```

**Why this matters**:
- Prevents large intermediate objects (raw post dicts, multi-kilobyte formatted text) from being serialized alongside the final state.
- Reduces memory usage when multiple graph invocations run concurrently.
- Keeps the LLM context clean—nodes never accidentally forward stale data to downstream steps.

This is a recommended LangGraph pattern: each node owns its output field and clears its input field.

---

## 12. Chunking / Map-Reduce Pattern

**Source**: `src/bluesky_feed_agent/agent/graph.py`, lines 115–153

Large feeds (more than `CHUNK_SIZE = 30` post blocks) would exceed the LLM's practical context window. `summarize_feed_node` implements a **map-reduce** strategy entirely within a single node:

```python
if len(post_blocks) <= CHUNK_SIZE:
    # ── Map: single LLM call (small feed) ─────────────────────────
    prompt = get_summary_prompt(feed_with_date)
    response = llm.invoke([HumanMessage(content=prompt)])
    state.summary = response.content
else:
    # ── Map: one LLM call per chunk ────────────────────────────────
    partial_summaries = []
    for start in range(0, len(post_blocks), CHUNK_SIZE):
        chunk_text = "\n".join(post_blocks[start : start + CHUNK_SIZE])
        resp = llm.invoke([HumanMessage(content=get_summary_prompt(chunk_text))])
        partial_summaries.append(resp.content)

    # ── Reduce: merge all partial summaries ────────────────────────
    merge_prompt = get_chunk_merge_prompt(partial_summaries)
    merged = llm.invoke([HumanMessage(content=merge_prompt)])
    state.summary = merged.content
```

This pattern is commonly implemented in LangGraph by splitting it across multiple nodes (map → reduce nodes) or using LangGraph's built-in `Send` API. Here it is implemented within a single node for simplicity, which is valid when the map step is fast and the number of chunks stays small.

**Configuration** (`src/bluesky_feed_agent/config.py`):
```python
CHUNK_SIZE = 30  # max post blocks per LLM call
```

---

## 13. LangChain Integration

**Source**: `src/bluesky_feed_agent/agent/graph.py`, lines 7–8

LangGraph is designed to work alongside [LangChain](https://github.com/langchain-ai/langchain). This agent uses:

```python
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
```

| LangChain Component | Role in This Agent |
|---------------------|--------------------|
| `ChatGoogleGenerativeAI` | LLM wrapper for Gemini 2.5 Flash, used in `summarize_feed_node` |
| `HumanMessage` | Message type passed to `llm.invoke([HumanMessage(content=prompt)])` |

The LLM instance is created once and cached as a module-level singleton (`_llm_instance`) to avoid re-authenticating on every node call:

```python
_llm_instance: ChatGoogleGenerativeAI | None = None

def _get_llm() -> ChatGoogleGenerativeAI:
    global _llm_instance
    if _llm_instance is None:
        api_key = get_openai_api_key()
        _llm_instance = ChatGoogleGenerativeAI(
            model="models/gemini-2.5-flash",
            temperature=0.7,
            google_api_key=api_key,
        )
    return _llm_instance
```

This singleton pattern is independent of LangGraph itself but is a common practice in LangGraph agents to keep node invocations lightweight.

---

## 14. Deployment Configuration (langgraph.json)

**Source**: `langgraph.json`

```json
{
  "dependencies": [{"type": "python", "path": "./pyproject.toml"}],
  "pip_installer": "uv"
}
```

`langgraph.json` is picked up by the **LangGraph CLI** and the **LangGraph Cloud** deployment platform. It tells the deployment tooling:

- Which Python package to install (the local package defined in `pyproject.toml`).
- Which package manager to use (`uv`).

When running locally via `langgraph dev` or deploying to LangGraph Cloud, this file is used to scaffold the runtime environment automatically.

---

## 15. Full Data-Flow Diagram

```
                 ┌─────────────────────┐
                 │   Caller / CLI       │
                 │ BlueskyFeedState(    │
                 │   user_handle=...   │
                 │ )                   │
                 └──────────┬──────────┘
                            │ agent.invoke(initial_state)
                            ▼
                   ┌──────────────────┐
    ENTRY POINT ──►│   fetch_feed     │  reads: user_handle
                   │                  │  writes: posts  OR  error
                   └────────┬─────────┘
                            │
              should_summarize(state)  ← conditional edge
                   ┌────────┴─────────┐
              error?│                 │ success?
              no posts?               │
                   ▼                  ▼
        ┌──────────────────┐  ┌──────────────────┐
        │  error_handler   │  │   format_feed     │  reads: posts
        │                  │  │                   │  writes: raw_feed_text
        │  (logs error)    │  │                   │  clears: posts=[]
        └────────┬─────────┘  └────────┬──────────┘
                 │                     │ direct edge
                 │                     ▼
                 │           ┌──────────────────┐
                 │           │    summarize      │  reads: raw_feed_text
                 │           │                   │  writes: summary
                 │           │  (chunking if     │  clears: raw_feed_text=None
                 │           │   >30 blocks)     │
                 │           └────────┬──────────┘
                 │                    │ direct edge
                 └──────────┬─────────┘
                            ▼
                          END
                            │
                   agent.invoke returns final BlueskyFeedState
                            │
                   ┌────────▼────────────────────────────────┐
                   │  run_feed_summary_agent() (async runner) │
                   │  • await TTS generation                  │
                   │  • await email send (executor)           │
                   │  • await Telegram send (executor)        │
                   └─────────────────────────────────────────┘
```

### Node Summary Table

| Node | LangGraph role | Input fields | Output fields | Conditional? |
|------|---------------|-------------|--------------|-------------|
| `fetch_feed` | Entry node | `user_handle` | `posts`, `error` | No |
| `format_feed` | Middle node | `posts` | `raw_feed_text` | No |
| `summarize` | Middle node | `raw_feed_text` | `summary` | No |
| `error_handler` | Error sink | `error` | _(unchanged)_ | No |
| `should_summarize` | Conditional router | `error`, `posts` | _(routing only)_ | Yes |
| `END` | Terminal sentinel | — | — | — |
