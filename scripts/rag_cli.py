#!/usr/bin/env python3
"""
RAGex CLI - Stable Connection Edition
- Fixes 'Server disconnected' errors by disabling keep-alive
- Auto-starts backend
- TrueColor ASCII Art
"""
import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import aiohttp

# --- CONFIGURATION ---
API_BASE = os.getenv("RAG_API_BASE", "http://127.0.0.1:8000/api/v1")
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
VENV_PY = BACKEND_DIR / ".venv" / "bin" / "python"
SERVER_CMD = [
    str(VENV_PY), "-m", "uvicorn", "app.main:app", 
    "--host", "127.0.0.1", "--port", "8000", "--log-level", "warning"
]

# --- STYLING ---
RAGEX_PINK = "\033[38;2;251;134;213m"

C = {
    "pink": RAGEX_PINK,
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "cyan": "\033[96m",
    "gray": "\033[90m",
    "bold": "\033[1m",
    "reset": "\033[0m",
}

def splash():
    art = f"""{C['pink']}
██████╗  █████╗  ██████╗ ███████╗██╗  ██╗
██╔══██╗██╔══██╗██╔════╝ ██╔════╝╚██╗██╔╝
██████╔╝███████║██║  ███╗█████╗   ╚███╔╝ 
██╔══██╗██╔══██║██║   ██║██╔══╝   ██╔██╗ 
██║  ██║██║  ██║╚██████╔╝███████╗██╔╝ ██╗
╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝{C['reset']}
    """
    print(art)
    print(f"{C['gray']}RAGex Companion CLI • v2.2 (Stable){C['reset']}\n")

# --- UTILS ---

async def _server_check() -> bool:
    try:
        # Use a fresh session for the check to avoid pooling issues
        async with aiohttp.ClientSession() as s:
            r = await s.get(API_BASE.replace("/api/v1", "/"), timeout=2)
            return r.status == 200
    except:
        return False

async def ensure_backend():
    """Checks if backend is running; if not, starts it."""
    if await _server_check():
        return

    print(f"{C['blue']}➜ Starting backend server...{C['reset']}", end="", flush=True)
    
    if not VENV_PY.exists():
        print(f"\n{C['yellow']}Error: Virtual environment not found at {VENV_PY}{C['reset']}")
        sys.exit(1)

    await asyncio.create_subprocess_exec(
        *SERVER_CMD, cwd=str(BACKEND_DIR), 
        stdout=asyncio.subprocess.DEVNULL, 
        stderr=asyncio.subprocess.DEVNULL
    )

    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    for i in range(600): # 60s timeout
        if await _server_check():
            print(f"\r{C['green']}➜ Backend Ready           {C['reset']}")
            return
        sys.stdout.write(f"\r{C['blue']}➜ Starting backend server {frames[i % len(frames)]}{C['reset']}")
        sys.stdout.flush()
        await asyncio.sleep(0.1)
    
    print(f"\n\n{C['yellow']}Server timed out.{C['reset']}")
    sys.exit(1)

# --- CORE ACTIONS ---

async def index_flow(session: aiohttp.ClientSession, url: str):
    print(f"\n{C['cyan']}Indexing:{C['reset']} {url}")
    
    try:
        async with session.post(f"{API_BASE}/index", json={"url": url, "max_pages": 3}) as r:
            r.raise_for_status()

        start = time.time()
        frames = ["|", "/", "-", "\\"]
        i = 0
        
        while True:
            if time.time() - start > 120:
                print(f"\n{C['yellow']}Analysis timed out.{C['reset']}")
                return None

            sys.stdout.write(f"\r{C['gray']}Analyzing content {frames[i%4]}{C['reset']}")
            sys.stdout.flush()
            
            try:
                async with session.post(f"{API_BASE}/analyze", json={"url": url}) as r:
                    if r.status == 200:
                        data = await r.json()
                        if data.get("type") != "Empty":
                            sys.stdout.write("\r" + " "*30 + "\r")
                            return data
            except:
                pass 
            
            i += 1
            await asyncio.sleep(0.5)

    except Exception as e:
        print(f"\n{C['yellow']}Error: {e}{C['reset']}")
        return None

async def main():
    if os.name == 'nt': os.system('cls')
    else: os.system('clear')
    
    splash()
    await ensure_backend()

    # FIX: force_close=True prevents "Server disconnected" on idle
    connector = aiohttp.TCPConnector(force_close=True)
    async with aiohttp.ClientSession(connector=connector) as session:
        
        # 1. URL Input
        while True:
            try:
                url = input(f"\n{C['bold']}Target URL > {C['reset']}").strip()
                if url: break
            except KeyboardInterrupt:
                return

        # 2. Indexing
        analysis = await index_flow(session, url)
        if not analysis:
            print("Failed to analyze.")
            return

        # 3. Show Summary
        summary = analysis.get("summary", "No summary.")
        topics = ", ".join(analysis.get("topics", [])[:6])
        
        print(f"{C['gray']}─"*40 + f"{C['reset']}")
        print(f"{C['bold']}SUMMARY:{C['reset']} {summary}")
        print(f"{C['bold']}TOPICS:{C['reset']}  {topics}")
        print(f"{C['gray']}─"*40 + f"{C['reset']}")

        # 4. Chat Loop
        print(f"\n{C['green']}Ready. (Ctrl+C to quit){C['reset']}")
        
        while True:
            try:
                q = input(f"\n{C['pink']}QUERY ➜ {C['reset']}").strip()
                if not q: continue
            except KeyboardInterrupt:
                print(f"\n{C['gray']}Exiting.{C['reset']}")
                break

            start_t = time.time()
            try:
                payload = {"question": q, "history": [], "include_sources": True}
                async with session.post(f"{API_BASE}/query", json=payload) as resp:
                    res = await resp.json()
                
                elapsed = time.time() - start_t
                
                # Render Answer
                ans = res.get("answer", "")
                conf = res.get("confidence") or res.get("confidence_score")
                srcs = res.get("sources", [])

                print(f"\n{ans}\n")
                
                # Footer Info
                meta = f"{C['gray']}Confidence: {conf} • Time: {elapsed:.2f}s{C['reset']}"
                print(meta)
                
                if srcs:
                    print(f"{C['blue']}Sources:{C['reset']}")
                    for s in srcs[:3]:
                        print(f"  • {s}")
            
            except Exception as e:
                print(f"{C['yellow']}Error: {e}{C['reset']}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)