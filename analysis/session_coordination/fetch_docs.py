"""Fetch a bounded official evidence set for Codex session isolation."""
import asyncio
import datetime
import json
from pathlib import Path

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig


OUT = Path(__file__).resolve().parent / "reports"
QUERY = "Codex sessions worktrees hooks cwd"
PAGES = [
    ("official_search", "https://developers.openai.com/search?q=Codex%20sessions%20worktrees%20hooks%20cwd"),
    ("app_worktrees", "https://developers.openai.com/codex/app/worktrees/"),
    ("hooks", "https://developers.openai.com/codex/hooks/"),
    ("cli_reference", "https://developers.openai.com/codex/cli/reference/"),
    ("git_worktree", "https://git-scm.com/docs/git-worktree"),
]
TERMS = ("worktree", "sessionstart", "pretooluse", "cwd", "sandbox", "--cd", "--worktree", "additionalcontext", "permissiondecision", "hook", "resume")


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {
        "query": QUERY,
        "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "version_note": "Live documentation, not pinned to a Codex release or locally tested App version.",
        "limits": [
            "No web-search MCP is available. The first request attempts an official-site search URL; a failed search is not evidence of search results.",
            "developers.openai.com may redirect to a different official domain; final_url records that change rather than attributing redirected text to the original domain.",
            "These are documentation observations, not tests of the installed host's hook coverage or permission enforcement.",
            "The initial sandboxed Chromium startup failed with Operation not permitted. Fetching succeeded only after real host escalation.",
        ],
        "sources": [],
    }
    config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, page_timeout=45000)
    async with AsyncWebCrawler(config=BrowserConfig(headless=True, extra_args=["--no-sandbox"])) as crawler:
        for name, url in PAGES:
            entry = {"name": name, "url": url}
            try:
                result = await crawler.arun(url=url, config=config)
                markdown = result.markdown.raw_markdown if hasattr(result.markdown, "raw_markdown") else str(result.markdown or "")
                entry.update(success=result.success, status_code=result.status_code, error=result.error_message, final_url=getattr(result, "redirected_url", None) or url)
                lines = markdown.splitlines()
                start = 0 if name == "git_worktree" else next((i for i, line in enumerate(lines) if line.startswith("# ")), 0)
                lines = lines[start:]
                selected = set()
                for i, line in enumerate(lines):
                    if any(term in line.lower() for term in TERMS):
                        selected.update(range(max(0, i-2), min(len(lines), i+5)))
                entry["excerpts"] = "\n".join(f"{i+1}: {lines[i]}" for i in sorted(selected))[:80000]
                if result.success:
                    (OUT / (name + ".md")).write_text("\n".join(lines), encoding="utf-8")
            except Exception as error:
                entry.update(success=False, error=str(error))
            report["sources"].append(entry)
            (OUT / "sources.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(name, entry.get("success"), entry.get("status_code"), entry.get("error", ""), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
