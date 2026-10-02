# 📡 PublicRSS — AI-Assisted RSS Discovery Engine

> A curated, searchable directory of verified RSS and Atom feeds, categorized and classified using the **Gemma** open-weights intelligence model with a human-in-the-loop review workflow.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Framework-Flask%203.x-lightgrey.svg)](https://flask.palletsprojects.com/)
[![Validation](https://img.shields.io/badge/Validation-Pydantic%20v2-green.svg)](https://docs.pydantic.dev/)
[![Frontend](https://img.shields.io/badge/Frontend-HTMX%20%2B%20Tailwind%20CSS-orange.svg)](https://htmx.org/)
[![Tests](https://img.shields.io/badge/Tests-27%20Passed-brightgreen.svg)](https://pytest.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## 📖 Table of Contents

- [What is PublicRSS?](#-what-is-publicrss)
- [Key Features](#-key-features)
- [How It Works: The Intelligence Contract](#-how-it-works-the-intelligence-contract)
- [Getting Started (Beginner Friendly)](#-getting-started-beginner-friendly)
  - [Prerequisites](#prerequisites)
  - [1. Clone the Repository](#1-clone-the-repository)
  - [2. Create a Virtual Environment](#2-create-a-virtual-environment)
  - [3. Install Dependencies](#3-install-dependencies)
  - [4. Set Up Environment Variables](#4-set-up-environment-variables)
  - [5. Run the Application](#5-run-the-application)
- [Running Automated Tests](#-running-automated-tests)
- [Project Directory Structure](#-project-directory-structure)
- [Troubleshooting & FAQs](#-troubleshooting--faqs)
- [Contributing](#-contributing)
  - [How to Submit Changes](#how-to-submit-changes)
  - [Code Guidelines](#code-guidelines)
- [Reporting Issues](#-reporting-issues)
- [License](#-license)

---

## 🌟 What is PublicRSS?

RSS (Really Simple Syndication) is the open foundation of the decentralized web. However, finding high-quality feeds across blogs, newsletters (Substack), and communities (Reddit) can be difficult because feed metadata is often messy, missing, or unstructured.

**PublicRSS** bridges this gap:
1. Anyone can submit an RSS or Atom feed URL.
2. The engine fetches, validates, and sanitizes the content.
3. The **Gemma AI** model evaluates the feed against a strict **Intelligence Contract** to propose topic categories, audience levels, editorial tone, and collection tags.
4. Human curators inspect the proposal side-by-side with raw feed articles and **Approve**, **Edit & Approve**, or **Reject** it.
5. Approved feeds are published to the public searchable catalog with one-click **"Copy RSS URL"** functionality.

---

## 🚀 Key Features

* **Public Catalog:** Instant search and multi-dimensional filtering across Collections, Topics, Audience Levels (`beginner`, `intermediate`, `advanced`, `expert`), and Editorial Tones (`newsy`, `technical`, `academic`, etc.).
* **1-Click Copy:** Fast clipboard copying for easy import into RSS readers like NetNewsWire, Feedly, Reeder, or NewsBlur.
* **Curated Presets:** Pre-cataloged top feeds from **Substack** (e.g., *The Pragmatic Engineer*, *Astral Codex Ten*, *ByteByteGo*) and **Reddit** (e.g., *r/programming*, *r/MachineLearning*, *r/LocalLLaMA*).
* **Smart URL Normalization:** Automatically fixes user links:
  * Substack URLs (`https://publication.substack.com`) are auto-routed to `/feed`.
  * Reddit community URLs (`https://reddit.com/r/technology`) are auto-routed to RSS endpoints.
* **HTTP 429 Rate-Limit Diagnostics:** Detects publisher rate-limiting (common on cloud IP addresses hitting Reddit) with exact countdown timer feedback and automatic backoff retries.
* **Security & SSRF Mitigation:** Protects against server-side request forgery by blocking private/loopback IP address ranges, imposing a 5MB payload ceiling, and stripping all scripts and HTML.
* **Zero Frontend Build Step:** Built with server-rendered Jinja2 templates, HTMX for real-time live search, Tailwind CSS via CDN, and Vanilla JS. No complex Node/Webpack pipelines required.

---

## 🧠 How It Works: The Intelligence Contract

```
   [User Submits URL]
           │
           ▼
   [1. Secure Ingestion]
   ├── SSRF & Private IP Guard
   ├── 5MB Maximum Size Check
   └── HTML / Script Tag Sanitization
           │
           ▼
   [2. Delimited Prompt Assembly]
   ├── Exactly 7 Sample Articles
   ├── Titles capped at 150 chars, Summaries capped at 300 chars
   ├── URLs strictly stripped to prevent jailbreaks
   └── Isolated in <UNTRUSTED_FEED_DATA> tags
           │
           ▼
   [3. Gemma Inference & 3-Layer Validation]
   ├── Layer 1: JSON Syntax Validation
   ├── Layer 2: Pydantic Schema & Enum Enforcement (extra='forbid')
   └── Layer 3: Semantic Sanity (Topic != Title, 1-3 words, no prompt leaks)
           │
           ├── (Failed?) ──> Automatic Retry with Correction Prompt (Max 2 Attempts)
           │
           ▼
   [4. Human Curator Review Panel]
   ├── Side-by-side Raw Feed Data vs. Gemma Proposal
   └── [Approve] / [Edit & Approve] / [Reject]
           │
           ▼
   [5. Live Public Directory]
```

---

## 🛠️ Getting Started (Beginner Friendly)

Follow these simple steps to run PublicRSS locally on your computer.

### Prerequisites

Make sure you have the following installed on your machine:
* **Python 3.10 or higher** (Check with `python3 --version` or `python --version`)
* **Git** (Check with `git --version`)

---

### 1. Clone the Repository

Open your terminal (macOS/Linux) or Command Prompt / PowerShell (Windows) and run:

```bash
git clone https://github.com/your-username/publicrss.git
cd publicrss
```

---

### 2. Create a Virtual Environment

A virtual environment keeps your project dependencies isolated from the rest of your system:

#### On macOS and Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

#### On Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

*(You will know it's activated when your terminal prompt shows `(venv)` at the beginning).*

---

### 3. Install Dependencies

Install all required Python packages using `pip`:

```bash
pip install -r requirements.txt
```

---

### 4. Set Up Environment Variables

Create a local `.env` configuration file from the provided example:

#### On macOS / Linux:
```bash
cp .env.example .env
```

#### On Windows (Command Prompt):
```cmd
copy .env.example .env
```

Open the `.env` file in your favorite text editor. You will see:

```env
# Google AI Studio API Key for Gemma inference
GEMINI_API_KEY=your_api_key_here

# Gemma model name
GEMMA_MODEL_NAME=gemma-4-26b-a4b-it

# Flask secret key for user sessions
SECRET_KEY=change-this-in-production

# Server port
PORT=3000
```

> **Note:** If you don't have a `GEMINI_API_KEY` yet, you can obtain a free one from [Google AI Studio](https://aistudio.google.com/). PublicRSS also includes a built-in heuristic fallback, so you can still ingest, preview, and curate feeds locally even without an API key!

---

### 5. Run the Application

Start the Flask development server:

```bash
python app.py
```

You should see output similar to:
```
 * Serving Flask app 'app'
 * Debug mode: off
 * Running on http://0.0.0.0:3000
```

Open your browser and navigate to:
👉 **[http://localhost:3000](http://localhost:3000)**

---

## 🧪 Running Automated Tests

PublicRSS includes a full test suite built with **pytest** covering:
- Successful RSS 2.0 and Atom 1.0 feed parsing
- Malformed XML and broken HTML error recovery
- SSRF and private IP blocking
- Pydantic schema validation & enum restrictions
- Prompt injection resistance (e.g. malicious article titles containing `"Ignore all instructions"`)
- Full curator workflow lifecycle (Approve, Edit, Reject)

To run the test suite:

```bash
PYTHONPATH=. pytest tests -v
```

All 27 test cases should pass with 100% green status!

---

## 📂 Project Directory Structure

```
├── app.py                  # Main Flask application entrypoint & factory
├── requirements.txt        # Python dependency manifest
├── .env.example            # Sample environment configuration template
├── README.md               # Beginner-friendly project documentation
│
├── models/                 # Database Layer
│   ├── db.py               # SQLAlchemy initialization
│   └── feed.py             # Feed and AIProposal database models
│
├── feeds/                  # Feed Ingestion Pipeline
│   ├── fetcher.py          # HTTP fetcher, SSRF security & 429 diagnostics
│   ├── parser.py           # RSS 2.0 / Atom feedparser wrapper
│   ├── sanitizer.py        # Text bounds, script/HTML removal, URL stripping
│   └── service.py          # Ingestion coordinator & contract payload builder
│
├── ai/                     # Gemma Intelligence Subsystem
│   ├── schemas.py          # Pydantic contract schema (topics, enums, limits)
│   ├── prompts.py          # Delimited prompt generation & correction prompts
│   ├── validator.py        # 3-Layer validation engine (JSON, Pydantic, Semantic)
│   └── provider.py         # Google AI Studio API client with auto-retry
│
├── views/                  # Flask Route Controllers (MVT Views)
│   ├── directory.py        # Public catalog, search & HTMX partial handlers
│   ├── onboarding.py       # Feed URL submission & Gemma analysis trigger
│   └── review.py           # Curator review queue (Approve / Edit / Reject)
│
├── templates/              # Jinja2 HTML Templates
│   ├── base.html           # Master layout with Tailwind CDN & HTMX
│   ├── directory.html      # Public feeds directory
│   ├── onboarding.html     # Feed submission form & category presets
│   ├── review_list.html    # Curator staging queue table
│   ├── review_detail.html  # Side-by-side feed inspection panel
│   └── partials/           # Reusable HTMX sub-components
│       └── feed_grid.html  # Live search feed card grid
│
├── static/                 # Static Assets
│   └── js/main.js          # Clipboard copy, toast alerts, preset category filtering
│
└── tests/                  # Automated Test Suite
    ├── conftest.py         # Test fixtures & in-memory SQLite DB
    ├── test_feeds.py       # Parsing, SSRF & sanitization tests
    ├── test_ai_validation.py # 3-layer validation & retry tests
    ├── test_prompt_injection.py # Adversarial prompt injection defense tests
    └── test_workflow.py    # End-to-end curator approval lifecycle tests
```

---

## ❓ Troubleshooting & FAQs

### Why does a user-submitted Reddit link return a `429 Too Many Requests` error?
Reddit actively rate-limits unauthenticated requests from cloud hosting IP addresses (like GCP, AWS, and Azure), allowing only **1 request per 30–60 second window**.
- PublicRSS automatically inspects the `x-ratelimit-reset` response header and provides an exact countdown timer.
- PublicRSS automatically attempts a quick retry if the reset window is brief.
- If you hit a 429 on Reddit, simply wait 30–60 seconds for Reddit's rate limit bucket to reset, then submit again.

### Can I run the project without a Gemini API key?
**Yes!** If `GEMINI_API_KEY` is not provided or the quota is exhausted, PublicRSS seamlessly engages its built-in rule-based fallback heuristic. It will stage an initial proposal so you can still use the Curator Review panel to review, edit, and publish feeds.

### Where is data stored?
By default, data is stored in a local SQLite file (`sqlite:///publicrss.db`). You can customize the connection string via `DATABASE_URL` in your `.env` file to use PostgreSQL or MySQL in production.

---

## 🤝 Contributing

Contributions are warmly welcomed! Whether you are fixing a bug, adding new curated feeds, or improving documentation, here is how you can help:

### How to Submit Changes

1. **Fork the repository** on GitHub.
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/publicrss.git
   cd publicrss
   ```
3. **Create a new branch** for your feature or bugfix:
   ```bash
   git checkout -b feature/add-new-curated-feeds
   ```
4. **Make your changes** in your code editor.
5. **Run tests** to make sure everything passes:
   ```bash
   PYTHONPATH=. pytest tests -v
   ```
6. **Commit your changes** with a descriptive commit message:
   ```bash
   git commit -m "Add curated tech podcasts and fix URL parser edge case"
   ```
7. **Push to your fork**:
   ```bash
   git push origin feature/add-new-curated-feeds
   ```
8. **Open a Pull Request (PR)** on GitHub with an explanation of your changes.

### Code Guidelines
- Keep functions modular, readable, and typed with Python type hints.
- Maintain the **Zero Node.js / NPM Build Pipeline** rule (Tailwind and HTMX via CDN).
- Ensure all new features have corresponding tests under `tests/`.

---

## 🐛 Reporting Issues

If you find a bug, have a question, or would like to propose a feature:

1. Check the [Issues tab](https://github.com/your-username/publicrss/issues) to see if the topic has already been discussed.
2. If not, open a **New Issue** with:
   * A clear title describing the problem.
   * Steps to reproduce the issue.
   * The RSS feed URL you submitted (if applicable).
   * Any relevant error messages or screenshots.

---

## 📄 License

This project is open-source and distributed under the **MIT License**. Feel free to use, modify, and distribute it for personal or commercial projects.
