"""FastAPI interactive web dashboard server for Multi-Source Web Scraping Pipeline."""

import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import uvicorn
from fastapi import BackgroundTasks, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from main import run_pipeline

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"
CSV_FILE = OUTPUT_DIR / "final_dataset.csv"
SUMMARY_FILE = OUTPUT_DIR / "summary_report.json"
LOG_FILE = LOGS_DIR / "scraper.log"

app = FastAPI(
    title="Web Scraping & Data Pipeline Dashboard",
    description="Interactive UI & REST API for Multi-Source Scraper Assessment",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

is_scraping_running = False


@app.get("/api/summary")
def get_summary() -> Dict[str, Any]:
    """Return JSON metrics summary."""
    if SUMMARY_FILE.exists():
        try:
            with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            return {"error": str(e)}
    return {"error": "Summary report not found"}


@app.get("/api/records")
def get_records(
    source: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
) -> Dict[str, Any]:
    """Query scraped records with filtering, searching, and pagination."""
    if not CSV_FILE.exists():
        return {"total": 0, "page": page, "page_size": page_size, "records": []}

    try:
        df = pd.read_csv(CSV_FILE)
        # Fill NaN values with None for clean JSON serialization
        df = df.where(pd.notnull(df), None)

        if source and source.strip() and source.lower() != "all":
            df = df[df["source"].str.lower() == source.strip().lower()]

        if search and search.strip():
            q = search.strip().lower()
            mask = (
                df["name_or_title"].astype(str).str.lower().str.contains(q, na=False)
                | df["author"].astype(str).str.lower().str.contains(q, na=False)
                | df["tags"].astype(str).str.lower().str.contains(q, na=False)
            )
            df = df[mask]

        total = len(df)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged_df = df.iloc[start_idx:end_idx]

        records = paged_df.to_dict(orient="records")
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 1,
            "records": records,
        }
    except Exception as exc:
        return {"error": str(exc), "total": 0, "records": []}


@app.get("/api/download-csv")
def download_csv():
    """Download the consolidated dataset CSV."""
    if CSV_FILE.exists():
        return FileResponse(
            path=str(CSV_FILE),
            filename="final_dataset.csv",
            media_type="text/csv",
        )
    return JSONResponse(status_code=404, content={"message": "CSV not found"})


@app.get("/api/logs")
def get_logs() -> Dict[str, Any]:
    """Retrieve the recent lines from scraper.log."""
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            return {"lines": [line.rstrip() for line in lines[-200:]]}
        except Exception as e:
            return {"lines": [f"Error reading log: {e}"]}
    return {"lines": ["Log file not found."]}


def _execute_scraper_task(books_pages: Optional[int], quotes_pages: Optional[int]):
    global is_scraping_running
    try:
        is_scraping_running = True
        run_pipeline(
            books_max_pages=books_pages,
            quotes_max_pages=quotes_pages,
            scrape_details=False,
            delay=0.2,
        )
    finally:
        is_scraping_running = False


@app.post("/api/run-scraper")
def trigger_scraper(
    background_tasks: BackgroundTasks,
    books_pages: Optional[int] = 2,
    quotes_pages: Optional[int] = 2,
):
    """Trigger an asynchronous scraping run."""
    global is_scraping_running
    if is_scraping_running:
        return {"status": "busy", "message": "Scraper is currently running."}

    background_tasks.add_task(_execute_scraper_task, books_pages, quotes_pages)
    return {
        "status": "started",
        "message": f"Scraping started (Books: {books_pages} pages, Quotes: {quotes_pages} pages).",
    }


@app.get("/api/status")
def scraper_status():
    global is_scraping_running
    return {"is_running": is_scraping_running}


