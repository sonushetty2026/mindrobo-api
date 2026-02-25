"""
Vector-powered knowledge base system using pgvector.
Provides fast semantic search for AI agents answering customer calls.
"""

import logging
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import httpx
import os
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class VectorKnowledgeBase:
    def __init__(self):
        self.api_key = os.getenv('AZURE_OPENAI_API_KEY', '')
        self.endpoint = os.getenv('AZURE_OPENAI_ENDPOINT', '').rstrip('/')
        self.api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-01')
        self.embedding_deployment = os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT', 'text-embedding-3-small')
    
    async def add_knowledge(self, 
                           db: AsyncSession,
                           business_id: str,
                           content: str, 
                           source: str,
                           knowledge_type: str = 'general',
                           tier: int = 2) -> bool:
        """Add knowledge with vector embedding to the database.
        
        Args:
            business_id: UUID of the business
            content: Text content to embed
            source: Source URL/file name
            knowledge_type: services, pricing, hours, contact, etc.
            tier: 1 (user-edited) or 2 (auto-extracted)
        """
        try:
            # Generate embedding
            embedding = await self._get_embedding(content)
            if not embedding:
                logger.error("Failed to generate embedding for content")
                return False
            
            # Insert into knowledge_entries with vector
            await db.execute(text("""
                INSERT INTO knowledge_entries 
                (id, business_id, content, source, knowledge_type, tier, embedding, created_at, updated_at)
                VALUES (gen_random_uuid(), :business_id, :content, :source, :knowledge_type, :tier, :embedding, NOW(), NOW())
            """), {
                'business_id': business_id,
                'content': content,
                'source': source,
                'knowledge_type': knowledge_type,
                'tier': tier,
                'embedding': embedding
            })
            
            await db.commit()
            logger.info(f"Added knowledge entry for business {business_id}: {knowledge_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add knowledge: {e}")
            await db.rollback()
            return False
    
    async def search_knowledge(self, 
                              db: AsyncSession,
                              business_id: str, 
                              query: str, 
                              limit: int = 5,
                              knowledge_types: Optional[List[str]] = None) -> List[Dict]:
        """Search knowledge base using vector similarity.
        
        Returns relevant knowledge entries with similarity scores.
        """
        try:
            # Generate query embedding
            query_embedding = await self._get_embedding(query)
            if not query_embedding:
                return []
            
            # Build type filter
            type_filter = ""
            if knowledge_types:
                types_str = "', '".join(knowledge_types)
                type_filter = f"AND knowledge_type IN ('{types_str}')"
            
            # Vector similarity search with pgvector
            result = await db.execute(text(f"""
                SELECT 
                    content, 
                    source, 
                    knowledge_type, 
                    tier,
                    (embedding <-> :query_embedding::vector) as distance,
                    (1 - (embedding <-> :query_embedding::vector)) as similarity
                FROM knowledge_entries 
                WHERE business_id = :business_id 
                {type_filter}
                ORDER BY embedding <-> :query_embedding::vector 
                LIMIT :limit
            """), {
                'business_id': business_id,
                'query_embedding': query_embedding,
                'limit': limit
            })
            
            results = []
            for row in result:
                results.append({
                    'content': row.content,
                    'source': row.source,
                    'knowledge_type': row.knowledge_type,
                    'tier': row.tier,
                    'similarity': float(row.similarity),
                    'distance': float(row.distance)
                })
            
            logger.info(f"Found {len(results)} knowledge entries for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Knowledge search failed: {e}")
            return []
    
    async def get_knowledge_by_type(self, 
                                   db: AsyncSession,
                                   business_id: str, 
                                   knowledge_type: str) -> List[Dict]:
        """Get all knowledge entries of a specific type (e.g., 'pricing', 'services')."""
        try:
            result = await db.execute(text("""
                SELECT content, source, tier, created_at
                FROM knowledge_entries 
                WHERE business_id = :business_id AND knowledge_type = :knowledge_type
                ORDER BY tier ASC, created_at DESC
            """), {
                'business_id': business_id,
                'knowledge_type': knowledge_type
            })
            
            return [
                {
                    'content': row.content,
                    'source': row.source,
                    'tier': row.tier,
                    'created_at': row.created_at
                }
                for row in result
            ]
            
        except Exception as e:
            logger.error(f"Failed to get knowledge by type: {e}")
            return []
    
    async def update_knowledge_tier(self,
                                   db: AsyncSession,
                                   business_id: str,
                                   content: str,
                                   new_tier: int) -> bool:
        """Update knowledge tier (e.g., promote user-edited data to Tier 1)."""
        try:
            await db.execute(text("""
                UPDATE knowledge_entries 
                SET tier = :new_tier, updated_at = NOW()
                WHERE business_id = :business_id AND content = :content
            """), {
                'business_id': business_id,
                'content': content,
                'new_tier': new_tier
            })
            
            await db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to update knowledge tier: {e}")
            return False
    
    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Generate Azure OpenAI embedding for text."""
        if not self.api_key or not self.endpoint:
            logger.warning("Azure OpenAI not configured - cannot generate embeddings")
            return None

        url = f"{self.endpoint}/openai/deployments/{self.embedding_deployment}/embeddings?api-version={self.api_version}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    headers={
                        'api-key': self.api_key,
                        'Content-Type': 'application/json'
                    },
                    json={
                        'input': text[:8000],
                        'encoding_format': 'float'
                    }
                )

                if response.status_code != 200:
                    logger.error(f"Azure OpenAI embeddings error: {response.status_code} - {response.text}")
                    return None

                result = response.json()
                return result['data'][0]['embedding']

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None


# Global instance
vector_kb = VectorKnowledgeBase()
