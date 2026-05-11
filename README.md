# Earth Monitor

**Multimodal AI Satellite Logistics & Environment Earth Monitor**

The app ties together **natural-language search**, **geocoding**, **Copernicus Sentinel-2 imagery** (when credentials are set), and a **small PyTorch forward pass** used for demo hotspot alerts. The satellite pipeline is the most complete part, and the hotspot head below is lightweight.

## Problem framing

Exploring satellite scenes usually means maps, coordinates, or specialist tools. Here you can phrase a query in plain language, and the backend parses it, resolves a place, and pulls scenes from Copernicus. **Hotspot scores are not real-world hazard forecasts**, they exist to show how a torch model could sit in the same service (see next section).

## Machine learning (what is real vs proof of concept)

**Query side (useful, API-dependent):** Mistral via Hugging Face Inference API extracts `feature` and `location`, and OpenStreetMap (Nominatim) supplies bbox / city / country. Regex fallbacks apply if the LLM is unavailable.

**Hotspot side (`copernicus/inference.py`), proof of concept only**

- **What it does in code:** A tiny **MLP** (two `Linear` layers, ReLU, dropout) is a genuine feed-forward **neural network**, just not a vision model. It reads a **512-D vector** and runs **binary classification** (two logits → softmax). `alertCount` comes from that probability, and **`alertType` is not a multi-class output**, it is picked with a **modulo heuristic** on the same scalar, so the UI can show varied labels without a trained multi-head model.
- **What it does *not* do:** It never sees **image pixels**. Sentinel-2 tiles are fetched elsewhere, and alerts are **not** derived from the raster you see on screen.
- **Training vs runtime:** `model/tuning.py` trains on **fully synthetic** random 512-D data with synthetic binary labels and Optuna-tuned hyperparameters. **`predict_alert` does not load any `state_dict`**, weights stay at random init. Inputs are **SHA-256-seeded fake "embeddings"** from the location string, not semantic vectors.
- **Why not CLIP here:** `model/embedding_service.py` can produce real **CLIP** text/image embeddings, but **`predict_alert` does not call it**, smaller container, faster startup, no extra model download on the hotspot path. Wiring CLIP (or another encoder) in would be a natural next step once you have **labels and a training loop** that actually ship to disk.

**Steps for further improvement of this proof of concept**

- Train on **real inputs** (CLIP or a geo/vision encoder) and **real labels** (hazard catalogs, weather APIs, human annotations), then **`load_state_dict`** in the API.
- Replace the binary + modulo hack with a **proper multi-class or multi-label head** (or structured JSON from an LLM with guardrails).
- **Fuse** parsed query + **embeddings of the returned tile** so risk is tied to content, not only the place name.
- Add a **small eval set and metrics**, and log when the system is in “demo inference” vs “trained checkpoint” so users are not misled.

## Technology choices, trade-offs & scaling

- **PyTorch in FastAPI:** Fine for demos. For heavier models, move inference off the request thread (separate worker, **ONNX**, **TorchServe**, etc.) so you do not block I/O-bound routes or blow RAM on concurrent requests.
- **Mistral via Hugging Face API:** Keeps the Docker image small (no 7B weights in-container). Downside: rate limits and extra network hop. Self-hosting Mistral/`vLLM` is the obvious upgrade if you outgrow the API.
- **GraphQL (Apollo):** One schema for search + hotspots, and clients ask for the fields they need. Caching is trickier than with plain REST + CDN.
- **Spark:** Used for ingestion-style processing of large Sentinel-2 volumes, and local compose runs master + worker mainly to mirror that shape of stack.

## Reproducible code (quick start)

### Prerequisites

- Docker Desktop

### Run the app

`docker compose` starts Kafka, Zookeeper, Spark, OpenSearch, the Copernicus FastAPI service, the Node GraphQL server, and the Angular front end, each in its own container (see Architecture).

1. **API tokens (optional):** Set `COPERNICUS_CLIENT_ID`, `COPERNICUS_CLIENT_SECRET`, and `HUGGINGFACE_TOKEN` in your environment where needed.
2. **Start:** `docker compose up --build`
3. **URLs:**
   - Front end: [http://localhost:80](http://localhost:80)
   - GraphQL: [http://localhost:4000](http://localhost:4000)
   - Spark UI: [http://localhost:8080](http://localhost:8080)
   - OpenSearch: [http://localhost:9200](http://localhost:9200)

## Architecture

**Who talks to whom (read in order)**

1. **You (browser)** open the app served from the **web** container (Angular, port 80 on the host). You only interact with that UI.
2. **Angular** sends **HTTP POST** requests to **`http://localhost:4000/graphql`** on the host. That hits the **server** container (Node + Apollo). The browser **does not** call the Python service or OpenSearch directly.
3. **Node** runs GraphQL resolvers. When it needs satellite data or hotspots, it calls the **copernicus** container over HTTP using the Docker network URL `COPERNICUS_SERVICE_URL` (for example `http://copernicus:5001` inside Compose). On the host, that same service is exposed as port **5001** for debugging.
4. **Python (FastAPI) in copernicus** may call **external** services: Copernicus Data Space (imagery), Hugging Face (Mistral), Nominatim (geocoding). Imagery is returned to the client in the API response, and it is not a long-lived “library” stored inside this repo by default.
5. **OpenSearch, Kafka, Spark** run in their own containers and are part of the same stack for search indexing / streaming / batch processing patterns, and the main UI flow is Angular → Node → Copernicus service (+ those externals).

**What runs in Docker vs outside**

| Piece | Containerized? | Typical persistence |
| --- | --- | --- |
| Angular UI | Yes (`web`) | None (static assets in image) |
| GraphQL API | Yes (`server`) | None |
| Copernicus + PyTorch + parsers | Yes (`copernicus`) | None (stateless, secrets via env) |
| OpenSearch | Yes | Index data inside container volume unless you mount one |
| Kafka / Zookeeper | Yes | Broker logs / topics in container |
| Spark master/worker | Yes | Ephemeral in demo compose |
| Copernicus satellite API, HF Mistral, Nominatim | No (external SaaS / public APIs) | Their systems |

**Stack list**

- Front end: Angular 17  
- API gateway to the UI: Apollo Server / Express (GraphQL) on Node  
- Satellite / ML microservice: FastAPI + PyTorch + query code in `copernicus/`  
- OpenSearch 2.11, Spark 3.4, Kafka + Zookeeper (supporting services in compose)

Architecture diagram (SVG, no extra tools): `docs/earth-monitor-architecture.svg`. Mermaid source: `docs/earth-monitor-architecture.mmd` (optional: `npx @mermaid-js/mermaid-cli` to export PNG/PDF).