@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    """Serve the single-page application dashboard."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Scraping Pipeline Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #090c10;
      --card-bg: rgba(22, 27, 34, 0.7);
      --card-border: rgba(255, 255, 255, 0.08);
      --card-hover: rgba(30, 38, 48, 0.85);
      --text: #f0f6fc;
      --text-muted: #8b949e;
      --accent: #58a6ff;
      --accent-glow: rgba(88, 166, 255, 0.15);
      --success: #3fb950;
      --warning: #d29922;
      --purple: #bc8cff;
      --cyan: #39c5bb;
      --gradient-books: linear-gradient(135deg, #388bfd, #1f6feb);
      --gradient-quotes: linear-gradient(135deg, #2ea043, #238636);
      --font-main: 'Plus Jakarta Sans', sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: var(--font-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
      background-image: 
        radial-gradient(circle at 10% 20%, rgba(56, 139, 253, 0.08) 0%, transparent 40%),
        radial-gradient(circle at 90% 80%, rgba(46, 160, 67, 0.06) 0%, transparent 40%);
    }

    header {
      backdrop-filter: blur(12px);
      background: rgba(9, 12, 16, 0.8);
      border-bottom: 1px solid var(--card-border);
      position: sticky;
      top: 0;
      z-index: 100;
      padding: 1rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 0.8rem;
    }

    .brand-icon {
      width: 40px;
      height: 40px;
      border-radius: 10px;
      background: linear-gradient(135deg, #58a6ff, #bc8cff);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.2rem;
      box-shadow: 0 4px 12px rgba(88, 166, 255, 0.3);
    }

    .brand-title {
      font-size: 1.25rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      background: linear-gradient(90deg, #f0f6fc, #c9d1d9);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .brand-subtitle {
      font-size: 0.75rem;
      color: var(--text-muted);
      font-weight: 500;
    }

    .header-actions {
      display: flex;
      gap: 0.75rem;
      align-items: center;
    }

    .btn {
      padding: 0.55rem 1.1rem;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
      border: 1px solid transparent;
      text-decoration: none;
    }

    .btn-primary {
      background: #238636;
      color: #fff;
    }
    .btn-primary:hover {
      background: #2ea043;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(46, 160, 67, 0.3);
    }

    .btn-outline {
      background: rgba(255, 255, 255, 0.04);
      color: var(--text);
      border-color: var(--card-border);
    }
    .btn-outline:hover {
      background: rgba(255, 255, 255, 0.08);
      border-color: rgba(255, 255, 255, 0.2);
    }

    main {
      flex: 1;
      max-width: 1440px;
      margin: 0 auto;
      padding: 2rem;
      width: 100%;
      display: flex;
      flex-direction: column;
      gap: 2rem;
    }

    /* KPI METRICS GRID */
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1.25rem;
    }

    .kpi-card {
      background: var(--card-bg);
      backdrop-filter: blur(10px);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      transition: all 0.2s;
    }
    .kpi-card:hover {
      border-color: rgba(88, 166, 255, 0.3);
      transform: translateY(-2px);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    }

    .kpi-label {
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      font-weight: 600;
    }

    .kpi-value {
      font-size: 1.8rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: #fff;
    }

    .kpi-badge {
      font-size: 0.75rem;
      padding: 0.2rem 0.5rem;
      border-radius: 6px;
      align-self: flex-start;
      font-weight: 600;
    }

    .badge-success { background: rgba(63, 185, 80, 0.15); color: var(--success); }
    .badge-blue { background: rgba(88, 166, 255, 0.15); color: var(--accent); }
    .badge-purple { background: rgba(188, 140, 255, 0.15); color: var(--purple); }

    /* SOURCE COMPARISON CARDS */
    .sources-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.5rem;
    }

    @media (max-width: 900px) {
      .sources-row { grid-template-columns: 1fr; }
    }

    .source-box {
      background: var(--card-bg);
      backdrop-filter: blur(8px);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
      position: relative;
      overflow: hidden;
    }

    .source-box::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 3px;
    }

    .source-books::before { background: var(--gradient-books); }
    .source-quotes::before { background: var(--gradient-quotes); }

    .source-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .source-title {
      font-size: 1.15rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 0.6rem;
    }

    .source-stat-row {
      display: flex;
      justify-content: space-between;
      font-size: 0.88rem;
      padding: 0.5rem 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    .source-stat-row:last-child { border-bottom: none; }
    .stat-name { color: var(--text-muted); }
    .stat-val { font-weight: 600; font-family: var(--font-mono); }

    /* DATA EXPLORER SECTION */
    .explorer-section {
      background: var(--card-bg);
      backdrop-filter: blur(10px);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }

    .explorer-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 1rem;
    }

    .explorer-title {
      font-size: 1.2rem;
      font-weight: 700;
    }

    .filter-controls {
      display: flex;
      gap: 0.75rem;
      flex-wrap: wrap;
      align-items: center;
    }

    .search-input {
      background: rgba(13, 17, 23, 0.8);
      border: 1px solid var(--card-border);
      color: var(--text);
      padding: 0.55rem 1rem;
      border-radius: 8px;
      font-size: 0.85rem;
      outline: none;
      min-width: 260px;
      font-family: var(--font-main);
      transition: border-color 0.2s;
    }
    .search-input:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px var(--accent-glow);
    }

    .filter-pill {
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      padding: 0.45rem 0.9rem;
      border-radius: 20px;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }
    .filter-pill.active {
      background: var(--accent);
      color: #090c10;
      border-color: var(--accent);
    }

    /* TABLE */
    .table-container {
      overflow-x: auto;
      border: 1px solid var(--card-border);
      border-radius: 10px;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 0.85rem;
    }

    th {
      background: rgba(13, 17, 23, 0.9);
      padding: 0.85rem 1rem;
      font-weight: 600;
      color: var(--text-muted);
      border-bottom: 1px solid var(--card-border);
      white-space: nowrap;
    }

    td {
      padding: 0.85rem 1rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      color: #c9d1d9;
    }

    tr:hover td {
      background: rgba(255, 255, 255, 0.02);
    }

    .tag-badge {
      display: inline-block;
      background: rgba(136, 153, 166, 0.15);
      color: #8b949e;
      padding: 0.15rem 0.4rem;
      border-radius: 4px;
      font-size: 0.72rem;
      margin-right: 0.3rem;
      margin-bottom: 0.2rem;
    }

    .badge-src-books {
      background: rgba(56, 139, 253, 0.15);
      color: #58a6ff;
      border: 1px solid rgba(56, 139, 253, 0.3);
      padding: 0.2rem 0.6rem;
      border-radius: 6px;
      font-weight: 600;
      font-size: 0.75rem;
    }

    .badge-src-quotes {
      background: rgba(46, 160, 67, 0.15);
      color: #3fb950;
      border: 1px solid rgba(46, 160, 67, 0.3);
      padding: 0.2rem 0.6rem;
      border-radius: 6px;
      font-weight: 600;
      font-size: 0.75rem;
    }

    .stars {
      color: #e3b341;
      letter-spacing: 2px;
    }

    /* PAGINATION */
    .pagination-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.85rem;
      color: var(--text-muted);
    }

    .page-buttons {
      display: flex;
      gap: 0.5rem;
    }

    /* LOG MODAL / DRAWER */
    .terminal-box {
      background: #0d1117;
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 1rem;
      font-family: var(--font-mono);
      font-size: 0.75rem;
      color: #7ee787;
      max-height: 250px;
      overflow-y: auto;
      line-height: 1.5;
    }

    footer {
      border-top: 1px solid var(--card-border);
      padding: 1.5rem 2rem;
      text-align: center;
      font-size: 0.8rem;
      color: var(--text-muted);
    }
  </style>
</head>
<body>

  <header>
    <div class="brand">
      <div class="brand-icon">⚡</div>
      <div>
        <div class="brand-title">Antigravity Scraper Dashboard</div>
        <div class="brand-subtitle">Multi-Source Web Scraping & Consolidation Pipeline</div>
      </div>
    </div>
    <div class="header-actions">
      <button class="btn btn-primary" id="btnRunScraper" onclick="triggerRun()">
        ▶ Run Scraper
      </button>
      <a href="/api/download-csv" class="btn btn-outline" download>
        ⬇ Download CSV
      </a>
      <a href="/docs" target="_blank" class="btn btn-outline">
        📘 OpenAPI Docs
      </a>
    </div>
  </header>

  <main>
    <!-- TOP KPI STATS -->
    <section class="kpi-grid">
      <div class="kpi-card">
        <span class="kpi-label">Final Consolidated Records</span>
        <span class="kpi-value" id="valFinalCount">1,100</span>
        <span class="kpi-badge badge-success">✓ 100% Quality Pass</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">Total Execution Time</span>
        <span class="kpi-value" id="valExecTime">64.57s</span>
        <span class="kpi-badge badge-blue">Dynamic Pagination</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">Duplicates Removed</span>
        <span class="kpi-value" id="valDupes">0</span>
        <span class="kpi-badge badge-purple">Composite Fingerprints</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">Integrity Rejections</span>
        <span class="kpi-value" id="valRejected">0</span>
        <span class="kpi-badge badge-success">Strict Validation</span>
      </div>
    </section>

    <!-- SOURCE BREAKDOWN -->
    <section class="sources-row">
      <div class="source-box source-books">
        <div class="source-header">
          <div class="source-title">
            <span>📚</span> Books to Scrape
          </div>
          <span class="badge-src-books">50 Pages Traversed</span>
        </div>
        <div>
          <div class="source-stat-row">
            <span class="stat-name">Target URL</span>
            <span class="stat-val"><a href="https://books.toscrape.com/" target="_blank" style="color: #58a6ff; text-decoration: none;">books.toscrape.com</a></span>
          </div>
          <div class="source-stat-row">
            <span class="stat-name">Records Harvested</span>
            <span class="stat-val" id="booksCollected">1,000</span>
          </div>
          <div class="source-stat-row">
            <span class="stat-name">Cleaning & Validation Rate</span>
            <span class="stat-val">100% (1,000 / 1,000)</span>
          </div>
          <div class="source-stat-row">
            <span class="stat-name">Relative URL Resolution</span>
            <span class="stat-val">urllib.parse.urljoin</span>
          </div>
        </div>
      </div>

      <div class="source-box source-quotes">
        <div class="source-header">
          <div class="source-title">
            <span>💬</span> Quotes to Scrape
          </div>
          <span class="badge-src-quotes">10 Pages Traversed</span>
        </div>
        <div>
          <div class="source-stat-row">
            <span class="stat-name">Target URL</span>
            <span class="stat-val"><a href="https://quotes.toscrape.com/" target="_blank" style="color: #3fb950; text-decoration: none;">quotes.toscrape.com</a></span>
          </div>
          <div class="source-stat-row">
            <span class="stat-name">Records Harvested</span>
            <span class="stat-val" id="quotesCollected">100</span>
          </div>
          <div class="source-stat-row">
            <span class="stat-name">Author & Tag Extraction</span>
            <span class="stat-val">Cleaned & Normalised</span>
          </div>
          <div class="source-stat-row">
            <span class="stat-name">Pagination Stop Condition</span>
            <span class="stat-val">li.next absent</span>
          </div>
        </div>
      </div>
    </section>

    <!-- DATA EXPLORER -->
    <section class="explorer-section">
      <div class="explorer-header">
        <div class="explorer-title">Ingested Records Explorer</div>
        <div class="filter-controls">
          <input 
            type="text" 
            id="searchInput" 
            class="search-input" 
            placeholder="Search by title, author, or tag..."
            oninput="handleSearch()"
          />
          <button class="filter-pill active" onclick="setSource('all', this)">All (1,100)</button>
          <button class="filter-pill" onclick="setSource('Books to Scrape', this)">Books (1,000)</button>
          <button class="filter-pill" onclick="setSource('Quotes to Scrape', this)">Quotes (100)</button>
        </div>
      </div>

      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Source</th>
              <th>Name / Title / Quote</th>
              <th>Price</th>
              <th>Rating</th>
              <th>Author</th>
              <th>Tags</th>
              <th>Link</th>
            </tr>
          </thead>
          <tbody id="tableBody">
            <tr><td colspan="7" style="text-align:center; padding: 2rem;">Loading data records...</td></tr>
          </tbody>
        </table>
      </div>

      <div class="pagination-bar">
        <div id="pageInfo">Showing 1 to 25 of 1,100 records</div>
        <div class="page-buttons">
          <button class="btn btn-outline" id="btnPrev" onclick="changePage(-1)">← Prev</button>
          <button class="btn btn-outline" id="btnNext" onclick="changePage(1)">Next →</button>
        </div>
      </div>
    </section>

    <!-- LOG VIEWER SECTION -->
    <section class="explorer-section">
      <div class="explorer-header">
        <div class="explorer-title">Live Pipeline Activity Log (`scraper.log`)</div>
        <button class="btn btn-outline" onclick="loadLogs()">🔄 Refresh Logs</button>
      </div>
      <div class="terminal-box" id="logBox">
        Connecting to scraper logs...
      </div>
    </section>
  </main>

  <footer>
    Multi-Source Web Scraping & Data Consolidation Pipeline &bull; Python 3.11+ &bull; Requests & BeautifulSoup4 &bull; Built for Technical Assessment
  </footer>

  <script>
    let currentSource = 'all';
    let currentSearch = '';
    let currentPage = 1;
    let pageSize = 20;

    async function fetchSummary() {
      try {
        const res = await fetch('/api/summary');
        const data = await res.json();
        if (data.final_record_count !== undefined) {
          document.getElementById('valFinalCount').textContent = data.final_record_count.toLocaleString();
          document.getElementById('valExecTime').textContent = data.execution_time_seconds + 's';
          document.getElementById('valDupes').textContent = data.total_duplicates;
          document.getElementById('valRejected').textContent = data.total_records_rejected;
          if (data.sources) {
            if (data.sources["Books to Scrape"]) {
              document.getElementById('booksCollected').textContent = data.sources["Books to Scrape"].records_collected.toLocaleString();
            }
            if (data.sources["Quotes to Scrape"]) {
              document.getElementById('quotesCollected').textContent = data.sources["Quotes to Scrape"].records_collected.toLocaleString();
            }
          }
        }
      } catch (err) {
        console.error('Error fetching summary:', err);
      }
    }

    async function fetchRecords() {
      try {
        let url = `/api/records?page=${currentPage}&page_size=${pageSize}`;
        if (currentSource !== 'all') url += `&source=${encodeURIComponent(currentSource)}`;
        if (currentSearch) url += `&search=${encodeURIComponent(currentSearch)}`;

        const res = await fetch(url);
        const data = await res.json();

        const tbody = document.getElementById('tableBody');
        tbody.innerHTML = '';

        if (!data.records || data.records.length === 0) {
          tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 2rem; color: var(--text-muted);">No records found matching filters.</td></tr>`;
          document.getElementById('pageInfo').textContent = 'Showing 0 records';
          return;
        }

        data.records.forEach(r => {
          const tr = document.createElement('tr');
          const isBook = r.source === 'Books to Scrape';
          const srcBadge = isBook 
            ? '<span class="badge-src-books">Books</span>' 
            : '<span class="badge-src-quotes">Quotes</span>';

          let ratingHtml = '-';
          if (r.rating) {
            ratingHtml = `<span class="stars">${'★'.repeat(r.rating)}${'☆'.repeat(5 - r.rating)}</span>`;
          }

          let tagsHtml = '-';
          if (r.tags) {
            tagsHtml = r.tags.split(',').map(t => `<span class="tag-badge">${t.trim()}</span>`).join('');
          }

          const priceHtml = r.price !== null && r.price !== undefined ? `<strong>£${Number(r.price).toFixed(2)}</strong>` : '-';
          const titleTruncated = r.name_or_title && r.name_or_title.length > 80 ? r.name_or_title.slice(0, 80) + '...' : r.name_or_title;

          tr.innerHTML = `
            <td>${srcBadge}</td>
            <td style="max-width: 400px; font-weight: 500;">${titleTruncated}</td>
            <td>${priceHtml}</td>
            <td>${ratingHtml}</td>
            <td style="color: var(--accent);">${r.author || '-'}</td>
            <td style="max-width: 250px;">${tagsHtml}</td>
            <td><a href="${r.source_url}" target="_blank" style="color: #58a6ff; text-decoration: none;">Visit ↗</a></td>
          `;
          tbody.appendChild(tr);
        });

        const startIdx = (currentPage - 1) * pageSize + 1;
        const endIdx = Math.min(startIdx + data.records.length - 1, data.total);
        document.getElementById('pageInfo').textContent = `Showing ${startIdx} to ${endIdx} of ${data.total.toLocaleString()} records`;

        document.getElementById('btnPrev').disabled = currentPage <= 1;
        document.getElementById('btnNext').disabled = currentPage >= data.total_pages;

      } catch (err) {
        console.error('Error fetching records:', err);
      }
    }

    async function loadLogs() {
      try {
        const res = await fetch('/api/logs');
        const data = await res.json();
        const box = document.getElementById('logBox');
        if (data.lines && data.lines.length > 0) {
          box.innerHTML = data.lines.map(l => `<div>${l}</div>`).join('');
          box.scrollTop = box.scrollHeight;
        } else {
          box.textContent = "No log lines available.";
        }
      } catch (err) {
        console.error('Error loading logs:', err);
      }
    }

    function setSource(source, btn) {
      currentSource = source;
      currentPage = 1;
      document.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      fetchRecords();
    }

    let searchTimer = null;
    function handleSearch() {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        currentSearch = document.getElementById('searchInput').value;
        currentPage = 1;
        fetchRecords();
      }, 300);
    }

    function changePage(delta) {
      currentPage += delta;
      if (currentPage < 1) currentPage = 1;
      fetchRecords();
    }

    async function triggerRun() {
      const btn = document.getElementById('btnRunScraper');
      btn.disabled = true;
      btn.textContent = '⏳ Scraping in progress...';
      try {
        const res = await fetch('/api/run-scraper?books_pages=2&quotes_pages=2', { method: 'POST' });
        const data = await res.json();
        alert(data.message);
        // Poll status
        const poll = setInterval(async () => {
          const sRes = await fetch('/api/status');
          const sData = await sRes.json();
          loadLogs();
          if (!sData.is_running) {
            clearInterval(poll);
            btn.disabled = false;
            btn.textContent = '▶ Run Scraper';
            fetchSummary();
            fetchRecords();
          }
        }, 2000);
      } catch (err) {
        btn.disabled = false;
        btn.textContent = '▶ Run Scraper';
        alert('Failed to trigger scraper.');
      }
    }

    // Initial load
    fetchSummary();
    fetchRecords();
    loadLogs();
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("STARTING SCRAPER DASHBOARD ON LOCALHOST")
    print("URL: http://127.0.0.1:8000 (or http://localhost:8000)")
    print("=" * 60 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
