# Beliscan

Multi-agent system for real estate valuation workflows built on top of **LangGraph**, **A2A**, **MCP**, **MongoDB**, and **MinIO**.

## What this project does

The system automates the full valuation-candidate pipeline:

1. Receives a valuation object description.
2. Searches candidate analogs through DOM.RIA via MCP.
3. Stores candidates and run state in MongoDB.
4. Validates each candidate with a dedicated validator agent.
5. Captures proof screenshots for approved candidates.
6. Moves proof objects from temporary MinIO storage to permanent valuation storage.
7. Returns a valuation run identifier that can later be used by external software to fetch results.

---

## Main components

### MCP services

- **`dom_ria_mcp`**  
  MCP server for working with DOM.RIA:
  - address resolution
  - search URL and search API parameter building
  - candidate ID search
  - property retrieval by ID

- **`mongo_cache_mcp`**  
  MCP server for working with the property cache in MongoDB.

- **`mongo_store_mcp`**  
  MCP server for working with valuation runs, candidates, statuses, proof paths, and final storage state.

- **`screenshot_mcp`**  
  MCP server that opens listing pages, captures screenshots, and uploads them to temporary MinIO storage.

- **`object_move_mcp`**  
  MCP server for moving proof objects from temporary MinIO storage to permanent valuation storage.

---

### Agents

- **`research_agent`**  
  Finds candidate analogs using DOM.RIA MCP tools and returns:
  - `search_url`
  - `candidates_ids`

- **`validator_agent`**  
  Validates one candidate against the valuation object and returns:
  - decision/status
  - reason
  - Mongo cache link
  - normalized payload

- **`proof_agent`**  
  Captures and stores screenshot proof for a listing URL.

- **`supervisor_agent`**  
  Orchestrates the full workflow:
  - registers valuation run
  - calls research agent
  - stores candidates
  - loops through candidate validation
  - triggers proof creation
  - moves proof objects to permanent MinIO storage
  - finalizes the run

---

## Project structure

```text
src/
  dom_ria_mcp/
  mongo_cache_mcp/
  mongo_store_mcp/
  object_move_mcp/
  proof_agent/
  research_agent/
  screenshot_mcp/
  supervisor_agent/
  validator_agent/
  valuation_store_api/
```

Supporting files:
- `.env.example`
- `.gitignore`
- `pyproject.toml`
- `uv.lock`
- `certs/*.pem`

---

## Tech stack

- Python 3.13
- LangGraph
- LangChain
- LangChain OpenAI
- FastMCP / MCP
- A2A
- MongoDB
- MinIO
- `uv` for dependency management

---

## Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd beliscan
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Configure environment variables

Copy root env:

```bash
cp .env.example .env
```

Also copy service-level env files if needed:

```bash
cp src/dom_ria_mcp/.env.example src/dom_ria_mcp/.env
cp src/mongo_cache_mcp/.env.example src/mongo_cache_mcp/.env
cp src/mongo_store_mcp/.env.example src/mongo_store_mcp/.env
cp src/object_move_mcp/.env.example src/object_move_mcp/.env
cp src/proof_agent/.env.example src/proof_agent/.env
cp src/research_agent/.env.example src/research_agent/.env
cp src/screenshot_mcp/.env.example src/screenshot_mcp/.env
cp src/supervisor_agent/.env.example src/supervisor_agent/.env
cp src/validator_agent/.env.example src/validator_agent/.env
```

Fill in:
- OpenAI connection settings
- MongoDB settings
- MinIO settings
- A2A host/port settings
- MCP URLs between services

---

## Running the system

Recommended startup order:

### 1. DOM.RIA MCP

```bash
uv run python -m dom_ria_mcp.dom_ria_server
```

### 2. Mongo cache MCP

```bash
uv run python -m mongo_cache_mcp.mongo_cache_server
```

### 3. Mongo store MCP

```bash
uv run python -m mongo_store_mcp.mongo_store_server
```

### 4. Screenshot MCP

```bash
uv run python -m screenshot_mcp.screenshot_server
```

### 5. Object move MCP

```bash
uv run python -m object_move_mcp.object_move_server
```

### 6. Research agent (A2A)

```bash
uv run python -m research_agent.a2a_server
```

### 7. Validator agent (A2A)

```bash
uv run python -m validator_agent.a2a_server
```

### 8. Proof agent (A2A)

```bash
uv run python -m proof_agent.a2a_server
```

### 9. Supervisor agent

```bash
uv run python -m supervisor_agent.run_agent
```

---

## Typical workflow

### Research phase
Supervisor sends valuation description to `research_agent`.

`research_agent`:
- detects asset kind
- detects property type/subtype
- resolves location
- builds DOM.RIA search query
- collects candidate IDs

### Validation phase
Supervisor:
- stores candidate IDs
- pulls unprocessed candidates from Mongo
- sends them one-by-one to `validator_agent`

`validator_agent`:
- checks Mongo cache
- fetches property if needed
- validates analog relevance
- stores payload in cache/store
- returns decision

### Proof phase
For approved candidates:
- supervisor sends listing URL to `proof_agent`
- `proof_agent` creates screenshot in temporary MinIO
- supervisor saves proof path
- supervisor calls `object_move_mcp`
- object is copied to permanent valuation storage

### Finalization phase
Supervisor returns:
- generated valuation run ID
- external object ID
- final storage references

---

## Result storage

### MongoDB stores
The system keeps:
- valuation runs
- analog candidates
- validation results
- cached property payloads
- proof and MinIO paths

### MinIO stores
The system uses:
- temporary/trash bucket for fresh screenshot uploads
- permanent valuation bucket for final proof objects

---

## Development notes

### Configuration
Prefer strongly typed config values, especially ports:
- `a2a_port` should be `int`
- Mongo and MinIO hosts should be validated at startup

### MCP tool contracts
For MCP tools, flat arguments are usually easier than wrapping everything in `request: BaseModel`, unless strict request envelopes are required.

### Proof object TTL
Object move only copies metadata like `expires_at`.  
Automatic deletion requires either:
- lifecycle policy on MinIO bucket/prefix
- or a separate cleanup job

### Warmup
A2A agents should warm up their graphs on startup to avoid cold-start latency.

---

## Example supervisor input

```python
{
    "external_object_id": "object-123",
    "valuation_description": "1-кімнатна квартира на вул. Андріївська 9, Київ type=flat rooms=1 is_commercial=0",
    "target_count": 10
}
```

---

## Useful scripts

Run supervisor test flow:

```bash
uv run python -m supervisor_agent.run_test_run_agent
```

Run proof agent directly for debugging:

```bash
uv run python -m proof_agent.a2a_server
```

---

## Future improvements

- Add more real estate sources via new MCP servers
- Batch candidate validation
- Batch proof creation with bounded concurrency
- Automatic MinIO cleanup by TTL
- API layer for external systems to fetch valuation run results

---

# Author

**ai_and_ml_guru**

---

# Usage Restrictions

Use, redistribution, or modification of this software **without explicit permission from the author is forbidden**.