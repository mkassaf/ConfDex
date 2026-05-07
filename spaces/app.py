from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Install Playwright Chromium binaries at startup (system packages installed via packages.txt)
subprocess.run(
    [sys.executable, "-m", "playwright", "install", "chromium"],
    check=False,
    capture_output=True,
)

import gradio as gr
import pandas as pd

from confscraper.categorize import categorize_paper
from confscraper.llm import DEFAULT_MODEL
from confscraper.output import write_csv_papers, write_csv_summaries, write_json, write_summaries
from confscraper.pipeline import scrape, scrape_conference


def _run_scrape(
    urls_text: str,
    slug: str,
    do_summarize: bool,
    topic: str,
    model: str,
    api_key: str,
) -> tuple[pd.DataFrame, str, str, str]:
    urls = [u.strip() for u in (urls_text or "").splitlines() if u.strip()]
    slug = (slug or "").strip()

    if not urls and not slug:
        raise gr.Error("Enter at least one URL or a conference slug.")

    resolved_model = model.strip() or os.environ.get("LLM_MODEL", DEFAULT_MODEL)
    resolved_key = api_key.strip() or None

    try:
        if slug:
            result = asyncio.run(scrape_conference(slug, concurrency=3, rate=3.0))
        else:
            result = asyncio.run(scrape(urls, concurrency=3, rate=3.0))
    except Exception as e:
        raise gr.Error(f"Scrape failed: {e}") from e

    if result.paper_count == 0:
        raise gr.Error("No papers found. Check the URL and try again.")

    csv_tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    csv_tmp.close()
    json_tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    json_tmp.close()

    if do_summarize:
        summaries: list[dict] = []
        for paper in result.papers:
            s = categorize_paper(paper, resolved_model, resolved_key, topic.strip() or None)
            summaries.append(s)
        df = pd.DataFrame(summaries)
        write_csv_summaries(summaries, Path(csv_tmp.name))
        write_summaries(summaries, Path(json_tmp.name))
        status = f"Summarized {result.paper_count} papers using {resolved_model}."
    else:
        rows = []
        for p in result.papers:
            d = p.model_dump()
            d["tags"] = "; ".join(d.get("tags") or [])
            rows.append(d)
        df = pd.DataFrame(rows)
        write_csv_papers(result, Path(csv_tmp.name))
        write_json(result, Path(json_tmp.name))
        status = f"Scraped {result.paper_count} papers."

    return df, csv_tmp.name, json_tmp.name, status


with gr.Blocks(title="conf-scraper") as demo:
    gr.Markdown(
        "# conf-scraper\n"
        "Scrape paper titles and abstracts from [conf.researchr.org](https://conf.researchr.org) conferences.\n\n"
        "Paste one or more track/home/program URLs **or** enter a conference slug to auto-discover all tracks."
    )

    with gr.Row():
        with gr.Column(scale=2):
            urls_input = gr.Textbox(
                label="Conference URLs (one per line)",
                placeholder="https://conf.researchr.org/track/icse-2026/icse-2026-research-track",
                lines=4,
            )
        with gr.Column(scale=1):
            slug_input = gr.Textbox(
                label="— OR — Conference slug (auto-discovers all tracks)",
                placeholder="icse-2026",
                lines=2,
            )

    with gr.Row():
        do_summarize = gr.Checkbox(label="Summarize abstracts with LLM")
        topic_input = gr.Textbox(
            label="Topic for relevance scoring (optional, only with summarize)",
            placeholder="Green agentic AI",
        )

    with gr.Accordion("LLM settings (only needed for summarize)", open=False):
        model_input = gr.Textbox(
            label="Model",
            placeholder=f"Default: {DEFAULT_MODEL}  |  Examples: gpt-4o, ollama/llama3.2, deepseek/deepseek-chat",
            value="",
        )
        api_key_input = gr.Textbox(
            label="API key (or set ANTHROPIC_API_KEY / OPENAI_API_KEY as a Space secret)",
            type="password",
        )

    scrape_btn = gr.Button("Scrape", variant="primary", size="lg")
    status_box = gr.Textbox(label="Status", interactive=False)
    df_output = gr.Dataframe(label="Results preview", wrap=True)

    with gr.Row():
        csv_file = gr.File(label="Download CSV")
        json_file = gr.File(label="Download JSON")

    scrape_btn.click(
        fn=_run_scrape,
        inputs=[urls_input, slug_input, do_summarize, topic_input, model_input, api_key_input],
        outputs=[df_output, csv_file, json_file, status_box],
    )

if __name__ == "__main__":
    demo.launch()
