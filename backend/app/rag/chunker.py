import re
from typing import List, Dict
from app.core.config import settings
from app.core.logger import setup_logger

logger = setup_logger(__name__)

def chunk_pages_smart(pages: List[Dict]) -> List[Dict]:
    """
    Split text into semantic chunks respecting sentence boundaries.
    """
    chunks = []
    seen_hashes = set()
    blacklist = [
        "all rights reserved", "privacy policy", "cookie policy", 
        "terms of use", "subscribe to newsletter"
    ]
    
    for page in pages:
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', page["text"]).strip()
        
        # Split by sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        current_chunk = []
        current_len = 0
        chunk_id = 0
        
        for sentence in sentences:
            sentence_len = len(sentence)
            
            # Check if chunk is full
            if current_len + sentence_len > settings.CHUNK_SIZE and current_chunk:
                text_block = " ".join(current_chunk)
                
                # Quality Checks
                if len(text_block) > 50 and not any(b in text_block.lower() for b in blacklist):
                    if hash(text_block) not in seen_hashes:
                        seen_hashes.add(hash(text_block))
                        chunks.append({
                            "id": f"{page['url']}::{chunk_id}",
                            "text": text_block,
                            "source": page["url"]
                        })
                        chunk_id += 1
                
                # Create Overlap
                overlap_len = 0
                new_chunk = []
                for s in reversed(current_chunk):
                    if overlap_len >= settings.CHUNK_OVERLAP: break
                    new_chunk.insert(0, s)
                    overlap_len += len(s)
                current_chunk = new_chunk
                current_len = overlap_len
            
            current_chunk.append(sentence)
            current_len += sentence_len
            
    logger.info(f"📦 Created {len(chunks)} chunks from {len(pages)} pages")
    return chunks