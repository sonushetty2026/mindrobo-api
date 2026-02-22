# API Specification for Issue #23 — Knowledge Ingestion

This document defines the API endpoints needed for the new onboarding flow.

**Frontend Agent:** Already implemented the 3-step UI (`/onboarding`)  
**Ingestion Agent:** Needs to implement these two endpoints

---

## Required Endpoints

### 1. POST /api/v1/knowledge/extract

**Purpose:** Extract knowledge chunks from a URL or PDF without saving to database.

**Request (URL extraction):**
```json
{
  "url": "https://example.com/services",
  "business_id": "uuid-string"
}
```

**Request (PDF upload):**
- Content-Type: `multipart/form-data`
- Fields:
  - `file`: PDF file (binary)
  - `business_id`: string

**Response (200 OK):**
```json
{
  "chunks": [
    {
      "id": "chunk-0",
      "content": "We offer plumbing services including drain cleaning, pipe repair, and water heater installation.",
      "source_type": "services",
      "metadata": {
        "url": "https://example.com/services",
        "title": "Our Services"
      }
    },
    {
      "id": "chunk-1",
      "content": "Business hours: Monday-Friday 8am-6pm, Saturday 9am-4pm. Closed Sundays.",
      "source_type": "contact",
      "metadata": {
        "url": "https://example.com/contact"
      }
    }
  ],
  "source": {
    "type": "url",
    "value": "https://example.com"
  }
}
```

**Response (422 Unprocessable Entity):**
```json
{
  "detail": "Could not extract content from URL"
}
```

**Chunking Strategy:**
- Split content into 200-500 character chunks (semantic splitting preferred)
- Each chunk should be a complete thought/sentence
- Include metadata: source_type (services, faq, about, contact, menu, webpage)
- Preserve source attribution (URL or PDF filename)

---

### 2. POST /api/v1/knowledge/publish

**Purpose:** Save approved chunks to the BusinessKnowledge table.

**Request:**
```json
{
  "business_id": "uuid-string",
  "chunks": [
    {
      "id": "chunk-0",
      "content": "We offer plumbing services including drain cleaning...",
      "source_type": "services",
      "metadata": {
        "url": "https://example.com/services",
        "title": "Our Services"
      }
    },
    {
      "id": "chunk-2",
      "content": "Business hours: Monday-Friday 8am-6pm...",
      "source_type": "contact",
      "metadata": {
        "url": "https://example.com/contact"
      }
    }
  ]
}
```

**Response (201 Created):**
```json
{
  "published_count": 2,
  "entries": [
    {
      "id": "uuid-1",
      "business_id": "uuid-string",
      "content": "We offer plumbing services...",
      "source_type": "services",
      "source_url": "https://example.com/services",
      "is_active": true,
      "created_at": "2024-02-22T10:30:00Z"
    },
    {
      "id": "uuid-2",
      "business_id": "uuid-string",
      "content": "Business hours...",
      "source_type": "contact",
      "source_url": "https://example.com/contact",
      "is_active": true,
      "created_at": "2024-02-22T10:30:00Z"
    }
  ]
}
```

**Response (404 Not Found):**
```json
{
  "detail": "Business not found"
}
```

---

## Database Schema

The `knowledge_entries` (or `BusinessKnowledge`) table should support:

```sql
CREATE TABLE knowledge_entries (
  id UUID PRIMARY KEY,
  business_id UUID NOT NULL REFERENCES businesses(id),
  content TEXT NOT NULL,
  source_type VARCHAR(50),  -- 'services', 'faq', 'about', 'contact', 'menu', 'webpage'
  source_url TEXT,
  title VARCHAR(255),
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## Implementation Notes for Ingestion Agent

### For URL Extraction:
1. Use existing scraper service (`app/services/scraper.py`)
2. Split scraped content into chunks (200-500 chars)
3. Return chunks immediately (no DB save)
4. Infer `source_type` from URL/content (faq, services, about, contact)

### For PDF Extraction:
1. Use a PDF parsing library (e.g., `PyPDF2` or `pdfplumber`)
2. Extract text content
3. Split into chunks
4. source_type = 'menu' (for restaurant menus) or 'document' (generic)

### For Publishing:
1. Validate `business_id` exists
2. Create one `KnowledgeEntry` per chunk
3. Store `source_url` and `source_type` from chunk metadata
4. Return list of created entries

---

## Testing Acceptance Criteria

- [ ] Can extract from a real website URL (e.g., https://example.com)
- [ ] Can extract from a PDF file upload
- [ ] Chunks are 200-500 characters each
- [ ] Can publish selected chunks to database
- [ ] Published chunks appear in `/api/v1/knowledge/{business_id}` list
- [ ] Frontend UI flows work end-to-end

---

## Coordination

**Frontend Agent** has:
- ✅ Built the 3-step UI (`app/templates/onboarding.html`)
- ✅ Updated `/api/v1/onboarding/` endpoint to serve new template
- ✅ JavaScript calls `/extract` and `/publish` endpoints

**Ingestion Agent** needs to:
- [ ] Implement `/api/v1/knowledge/extract` endpoint
- [ ] Implement `/api/v1/knowledge/publish` endpoint
- [ ] Add PDF parsing capability
- [ ] Test with real URL and PDF

Once Ingestion completes their endpoints, the feature is ready for QA testing.
