"""
Professional AI-powered business metadata extraction.

Uses OpenAI GPT to intelligently extract business information from websites,
filtering out noise and focusing on customer-relevant content.
"""

import logging
import json
import re
import asyncio
from typing import Dict, Optional, List
import httpx
import os

logger = logging.getLogger(__name__)

class BusinessExtractor:
    def __init__(self):
        self.api_key = os.getenv('AZURE_OPENAI_API_KEY', '')
        self.endpoint = os.getenv('AZURE_OPENAI_ENDPOINT', '').rstrip('/')
        self.api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-01')
        self.chat_deployment = os.getenv('AZURE_OPENAI_CHAT_DEPLOYMENT', 'gpt-4o-mini')
        
    async def extract_business_info(self, content: str, title: str = '', url: str = '') -> Dict[str, Optional[str]]:
        """Extract business information using AI analysis."""
        
        if not self.api_key or not self.endpoint:
            logger.warning("Azure OpenAI not configured - using fallback extraction")
            return self._fallback_extraction(content, title)
        
        try:
            # Step 1: Clean and filter content
            filtered_content = self._filter_content(content)
            
            # Step 2: AI extraction
            extracted_data = await self._ai_extract(filtered_content, title, url)
            
            # Step 3: Validate and clean results
            return self._validate_results(extracted_data)
            
        except Exception as e:
            logger.error(f"AI extraction failed: {e}")
            return self._fallback_extraction(content, title)
    
    def _filter_content(self, content: str) -> str:
        """Remove noise and focus on business-relevant content."""
        
        # Remove common website noise
        noise_patterns = [
            r'cookie[s]?\s+policy.*?(?=\n\n|\Z)',
            r'privacy\s+policy.*?(?=\n\n|\Z)', 
            r'terms\s+of\s+service.*?(?=\n\n|\Z)',
            r'©.*copyright.*?(?=\n\n|\Z)',
            r'all\s+rights\s+reserved.*?(?=\n\n|\Z)',
            r'follow\s+us.*?(?=\n\n|\Z)',
            r'social\s+media.*?(?=\n\n|\Z)',
            r'newsletter\s+signup.*?(?=\n\n|\Z)',
        ]
        
        filtered = content
        for pattern in noise_patterns:
            filtered = re.sub(pattern, '', filtered, flags=re.IGNORECASE | re.DOTALL)
        
        # Focus on key sections (look for these headings)
        key_sections = []
        section_patterns = [
            r'(about\s+us.*?)(?=\n[A-Z]|\Z)',
            r'(services.*?)(?=\n[A-Z]|\Z)', 
            r'(our\s+services.*?)(?=\n[A-Z]|\Z)',
            r'(what\s+we\s+do.*?)(?=\n[A-Z]|\Z)',
            r'(pricing.*?)(?=\n[A-Z]|\Z)',
            r'(contact.*?)(?=\n[A-Z]|\Z)',
            r'(hours.*?)(?=\n[A-Z]|\Z)',
        ]
        
        for pattern in section_patterns:
            matches = re.finditer(pattern, filtered, re.IGNORECASE | re.DOTALL)
            for match in matches:
                section = match.group(1).strip()
                if len(section) > 50:  # Substantial content
                    key_sections.append(section)
        
        # If we found key sections, use those; otherwise use filtered content
        if key_sections:
            return '\n\n'.join(key_sections)
        else:
            return filtered[:4000]  # Limit for API
    
    async def _ai_extract(self, content: str, title: str, url: str) -> Dict:
        """Use OpenAI to extract business information."""
        
        prompt = f"""Extract business information from this website content. Focus on factual information that would help a customer understand the business.

Website: {url}
Title: {title}

Content:
{content[:3000]}

Extract and return ONLY valid JSON with these fields:
{{
  "business_name": "Full legal business name",
  "business_description": "1-2 sentences describing what the business does and who they serve",
  "services_offered": "List of main services, separated by commas",
  "pricing_info": "Pricing details if mentioned (e.g. '50/visit, 5/hour')",
  "service_area": "Geographic areas served (cities, regions)",
  "business_hours": "Operating hours if mentioned",
  "owner_name": "Owner or key contact person name",
  "phone_number": "Primary phone number",
  "email_address": "Primary email address",
  "specialties": "What makes this business unique or specialized"
}}

Requirements:
- Use exact quotes from the content when possible
- If information is not found, use null
- Keep descriptions professional and customer-focused
- Extract pricing exactly as stated
- Return only the JSON object"""

        headers = {
            'api-key': self.api_key,
            'Content-Type': 'application/json'
        }
        
        payload = {
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.1,
            'max_tokens': 600
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                raise Exception(f"Azure OpenAI API error: {response.status_code} - {response.text}")
            
            result = response.json()
            ai_response = result['choices'][0]['message']['content'].strip()
            
            # Clean up response (remove markdown if present)
            ai_response = re.sub(r'', '', ai_response)
            
            return json.loads(ai_response)
    
    def _validate_results(self, data: Dict) -> Dict[str, Optional[str]]:
        """Validate and clean extracted data."""
        
        def clean_field(value):
            if not value or str(value).lower() in ['null', 'none', 'n/a', 'not found', 'not mentioned']:
                return None
            return str(value).strip()
        
        return {
            'business_name': clean_field(data.get('business_name')),
            'business_description': clean_field(data.get('business_description')),
            'services_and_prices': self._format_services_pricing(
                data.get('services_offered'), 
                data.get('pricing_info')
            ),
            'owner_name': clean_field(data.get('owner_name')),
            'phone': self._clean_phone(data.get('phone_number')),
            'email': self._clean_email(data.get('email_address')),
            'service_area': clean_field(data.get('service_area')),
            'business_hours': clean_field(data.get('business_hours')),
            'specialties': clean_field(data.get('specialties'))
        }
    
    def _format_services_pricing(self, services: str, pricing: str) -> Optional[str]:
        """Combine services and pricing information."""
        if not services:
            return None
            
        result = []
        if services:
            # Split services and clean them up
            service_list = [s.strip() for s in services.split(',') if s.strip()]
            result.extend([f"• {service}" for service in service_list[:5]])
        
        if pricing:
            result.append(f"\nPricing: {pricing}")
            
        return '\n'.join(result) if result else None
    
    def _clean_phone(self, phone: Optional[str]) -> Optional[str]:
        """Clean and validate phone number."""
        if not phone:
            return None
            
        # Extract digits only
        digits = re.sub(r'[^\d]', '', phone)
        
        # Validate US phone number
        if len(digits) == 10 and not digits.startswith('0'):
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits.startswith('1'):
            return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
            
        return None
    
    def _clean_email(self, email: Optional[str]) -> Optional[str]:
        """Clean and validate email address."""
        if not email:
            return None
            
        email = email.lower().strip()
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return email
            
        return None
    
    def _fallback_extraction(self, content: str, title: str) -> Dict[str, Optional[str]]:
        """Fallback extraction when AI is unavailable."""
        
        result = {
            'business_name': None,
            'business_description': None,
            'services_and_prices': None,
            'owner_name': None,
            'phone': None,
            'email': None
        }
        
        # Basic title cleaning for business name
        if title:
            clean_title = re.sub(r'\s*[-|]\s*(Home|Services|Contact).*$', '', title, re.IGNORECASE)
            if 5 <= len(clean_title.strip()) <= 100:
                result['business_name'] = clean_title.strip()
        
        # Phone extraction
        phone_match = re.search(r'\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})', content)
        if phone_match:
            result['phone'] = f"({phone_match.group(1)}) {phone_match.group(2)}-{phone_match.group(3)}"
        
        # Email extraction  
        email_match = re.search(r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b', content)
        if email_match:
            result['email'] = email_match.group(1).lower()
        
        return result

# Global instance
extractor = BusinessExtractor()

async def extract_business_metadata_ai(content: str, title: str = '', url: str = '') -> Dict[str, Optional[str]]:
    """Main extraction function to be used by the API."""
    return await extractor.extract_business_info(content, title, url)
