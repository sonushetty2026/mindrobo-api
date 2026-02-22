# Test Report: Issue #23 Frontend Integration

**Date:** 2026-02-22  
**Tester:** Frontend Agent  
**Live VM:** http://52.159.104.87  
**PR:** #25 (ui/issue-23-onboarding-frontend-v2)

---

## Status: 🔴 BLOCKED - VM Not Responding

### Issue
The live VM at `http://52.159.104.87` is not responding to HTTP requests.

### Tests Attempted

#### 1. Health Check
```bash
curl --max-time 5 http://52.159.104.87/health
```
**Result:** `Connection timed out after 5000 milliseconds`

#### 2. Direct Endpoint Test
```bash
curl --max-time 10 http://52.159.104.87/api/v1/ingest/preview
```
**Result:** Connection timeout (no response)

### Root Cause Analysis
Possible reasons:
1. **Service is down** — mindrobo-api service not running
2. **VM is offline** — Azure VM stopped or deallocated
3. **Firewall/NSG** — Port 80/8000 blocked for external traffic
4. **Wrong IP** — IP address changed after redeployment

---

## Code Changes Made

### Fixed API Endpoint Mismatch
My initial implementation called:
- ❌ `/api/v1/knowledge/extract`
- ❌ `/api/v1/knowledge/publish`

Updated to match merged PR #24:
- ✅ `/api/v1/ingest/preview`
- ✅ `/api/v1/ingest/publish`

### Request Format Updates
1. **Preview endpoint** now uses `FormData` for both URL and PDF:
   ```javascript
   const formData = new FormData();
   formData.append('url', url);
   formData.append('business_id', businessId);
   // or
   formData.append('pdf_file', file);
   formData.append('business_id', businessId);
   ```

2. **Publish endpoint** maps chunks correctly:
   ```javascript
   {
     content: chunk.content,
     source_url: chunk.source_url,
     title: chunk.title,
     content_type: chunk.source_type
   }
   ```

### Response Mapping
Maps API response to frontend state:
```javascript
extractedChunks = data.chunks.map(chunk => ({
  id: chunk.temp_id,
  content: chunk.content,
  source_type: chunk.content_type,
  source_url: chunk.source_url,
  title: chunk.title
}));
```

---

## Next Steps

### Immediate (CEO/Backend):
1. ✅ Check if mindrobo-api service is running:
   ```bash
   ssh azureuser@52.159.104.87 "sudo systemctl status mindrobo-api"
   ```

2. ✅ Verify port 8000 is accessible:
   ```bash
   ssh azureuser@52.159.104.87 "curl http://localhost:8000/health"
   ```

3. ✅ Check Azure NSG rules for port 80/8000

### Once VM is Accessible (Frontend):
1. Test `/onboarding` page loads
2. Test URL extraction with real website
3. Test PDF upload extraction
4. Test chunk review/selection
5. Test publish flow
6. Verify chunks saved to database
7. Check error handling for bad URLs/PDFs

---

## Files Changed in PR #25

- ✅ `app/templates/onboarding.html` (new 3-step UI)
- ✅ `app/api/v1/endpoints/onboarding.py` (updated to serve template)
- ✅ `API_SPEC_ISSUE_23.md` (coordination doc)

**Commits:**
1. `451b211` - Initial UI implementation
2. `1ce74c3` - Fixed API endpoints to match PR #24

---

## Summary

**Frontend work:** ✅ Complete and pushed to PR #25  
**API integration:** 🔴 Blocked — VM not responding  
**Action required:** CEO/Backend team to bring VM online  

Once VM is accessible, I can complete end-to-end testing and report any endpoint-specific errors.
