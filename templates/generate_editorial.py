#!/usr/bin/env python3
"""Generate preview images for editorial design style only."""

import asyncio
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright


async def render_template(template_path: str, data: dict, output_path: str):
    """Render a Jinja2 template to HTML and screenshot to PNG."""
    env = Environment(loader=FileSystemLoader(Path(template_path).parent))
    template = env.get_template(Path(template_path).name)
    html = template.render(**data)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 900, "height": 1200})
        await page.set_content(html)
        await page.wait_for_timeout(2000)
        await page.screenshot(path=output_path, full_page=False)
        await browser.close()
    print(f"Generated: {output_path}")


async def main():
    # Load demo data
    with open("demo_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    pages = ["cover", "content", "summary"]

    output_dir = Path("previews")
    output_dir.mkdir(exist_ok=True)

    tasks = []
    for page in pages:
        template_path = f"editorial/{page}.html"
        output_path = output_dir / f"editorial_{page}.png"
        tasks.append(render_template(template_path, data, str(output_path)))

    await asyncio.gather(*tasks)
    print("All editorial previews generated!")


if __name__ == "__main__":
    asyncio.run(main())
