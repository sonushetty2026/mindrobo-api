"""Business metadata extractor service.

Analyzes scraped website content to extract business information:
- Business name
- Business description  
- Services and pricing
- Owner/contact information

Uses AI/patterns to identify key business metadata from content.
"""

import logging
import re
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


def extract_business_metadata(content: str, title: str = "") -> Dict[str, Optional[str]]:
    """Extract business information from website content.
    
    Args:
        content: Raw text content from website
        title: Page title
    
    Returns:
        Dict with extracted business metadata:
        - business_name: Extracted or guessed business name
        - business_description: What the business does
        - services_and_prices: Services offered and pricing
        - owner_name: Owner/contact name if found
        - phone: Phone number if found
        - email: Email if found
    """
    result = {
        "business_name": None,
        "business_description": None,
        "services_and_prices": None,
        "owner_name": None,
        "phone": None,
        "email": None,
    }
    
    # Extract business name (from title first, then content patterns)
    result["business_name"] = _extract_business_name(content, title)
    
    # Extract business description
    result["business_description"] = _extract_business_description(content)
    
    # Extract services and pricing
    result["services_and_prices"] = _extract_services_and_prices(content)
    
    # Extract owner name
    result["owner_name"] = _extract_owner_name(content)
    
    # Extract contact info
    result["phone"] = _extract_phone(content)
    result["email"] = _extract_email(content)
    
    logger.info("Extracted business metadata: name=%s, desc_len=%d, services_len=%d", 
                result["business_name"], 
                len(result["business_description"] or ""),
                len(result["services_and_prices"] or ""))
    
    return result


def _extract_business_name(content: str, title: str = "") -> Optional[str]:
    """Extract business name from title or content."""
    # Clean up title first
    if title:
        # Remove common website suffixes
        clean_title = re.sub(r'\s*[-|]\s*(Home|Services|Contact|About|Professional|Company|LLC|Inc).*$', '', title, flags=re.IGNORECASE)
        clean_title = re.sub(r'\s*[-|]\s*[A-Z]{2}\s*$', '', clean_title)  # Remove state codes
        clean_title = clean_title.strip()
        if clean_title and len(clean_title) > 2:
            return clean_title
    
    # Look for business name patterns in content
    patterns = [
        r'Welcome to ([A-Z][A-Za-z\s&]+(?:LLC|Inc|Company|Co|Corporation|Corp|Services|Solutions|Group)?)',
        r'([A-Z][A-Za-z\s&]+(?:LLC|Inc|Company|Co|Services|Solutions|Group)) (?:is|was|has been|specializes)',
        r'Contact ([A-Z][A-Za-z\s&]+(?:LLC|Inc|Company|Co|Services|Solutions|Group))',
        r'About ([A-Z][A-Za-z\s&]+(?:LLC|Inc|Company|Co|Services|Solutions|Group))',
        r'([A-Z][A-Za-z\s&]+(?:Pool|Cleaning|Lawn|HVAC|Plumbing|Electric|Construction|Maintenance)(?:\s+(?:Service|Company|Co|LLC|Inc))?)',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            name = match.group(1).strip()
            if 3 <= len(name) <= 50:  # Reasonable business name length
                return name
    
    # If nothing found, try extracting from first meaningful line
    lines = content.split('\n')[:10]  # First 10 lines
    for line in lines:
        line = line.strip()
        if re.match(r'^[A-Z][A-Za-z\s&]+(LLC|Inc|Company|Co|Services|Solutions|Group)$', line):
            return line
    
    return None


def _extract_business_description(content: str) -> Optional[str]:
    """Extract business description from content."""
    # Look for description patterns
    patterns = [
        r'We are a ([^.]{20,200})\.',
        r'We specialize in ([^.]{20,200})\.',
        r'We provide ([^.]{20,200})\.',
        r'Our company ([^.]{20,200})\.',
        r'(?:About us|About|Our Story)[\s\n]*([A-Z][^.]{30,300})\.',
        r'Welcome.*?We ([^.]{30,200})\.',
        r'serving.{0,20}([^.]{30,200})\.',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)
        for match in matches:
            desc = match.group(1).strip()
            # Clean up the description
            desc = re.sub(r'\s+', ' ', desc)  # Normalize whitespace
            if 30 <= len(desc) <= 500:  # Reasonable description length
                return desc
    
    # Fallback: look for first substantial paragraph mentioning services
    paragraphs = content.split('\n\n')[:10]  # First 10 paragraphs
    for para in paragraphs:
        para = para.strip()
        if (50 <= len(para) <= 400 and 
            re.search(r'(?:service|repair|maintenance|cleaning|installation|professional|experienced)', para, re.IGNORECASE)):
            # Clean it up
            para = re.sub(r'\s+', ' ', para)
            return para
    
    return None


def _extract_services_and_prices(content: str) -> Optional[str]:
    """Extract services and pricing information."""
    services = []
    
    # Look for pricing patterns
    price_patterns = [
        r'([A-Z][A-Za-z\s]+)\s*[-–]\s*\$(\d+(?:,\d+)?(?:\.\d+)?)\s*/?\s*(\w+)?',
        r'([A-Z][A-Za-z\s]+):\s*\$(\d+(?:,\d+)?(?:\.\d+)?)\s*/?\s*(\w+)?',
        r'\$(\d+(?:,\d+)?(?:\.\d+)?)\s*/?\s*(\w+)?\s*[-–]\s*([A-Z][A-Za-z\s]+)',
    ]
    
    for pattern in price_patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            if len(match.groups()) >= 3:
                service, price, unit = match.group(1), match.group(2), match.group(3) or ""
                services.append(f"{service.strip()} - ${price}/{unit}".strip("/"))
    
    # Look for service lists without prices
    service_patterns = [
        r'Services.*?:(.{20,300}?)(?:\n\n|\n[A-Z]|$)',
        r'We (?:offer|provide)(.{20,300}?)(?:\.|$)',
        r'(?:Our|Available) services include(.{20,300}?)(?:\.|$)',
        r'•\s*([A-Z][A-Za-z\s]+(?:service|repair|cleaning|maintenance|installation))',
    ]
    
    for pattern in service_patterns:
        matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)
        for match in matches:
            service_text = match.group(1).strip()
            # Split on bullets or newlines
            service_items = re.split(r'[•\n-]', service_text)
            for item in service_items:
                item = item.strip()
                if 5 <= len(item) <= 100:  # Reasonable service length
                    services.append(item)
    
    if services:
        # Deduplicate and format
        unique_services = list(dict.fromkeys(services))  # Preserve order, remove dupes
        return '\n'.join(f"• {service}" for service in unique_services[:10])  # Max 10 services
    
    return None


