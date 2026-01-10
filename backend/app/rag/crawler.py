import asyncio
from typing import List, Dict, Set
from urllib.parse import urlparse
from playwright.async_api import async_playwright, BrowserContext, Page
from bs4 import BeautifulSoup
from app.core.config import settings
from app.core.logger import setup_logger

logger = setup_logger(__name__)

class WebCrawler:
    def __init__(self):
        self.visited: Set[str] = set()
        
    async def get_links(self, page: Page, base_url: str) -> List[str]:
        """Extracts valid links from the rendered page."""
        try:
            # Execute JS to get links quickly
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

    async def _process_page(self, context: BrowserContext, url: str, current_depth: int) -> Dict:
        """Internal helper to process a single page."""
        page = await context.new_page()
        try:
            # FIX: Robust Navigation
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=settings.REQUEST_TIMEOUT * 1000)
            except Exception as e:
                logger.warning(f"Timeout/Nav error on {url}: {e}")
                # Don't return empty yet, try to scrape what loaded
            
            # Extraction
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            for tag in soup(["script", "style", "nav", "footer", "noscript", "svg", "header", "aside"]):
                tag.decompose()
            
            title = soup.title.string if soup.title else ""
            body = soup.get_text(" ", strip=True)
            
            # Get links only if we are going deeper
            links = []
            if current_depth < 2:  # Assuming max_depth logic handled by caller
                links = await self.get_links(page, url)
                
            return {
                "url": url,
                "text": f"Title: {title}\nURL: {url}\n\n{body}",
                "depth": current_depth,
                "links": links
            }
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            return None
        finally:
            await page.close()

    async def crawl(self, url: str, max_pages: int = 10, max_depth: int = 2) -> List[Dict]:
        logger.info(f"🕷️ Starting crawl: {url}")
        pages = []
        queue = [(url, 1)]  # Tuple: (url, depth)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=settings.USER_AGENT,
                ignore_https_errors=True
            )
            # Block heavy resources
            await context.route("**/*", lambda route: route.abort() 
                if route.request.resource_type in ["image", "stylesheet", "font", "media"] 
                else route.continue_())

            while queue and len(self.visited) < max_pages:
                current_url, depth = queue.pop(0)
                
                if current_url in self.visited or depth > max_depth:
                    continue
                
                self.visited.add(current_url)
                logger.info(f"   Processing: {current_url} (Depth: {depth})")
                
                data = await self._process_page(context, current_url, depth)
                
                if data and len(data["text"]) > 100:
                    pages.append(data)
                    
                    # Add new links to queue
                    if depth < max_depth:
                        for link in data["links"]:
                            if link not in self.visited:
                                queue.append((link, depth + 1))
            
            await browser.close()
            
        return pages

async def crawl_site_async(url: str, max_pages: int = 10, max_depth: int = 2):
    crawler = WebCrawler()
    return await crawler.crawl(url, max_pages, max_depth)