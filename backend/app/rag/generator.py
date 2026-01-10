from __future__ import annotations
import json
from typing import Dict, List

from openai import OpenAI
from app.core.config import settings
from app.core.logger import setup_logger

logger = setup_logger(__name__)

# Initialize Groq Client safely
client = None
if settings.GROQ_API_KEY:
    try:
        client = OpenAI(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )
        logger.info(f"✅ Groq Client Configured (Model: {settings.LLM_MODEL})")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Groq client: {e}")
else:
    logger.warning("⚠️ GROQ_API_KEY missing. LLM features will be disabled.")

def contextualize_question(question: str, history: List[dict]) -> str:
    if "summarize" in question.lower() or not history or not client:
        return question
    
    messages = [{"role": "system", "content": "Rewrite the user's question to be a specific search query based on the history."}]
    for msg in history[-3:]:
        role = "user" if msg.get("role") == "user" else "assistant"
        messages.append({"role": role, "content": msg.get("content", "")})
    messages.append({"role": "user", "content": f"Rewrite: {question}"})
    
    try:
        resp = client.chat.completions.create(
            model=settings.LLM_MODEL, messages=messages, temperature=0.3
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return question

def generate_hyde_doc(question: str) -> str:
    if not client: return question
    try:
        resp = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": "Write a hypothetical answer to the user's question. Be direct."},
                {"role": "user", "content": question},
            ],
            temperature=0.5,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"HyDE generation failed: {e}")
        return question

def analyze_content(contexts: List[str]) -> Dict[str, object]:
    if not client or not contexts:
        return {"topics": [], "type": "Unknown", "summary": "Analysis unavailable."}

    sample_text = "\n".join(contexts[:2] + contexts[-2:] if len(contexts) > 4 else contexts)
    prompt = (
        "Analyze this text sample. Return JSON with keys: 'topics' (list[str]), "
        "'type' (str), 'summary' (str).\n\n" + sample_text[:3000]
    )

    try:
        resp = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        return json.loads(resp.choices[0].message.content)
    except Exception:
        return {"topics": ["General"], "type": "Web Content", "summary": "Content indexed successfully."}

def generate_answer(question: str, contexts: list, summary_mode: bool = False) -> dict:
    if not client: 
        return {"answer": "LLM Service Unavailable. Check API Key.", "refusal": True, "suggestions": []}

    context_text = "\n\n".join(contexts)
    
    if summary_mode:
        sys_msg = "Summarize the text. Then output '<<<FOLLOWUP>>>' and 3 questions."
    else:
        sys_msg = "Answer using ONLY the context. Then output '<<<FOLLOWUP>>>' and 3 questions."

    try:
        resp = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {question}"}
            ],
            temperature=0.3
        )
        
        full_text = resp.choices[0].message.content.strip()
        parts = full_text.split("<<<FOLLOWUP>>>")
        answer = parts[0].strip()
        suggestions = []
        
        if len(parts) > 1:
            raw_sug = parts[1].strip().split('\n')
            suggestions = [s.strip().lstrip('-•123. ') for s in raw_sug if s.strip()][:3]

        return {"answer": answer, "refusal": False, "suggestions": suggestions}
        
    except Exception as e:
        logger.error(f"Generation Error: {e}")
        return {"answer": "Error generating answer.", "refusal": True, "suggestions": []}