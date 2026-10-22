"""Busca com Chrome real (headless, perfil persistente) servida em 127.0.0.1:8890/search?q=.
Google primeiro, Bing se o Google pedir captcha (disjuntor 10 min). Pool de páginas e cache."""
import asyncio, json, os, re, time, urllib.parse
from aiohttp import web
from playwright.async_api import async_playwright

PROFILE = os.path.expanduser("~/.cache/placar/chrome-profile")
CACHE_P = os.path.expanduser("~/.cache/placar/chrome_search.json")
POOL, TIMEOUT = int(os.environ.get("CS_POOL", "3")), 8000
cache = json.load(open(CACHE_P)) if os.path.exists(CACHE_P) else {}
state = {"google_off": 0.0}

async def parse_google(p):
    return await p.eval_on_selector_all("div#search a:has(h3)", """els=>els.map(a=>({url:a.href,titulo:a.querySelector('h3').textContent,
      trecho:(a.closest('div.g, div[data-hveid]')||a).textContent.slice(0,400)}))""")

async def parse_bing(p):
    return await p.eval_on_selector_all("li.b_algo", """els=>els.map(e=>{const a=e.querySelector('h2 a');return a?{url:a.href,titulo:a.textContent,
      trecho:(e.querySelector('p')||e).textContent.slice(0,400)}:null}).filter(x=>x)""")

async def run(q):
    page = await pool.get()
    try:
        if time.time() > state["google_off"]:
            await page.goto("https://www.google.com/search?hl=pt-BR&num=10&q=" + urllib.parse.quote(q), timeout=TIMEOUT)
            if "/sorry/" in page.url or await page.query_selector("form#captcha-form"):
                state["google_off"] = time.time() + 600; print("google captcha", flush=True)
            else:
                r = await parse_google(page)
                if r: return r, "google"
        await page.goto("https://www.bing.com/search?setlang=pt-br&cc=BR&mkt=pt-BR&q=" + urllib.parse.quote(q), timeout=TIMEOUT)
        return await parse_bing(page), "bing"
    finally:
        pool.put_nowait(page)

async def search(req):
    q = req.query.get("q", "").strip()
    if q in cache: return web.json_response({"results": cache[q], "engine": "cache"})
    try:
        r, eng = await asyncio.wait_for(run(q), 12)
    except Exception as e:
        return web.json_response({"results": [], "error": str(e)[:100]})
    for x in r:
        m = re.search(r"[?&]u=a1([^&]+)", x["url"])
        if "bing.com/ck/" in x["url"] and m:
            import base64
            b = m.group(1); x["url"] = base64.urlsafe_b64decode(b + "=" * (-len(b) % 4)).decode("utf-8", "ignore")
        x["titulo"] = " ".join(x["titulo"].split()); x["trecho"] = " ".join(x["trecho"].split())
    r = [x for x in r if x["url"].startswith("http") and "google." not in x["url"]][:8]
    if r:
        cache[q] = r; json.dump(cache, open(CACHE_P, "w"), ensure_ascii=False)
    return web.json_response({"results": r, "engine": eng})

async def main():
    global pool
    pw = await async_playwright().start()
    ctx = await pw.chromium.launch_persistent_context(PROFILE, executable_path="/usr/bin/google-chrome",
        headless=True, locale="pt-BR", args=["--disable-blink-features=AutomationControlled"])
    pool = asyncio.Queue()
    for _ in range(POOL):
        pg = await ctx.new_page()
        await pg.route(re.compile(r".*\.(png|jpg|jpeg|gif|webp|woff2?|svg|mp4)(\?.*)?$"), lambda r: r.abort())
        pool.put_nowait(pg)
    app = web.Application(); app.router.add_get("/search", search)
    rn = web.AppRunner(app); await rn.setup(); await web.TCPSite(rn, "127.0.0.1", 8890).start()
    print("chrome_search up", flush=True)
    await asyncio.Event().wait()

asyncio.run(main())