def _extract_owner_name(content: str) -> Optional[str]:
    """Extract owner/contact person name."""
    patterns = [
        r'Contact ([A-Z][a-z]+ [A-Z][a-z]+)',
        r'Owner:?\s*([A-Z][a-z]+ [A-Z][a-z]+)',
        r'Founded by ([A-Z][a-z]+ [A-Z][a-z]+)',
        r'([A-Z][a-z]+ [A-Z][a-z]+),?\s*Owner',
        r'([A-Z][a-z]+ [A-Z][a-z]+),?\s*Founder',
        r'Call ([A-Z][a-z]+ [A-Z][a-z]+)',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, content, re.MULTILINE)
        for match in matches:
            name = match.group(1).strip()
            # Basic validation
            if 3 <= len(name) <= 40 and ' ' in name:
                return name
    
    return None


def _extract_phone(content: str) -> Optional[str]:
    """Extract phone number."""
    patterns = [
        r'\((\d{3})\)\s*(\d{3})-(\d{4})',
        r'(\d{3})[-.](\d{3})[-.](\d{4})',
        r'(\d{3})\s+(\d{3})\s+(\d{4})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            if len(match.groups()) == 3:
                return f"({match.group(1)}) {match.group(2)}-{match.group(3)}"
    
    return None


def _extract_email(content: str) -> Optional[str]:
    """Extract email address."""
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(pattern, content)
    if match:
        email = match.group(0).lower()
        # Skip common non-business emails
        if not re.search(r'@(gmail|yahoo|hotmail|outlook|aol|live|msn)', email):
            return email
    
    return None


def generate_placeholder_text(extracted_data: Dict[str, Optional[str]]) -> Dict[str, str]:
    """Generate helpful placeholder text based on extracted data."""
    placeholders = {
        "business_name": "Enter your business name (e.g., Tampa Pool Pro, ABC Lawn Care)",
        "business_description": "Describe what your business does (e.g., We're a pool cleaning and maintenance company serving the Tampa Bay area)",
        "services_and_prices": "List your main services and prices (e.g., Pool cleaning - $150/visit, Equipment repair - $85/hr)",
        "owner_name": "Your name or business owner's name (e.g., Mike Johnson, Sarah Williams)",
    }
    
    # If we extracted data, show examples based on what we found
    if extracted_data.get("business_name"):
        placeholders["business_name"] = f"Your business name (we found: {extracted_data['business_name']})"
    
    if extracted_data.get("owner_name"):
        placeholders["owner_name"] = f"Owner name (we found: {extracted_data['owner_name']})"
    
    # Add industry-specific examples if we can detect the industry
    content = (extracted_data.get("business_description") or "") + " " + (extracted_data.get("services_and_prices") or "")
    
    if re.search(r'pool|swimming|chlorine|chemical', content, re.IGNORECASE):
        placeholders["services_and_prices"] = "Pool cleaning - $150/visit, Equipment repair - $85/hr, Chemical balancing - included"
    elif re.search(r'lawn|grass|landscaping|mowing', content, re.IGNORECASE):
        placeholders["services_and_prices"] = "Lawn mowing - $75/visit, Landscaping - $120/hr, Fertilization - $45/treatment"
    elif re.search(r'hvac|heating|cooling|air', content, re.IGNORECASE):
        placeholders["services_and_prices"] = "AC repair - $150/visit, System maintenance - $200/year, Installation - $3500+"
    
    return placeholders