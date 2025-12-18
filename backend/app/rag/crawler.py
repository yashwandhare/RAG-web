import asyncio
from typing import List, Dict, Set
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright, Route
from bs4 import BeautifulSoup
import re
from app.core.config import settings
from app.core.logger import setup_logger

logger = setup_logger(__name__)

class WebCrawler:
    def __init__(self):
        self.visited: Set[str] = set()
        
    async def get_links(self, page, base_url: str) -> List[str]:
        """Extracts valid links from the rendered page."""
        try:
            hrefs = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a[href]'))
                    .map(a => a.href)
            }''')
            
            valid_links = []
            base_domain = urlparse(base_url).netloc
            
            for link in hrefs:
                parsed = urlparse(link)
                if parsed.scheme in ['http', 'https'] and parsed.netloc == base_domain:
                    clean_link = link.split('#')[0].split('?')[0]
                    # Filter file types that crash the crawler
                    if any(clean_link.lower().endswith(ext) for ext in ['.pdf', '.png', '.jpg', '.jpeg', '.zip', '.exe', '.docx']):
                        continue
                    if clean_link not in self.visited:
                        valid_links.append(clean_link)
            
            return list(set(valid_links))
        except Exception as e:
            logger.warning(f"Link extraction failed: {e}")
            return []

    async def crawl(self, url: str, max_pages: int, current_depth: int, max_depth: int) -> List[Dict]:
        if url in self.visited or len(self.visited) >= max_pages:
            return []
        if current_depth > max_depth:
            return []
            
        self.visited.add(url)
        logger.info(f"🕷️ Crawling (Playwright): {url} (Depth: {current_depth})")
        
        pages = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            # FIX 1: Ignore SSL errors for edu/legacy sites
            context = await browser.new_context(
                user_agent=settings.USER_AGENT,
                ignore_https_errors=True
            )
            
            # FIX 2: Block resources to speed up and prevent downloads
            await context.route("**/*", lambda route: route.abort() 
                if route.request.resource_type in ["image", "stylesheet", "font", "media"] 
                else route.continue_())

            page = await context.new_page()
            
            try:
                # FIX 3: Robust Navigation (Commit -> Wait)
                try:
                    # 'commit' returns as soon as server responds headers
                    await page.goto(url, wait_until="commit", timeout=settings.REQUEST_TIMEOUT * 1000)
                    # Then we wait for DOM, but don't crash if it takes too long
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=5000)
                    except:
                        pass # Proceed with whatever HTML we have
                except Exception as e:
                    logger.error(f"❌ Navigation failed for {url}: {e}")
                    return []

                # Dynamic Content (Scroll)
                try:
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1000)
                except: pass
                
                # Extraction
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")
                
                for tag in soup(["script", "style", "nav", "footer", "noscript", "svg", "header", "aside"]):
                    tag.decompose()
                
                title = soup.title.string if soup.title else ""
                body = soup.get_text(" ", strip=True)
                
                if len(body) > 100: # Only keep pages with content
                    full_text = f"Title: {title}\nURL: {url}\n\n{body}"
                    pages.append({"url": url, "text": full_text, "depth": current_depth})
                else:
                    logger.warning(f"⚠️ Page {url} skipped (insufficient content)")
                
                # Recursion
                if current_depth < max_depth:
                    links = await self.get_links(page, url)
                    for link in links[:5]:
                        sub_pages = await self.crawl(link, max_pages, current_depth + 1, max_depth)
                        pages.extend(sub_pages)

            except Exception as e:
                logger.error(f"❌ Crawler error on {url}: {e}")
            finally:
                await browser.close()
                
        return pages

async def crawl_site_async(url: str, max_pages: int = 10, max_depth: int = 2):
    crawler = WebCrawler()
    return await crawler.crawl(url, max_pages, 1, max_depth)