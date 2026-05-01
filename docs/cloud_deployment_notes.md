# Cloud Deployment Notes (Future Path)

> **Status:** Not deployed. This document describes the intended production architecture on GCP.

## Target Architecture: GCP

```
Internet → Cloud Load Balancer
               ├── Cloud Run (FastAPI backend)
               │     ├── Cloud SQL (PostgreSQL)
               │     ├── Vertex AI Embeddings API
               │     ├── Gemini API via Vertex AI
               │     └── Cloud Storage (documents)
               └── Cloud Storage + CDN (React frontend)

Secret Manager → API keys, DB credentials
Cloud Logging  → Application logs + AI trace logs
Cloud Monitoring → Latency, error rate dashboards
```

## Service Mapping

| Local Component | GCP Equivalent |
|----------------|---------------|
| PostgreSQL (Docker) | Cloud SQL for PostgreSQL |
| ChromaDB (Docker) | Vertex AI Search (enterprise) or Pinecone (managed) |
| Sentence Transformers (CPU) | Vertex AI Embeddings API (`textembedding-gecko`) |
| Gemini API (direct) | Vertex AI — Gemini via `google-cloud-aiplatform` |
| Docker Compose backend | Cloud Run (serverless, auto-scaling) |
| Vite dev server | Cloud Storage + Cloud CDN |
| Local `.env` | Secret Manager |

## Deployment Steps (Future)

### 1. Containerize backend for Cloud Run
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/procurement-copilot-backend ./backend
gcloud run deploy procurement-copilot \
  --image gcr.io/PROJECT_ID/procurement-copilot-backend \
  --platform managed \
  --region us-central1 \
  --set-env-vars DATABASE_URL=... \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest
```

### 2. Cloud SQL
```bash
gcloud sql instances create procurement-db \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=us-central1
```

### 3. Frontend to Cloud Storage
```bash
cd frontend && npm run build
gsutil -m rsync -r dist/ gs://procurement-copilot-frontend/
gcloud compute backend-buckets create procurement-frontend-bucket \
  --gcs-bucket-name=procurement-copilot-frontend
```

### 4. Secret Manager
```bash
gcloud secrets create gemini-api-key --data-file=- <<< "$GEMINI_API_KEY"
gcloud secrets create db-password --data-file=- <<< "$POSTGRES_PASSWORD"
```

## Cost Estimate (Minimal production setup)

| Service | Tier | Monthly Est. |
|---------|------|-------------|
| Cloud Run | 2M requests, 1 vCPU | ~$15 |
| Cloud SQL | db-f1-micro | ~$10 |
| Gemini 1.5 Flash | 1M input tokens | ~$0.075 |
| Cloud Storage | 5GB | ~$0.10 |
| **Total** | | **~$25/month** |

## Vertex AI Embeddings (upgrade path)

Replace `sentence-transformers` with Vertex AI for:
- No model download at startup
- GPU-accelerated batching
- Managed model versioning

```python
from vertexai.language_models import TextEmbeddingModel

model = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")
embeddings = model.get_embeddings(texts)
```

## Vertex AI Search (enterprise RAG)

For large document volumes (>10,000 pages), replace ChromaDB with Vertex AI Search:
- Managed vector index
- Built-in document parsing (PDF, HTML)
- Grounding API integration with Gemini

## Monitoring

Add to Cloud Logging:
- Every AI query (question, role, grounding status)
- Tool calls and latency
- Error rates by endpoint

Set up Cloud Monitoring alerts for:
- Backend error rate > 1%
- P99 latency > 5 seconds
- Database connection pool exhaustion
