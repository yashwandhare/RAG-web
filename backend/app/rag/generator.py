from openai import OpenAI
import re
from typing import List, Dict
from app.core.config import settings
from app.core.logger import setup_logger

logger = setup_logger(__name__)

# Initialize Groq Client
try:
    client = OpenAI(
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )
    logger.info(f"✅ Groq Client Configured (Model: {settings.LLM_MODEL})")
except Exception as e:
    logger.error(f"❌ Failed to initialize Groq client: {e}")
    client = None

def contextualize_question(question: str, history: List[dict]) -> str:
    if "summarize" in question.lower(): return question
    if not history or not client: return question
    
    messages = [{"role": "system", "content": "Rewrite the user's question to be a specific search query based on the history."}]
    for msg in history[-3:]:
        role = "user" if msg.get("role") == "user" else "assistant"
        messages.append({"role": role, "content": msg.get("content", "")})
    messages.append({"role": "user", "content": f"Rewrite: {question}"})
    
    try:
        resp = client.chat.completions.create(model=settings.LLM_MODEL, messages=messages, temperature=0.3)
        return resp.choices[0].message.content.strip()
    except: return question

def generate_answer(question: str, contexts: list, summary_mode: bool = False) -> dict:
    if not client: return {"answer": "AI Service Unavailable", "refusal": True, "suggestions": []}

    context_text = "\n\n".join(contexts)
    
    # ------------------ UPDATED PROMPT ------------------
    if summary_mode:
        system_content = (
            "You are a helpful research assistant. Generate a concise, factual summary of the provided text in ENGLISH.\n"
            "INSTRUCTIONS:\n"
            "1. Synthesize the main points from the context.\n"
            "2. If the context is fragmented, summarize what IS available.\n"
            "3. Always write the summary in English, even if the source text is in another language.\n"
            "4. After the summary, output '<<<FOLLOWUP>>>' followed by 3 interesting follow-up questions."
        )
    else:
        system_content = (
            "You are an intelligent research assistant. Answer the user's question using ONLY the provided context.\n\n"
            "**CRITICAL RULES:**\n"
            "1. **Language:** ALWAYS answer in English. If the context is in Indonesian, Spanish, or any other language, TRANSLATE the relevant information to English for your answer.\n"
            "2. **Inference Allowed:** If the text explicitly mentions specific items (e.g., 'Only for Pixel'), infer that others are excluded (e.g., 'No Samsung').\n"
            "3. **No Blind Refusals:** Do not just say 'I cannot find this'. State what *is* found in the text.\n"
            "4. **Formatting:** Answer clearly. Then, output '<<<FOLLOWUP>>>' followed by 3 short, relevant follow-up questions."
        )

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": f"Context:\n{context_text}\n\nQuestion: {question}"}
    ]
    
    try:
        resp = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            temperature=0.3
        )
        
        full_text = resp.choices[0].message.content.strip()
        suggestions = []
        answer_text = full_text

        # Parsing Logic
        if "<<<FOLLOWUP>>>" in full_text:
            parts = full_text.split("<<<FOLLOWUP>>>")
            answer_text = parts[0].strip()
            suggestions = [s.strip().lstrip('-•123. ') for s in parts[1].strip().split('\n') if s.strip()]
        
        # Fallback
        if not suggestions:
             lines = full_text.split('\n')
             candidates = [l.strip().lstrip('-•123. ') for l in reversed(lines) if l.strip().endswith('?')]
             suggestions = candidates[:3]
             for s in suggestions: answer_text = answer_text.replace(s, "")

        answer_text = answer_text.replace("<<<FOLLOWUP>>>", "").strip()
        
        # Improved Refusal
        is_refusal = False
        if not context_text or ("i cannot find" in answer_text.lower() and len(answer_text) < 50):
            is_refusal = True

        return {
            "answer": answer_text, 
            "refusal": is_refusal, 
            "suggestions": suggestions[:3] 
        }
        
    except Exception as e:
        logger.error(f"Generation Error: {e}")
        return {"answer": "Error generating answer.", "refusal": True, "suggestions": []}