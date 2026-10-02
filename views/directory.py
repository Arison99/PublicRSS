"""
Public Feeds Directory View.
Searchable, filterable catalog of authoritative approved feeds with
one-click 'Copy RSS URL' and HTMX-powered partial updates.
"""
from datetime import datetime, timezone
from flask import render_template, request, jsonify, flash, redirect, url_for
from . import directory_bp
from models.db import db
from models.feed import Feed, AIProposal, ProposalStatus


@directory_bp.route("/", methods=["GET"])
def directory_home():
    # If directory has 0 feeds on first visit, automatically seed sample feeds
    if Feed.query.count() == 0:
        seed_initial_feeds()

    q = request.args.get("q", "").strip()
    selected_collection = request.args.get("collection", "").strip()
    selected_topic = request.args.get("topic", "").strip()
    selected_audience = request.args.get("audience", "").strip()
    selected_tone = request.args.get("tone", "").strip()

    query = Feed.query

    if q:
        search_filter = f"%{q}%"
        query = query.filter(
            db.or_(
                Feed.title.ilike(search_filter),
                Feed.description.ilike(search_filter),
                Feed.primary_topic.ilike(search_filter),
                Feed.ai_description.ilike(search_filter),
                Feed.suggested_collection.ilike(search_filter),
                Feed.publisher.ilike(search_filter),
            )
        )

    if selected_collection:
        query = query.filter_by(suggested_collection=selected_collection)
    if selected_topic:
        query = query.filter_by(primary_topic=selected_topic)
    if selected_audience:
        query = query.filter_by(target_audience=selected_audience)
    if selected_tone:
        query = query.filter_by(content_tone=selected_tone)

    feeds = query.order_by(Feed.created_at.desc()).all()

    # Aggregations for filter dropdowns
    all_collections = sorted(list(set(f.suggested_collection for f in Feed.query.all() if f.suggested_collection)))
    all_topics = sorted(list(set(f.primary_topic for f in Feed.query.all() if f.primary_topic)))
    all_audiences = sorted(list(set(f.target_audience for f in Feed.query.all() if f.target_audience)))
    all_tones = sorted(list(set(f.content_tone for f in Feed.query.all() if f.content_tone)))

    # If requested by HTMX, return only the feeds partial
    if request.headers.get("HX-Request"):
        return render_template("partials/feed_grid.html", feeds=feeds)

    pending_proposals_count = AIProposal.query.filter_by(status=ProposalStatus.PENDING_REVIEW).count()

    return render_template(
        "directory.html",
        feeds=feeds,
        q=q,
        selected_collection=selected_collection,
        selected_topic=selected_topic,
        selected_audience=selected_audience,
        selected_tone=selected_tone,
        all_collections=all_collections,
        all_topics=all_topics,
        all_audiences=all_audiences,
        all_tones=all_tones,
        total_feeds=Feed.query.count(),
        pending_proposals_count=pending_proposals_count,
    )


@directory_bp.route("/feed/<int:feed_id>", methods=["GET"])
def feed_detail(feed_id: int):
    feed = db.get_or_404(Feed, feed_id)
    # Get associated proposal for sample articles preview if available
    proposal = AIProposal.query.filter_by(feed_url=feed.feed_url).order_by(AIProposal.created_at.desc()).first()
    sample_articles = proposal.sample_articles if proposal and proposal.sample_articles else []

    if request.headers.get("HX-Request"):
        return render_template("partials/feed_modal.html", feed=feed, sample_articles=sample_articles)

    return render_template("feed_detail.html", feed=feed, sample_articles=sample_articles)


@directory_bp.route("/seed", methods=["POST", "GET"])
def seed_endpoint():
    seed_initial_feeds()
    flash("Successfully populated directory with high-quality vetted RSS feeds!", "success")
    return redirect(url_for("directory.directory_home"))


def seed_initial_feeds():
    """Seeds vetted, representative feeds covering various collections and tones."""
    seeds = [
        {
            "feed_url": "https://news.ycombinator.com/rss",
            "site_url": "https://news.ycombinator.com",
            "title": "Hacker News: Front Page",
            "description": "Daily real-time technology news, computer science advancements, and entrepreneurial discussions curated by the Y Combinator community.",
            "publisher": "Y Combinator",
            "primary_topic": "Technology News",
            "sub_topics": ["Startups", "Programming", "Artificial Intelligence", "Hacker Culture"],
            "target_audience": "intermediate",
            "content_types": ["news", "opinion", "announcements"],
            "content_tone": "newsy",
            "suggested_collection": "Tech & Startups",
            "ai_description": "Premier community-driven pulse on technology breakthroughs, software development discussions, and startup innovation.",
            "evidence": ["High density of code & framework announcements", "Active community submissions on tooling"],
            "article_count": 30,
        },
        {
            "feed_url": "https://simonwillison.net/atom/everything/",
            "site_url": "https://simonwillison.net",
            "title": "Simon Willison's Weblog",
            "description": "Deep technical explorations into LLMs, Datasette, Python, and open-source tooling by co-creator of Django Simon Willison.",
            "publisher": "Simon Willison",
            "primary_topic": "Generative AI Engineering",
            "sub_topics": ["LLMs", "Datasette", "Python", "Local AI", "Prompt Injection"],
            "target_audience": "advanced",
            "content_types": ["analysis", "tutorial", "opinion", "research"],
            "content_tone": "technical",
            "suggested_collection": "AI & Systems",
            "ai_description": "Authoritative engineering insights on deploying local LLMs, securing AI architectures against prompt injection, and database hacking.",
            "evidence": ["First-hand experiments with Gemma & Gemini", "Extensive code examples and TIL posts"],
            "article_count": 25,
        },
        {
            "feed_url": "https://feeds.arstechnica.com/arstechnica/index",
            "site_url": "https://arstechnica.com",
            "title": "Ars Technica",
            "description": "Rigorous reporting covering enterprise IT, cybersecurity vulnerabilities, space exploration, and scientific discovery.",
            "publisher": "Condé Nast",
            "primary_topic": "Cybersecurity & Science",
            "sub_topics": ["Information Security", "Spaceflight", "Hardware", "Policy"],
            "target_audience": "intermediate",
            "content_types": ["news", "analysis", "reviews"],
            "content_tone": "educational",
            "suggested_collection": "Science & Space",
            "ai_description": "Deep-dive tech journalism focusing on cyber vulnerabilities, aerospace telemetry, and long-term tech policy.",
            "evidence": ["Detailed investigations on zero-day exploits", "Thorough hardware architecture breakdowns"],
            "article_count": 20,
        },
        {
            "feed_url": "https://blog.python.org/feeds/posts/default",
            "site_url": "https://blog.python.org",
            "title": "Python Insider",
            "description": "Official announcements from the core Python development team, release managers, and Python Software Foundation.",
            "publisher": "Python Software Foundation",
            "primary_topic": "Python Core Development",
            "sub_topics": ["CPython", "PEP Proposals", "Release Candidates", "Language Design"],
            "target_audience": "advanced",
            "content_types": ["announcements", "documentation"],
            "content_tone": "technical",
            "suggested_collection": "Programming Languages",
            "ai_description": "Authoritative release milestones, security advisories, and steering council decisions straight from the Python core team.",
            "evidence": ["CPython release notes & bugfix tags", "PEP governance decisions"],
            "article_count": 15,
        },
        {
            "feed_url": "https://feeds.npr.org/1001/rss.xml",
            "site_url": "https://www.npr.org",
            "title": "NPR News",
            "description": "National Public Radio's top news stories, investigative reporting, cultural analysis, and global affairs.",
            "publisher": "National Public Radio",
            "primary_topic": "Global Affairs",
            "sub_topics": ["Public Policy", "Economics", "Culture", "Investigative Journalism"],
            "target_audience": "general",
            "content_types": ["news", "analysis"],
            "content_tone": "newsy",
            "suggested_collection": "News & Culture",
            "ai_description": "Balanced, public-interest reporting spanning international politics, scientific milestones, and economic reporting.",
            "evidence": ["Broad global correspondent reports", "Factual public service broadcasting"],
            "article_count": 25,
        },
        # Curated Substack Feeds
        {
            "feed_url": "https://astralcodexten.substack.com/feed",
            "site_url": "https://astralcodexten.substack.com",
            "title": "Astral Codex Ten",
            "description": "A blog about science, medicine, philosophy, artificial intelligence, and rational discourse by Scott Alexander.",
            "publisher": "Scott Alexander (Substack)",
            "primary_topic": "Philosophy & AI",
            "sub_topics": ["Rationality", "AI Safety", "Cognitive Science", "Medicine"],
            "target_audience": "advanced",
            "content_types": ["analysis", "opinion", "research"],
            "content_tone": "academic",
            "suggested_collection": "Science & Ideas",
            "ai_description": "Long-form rationalist essays exploring cognitive biases, AI trajectory, statistical methodology, and epistemology.",
            "evidence": ["Deep analysis of medical trials", "In-depth evaluations of frontier LLM trends"],
            "article_count": 20,
        },
        {
            "feed_url": "https://newsletter.pragmaticengineer.com/feed",
            "site_url": "https://newsletter.pragmaticengineer.com",
            "title": "The Pragmatic Engineer",
            "description": "The #1 technology newsletter on Substack, covering Big Tech, engineering career management, and software trends.",
            "publisher": "Gergely Orosz (Substack)",
            "primary_topic": "Engineering Leadership",
            "sub_topics": ["Big Tech", "Software Architecture", "Career Growth", "Engineering Management"],
            "target_audience": "intermediate",
            "content_types": ["analysis", "news", "opinion"],
            "content_tone": "technical",
            "suggested_collection": "Engineering Leadership",
            "ai_description": "Industry pulse on software engineering practices, compensation trends, tech market layoffs, and distributed architecture.",
            "evidence": ["First-hand engineering manager interviews", "Deep dives into tech stack migrations"],
            "article_count": 20,
        },
        {
            "feed_url": "https://blog.bytebytego.com/feed",
            "site_url": "https://blog.bytebytego.com",
            "title": "ByteByteGo Newsletter",
            "description": "Clear system design breakdowns, distributed systems fundamentals, and architecture diagrams by Alex Xu.",
            "publisher": "Alex Xu (Substack)",
            "primary_topic": "System Design",
            "sub_topics": ["Distributed Systems", "Cloud Architecture", "Databases", "Microservices"],
            "target_audience": "intermediate",
            "content_types": ["tutorial", "analysis", "documentation"],
            "content_tone": "educational",
            "suggested_collection": "System Architecture",
            "ai_description": "Visual system design tutorials breaking down high-scale infrastructure patterns, caching layers, and database sharding.",
            "evidence": ["Comprehensive architectural diagrams", "Step-by-step scaling blueprints"],
            "article_count": 20,
        },
        {
            "feed_url": "https://lenny.substack.com/feed",
            "site_url": "https://lenny.substack.com",
            "title": "Lenny's Newsletter",
            "description": "Actionable product advice, growth frameworks, and startup management strategies.",
            "publisher": "Lenny Rachitsky (Substack)",
            "primary_topic": "Product Management",
            "sub_topics": ["Product Strategy", "Growth Loops", "SaaS Metrics", "Go-To-Market"],
            "target_audience": "intermediate",
            "content_types": ["analysis", "tutorial", "reviews"],
            "content_tone": "educational",
            "suggested_collection": "Product & Growth",
            "ai_description": "Tactical guides on product-market fit, user onboarding conversion, growth experimentation, and hiring senior talent.",
            "evidence": ["Interviews with top CPOs", "Empirical SaaS growth case studies"],
            "article_count": 20,
        },
        {
            "feed_url": "https://thezvi.substack.com/feed",
            "site_url": "https://thezvi.substack.com",
            "title": "Don't Worry About the Vase",
            "description": "Exhaustive weekly roundups and strategic analysis of AI developments, safety research, and societal implications.",
            "publisher": "Zvi Mowshowitz (Substack)",
            "primary_topic": "AI Governance & Safety",
            "sub_topics": ["Frontier AI", "Alignment", "AGI Trajectory", "AI Policy"],
            "target_audience": "expert",
            "content_types": ["analysis", "research", "news"],
            "content_tone": "academic",
            "suggested_collection": "AI & Research",
            "ai_description": "Comprehensive synthesis of technical AI breakthroughs, safety alignment research, and macroeconomic modeling of AGI.",
            "evidence": ["Weekly multi-thousand word AI roundups", "Rigorous probability calibrations"],
            "article_count": 20,
        },
        {
            "feed_url": "https://www.platformer.news/feed",
            "site_url": "https://www.platformer.news",
            "title": "Platformer",
            "description": "Investigative journalism on social networks, AI platforms, antitrust regulations, and tech policy.",
            "publisher": "Casey Newton (Substack)",
            "primary_topic": "Tech Policy & Platforms",
            "sub_topics": ["Big Tech", "AI Regulation", "Social Networks", "Antitrust"],
            "target_audience": "general",
            "content_types": ["news", "analysis", "opinion"],
            "content_tone": "newsy",
            "suggested_collection": "Tech & Society",
            "ai_description": "Critical insider reporting examining how algorithmic platforms, AI breakthroughs, and antitrust regulation shape democracy.",
            "evidence": ["Scoops on platform policy changes", "Direct reporting from antitrust hearings"],
            "article_count": 15,
        },
        # Curated Reddit Communities
        {
            "feed_url": "https://www.reddit.com/r/programming/.rss",
            "site_url": "https://www.reddit.com/r/programming",
            "title": "r/programming",
            "description": "Computer programming discussions, language releases, system software, and developer war stories from Reddit.",
            "publisher": "Reddit Community (r/programming)",
            "primary_topic": "Software Development",
            "sub_topics": ["Compilers", "Open Source", "Algorithms", "Code Craftsmanship"],
            "target_audience": "intermediate",
            "content_types": ["news", "opinion", "documentation"],
            "content_tone": "technical",
            "suggested_collection": "Programming Languages",
            "ai_description": "Community-curated link repository for engineering blog posts, library announcements, and developer discussions.",
            "evidence": ["High volume of language releases", "Technical critique in submission threads"],
            "article_count": 25,
        },
        {
            "feed_url": "https://www.reddit.com/r/MachineLearning/.rss",
            "site_url": "https://www.reddit.com/r/MachineLearning",
            "title": "r/MachineLearning",
            "description": "Premier academic and industry subreddit for machine learning papers, research discussions, and model architectures.",
            "publisher": "Reddit Community (r/MachineLearning)",
            "primary_topic": "Machine Learning Research",
            "sub_topics": ["Deep Learning", "Transformers", "arXiv Papers", "PyTorch"],
            "target_audience": "expert",
            "content_types": ["research", "analysis", "announcements"],
            "content_tone": "academic",
            "suggested_collection": "AI & Research",
            "ai_description": "Rigorous peer discussion on newly published arXiv machine learning papers, training optimizations, and transformer models.",
            "evidence": ["Direct links to arXiv preprints", "Peer reviews of new benchmark claims"],
            "article_count": 25,
        },
        {
            "feed_url": "https://www.reddit.com/r/LocalLLaMA/.rss",
            "site_url": "https://www.reddit.com/r/LocalLLaMA",
            "title": "r/LocalLLaMA",
            "description": "The hub for running open-source large language models on local hardware, quantization techniques, and llama.cpp hacks.",
            "publisher": "Reddit Community (r/LocalLLaMA)",
            "primary_topic": "Open Source LLMs",
            "sub_topics": ["Quantization", "llama.cpp", "Gemma", "Ollama", "Fine-Tuning"],
            "target_audience": "advanced",
            "content_types": ["tutorial", "reviews", "announcements"],
            "content_tone": "technical",
            "suggested_collection": "AI & Systems",
            "ai_description": "Hands-on guides and benchmarks for quantizing and running Gemma, Llama, and Mistral models on local consumer hardware.",
            "evidence": ["VRAM benchmark charts", "Quantization speed comparisons"],
            "article_count": 25,
        },
        {
            "feed_url": "https://www.reddit.com/r/technology/.rss",
            "site_url": "https://www.reddit.com/r/technology",
            "title": "r/technology",
            "description": "A major subreddit dedicated to news and discussions about the creation and use of technology and its surrounding issues.",
            "publisher": "Reddit Community (r/technology)",
            "primary_topic": "Technology News",
            "sub_topics": ["Consumer Tech", "Cybersecurity", "Privacy", "Tech Industry"],
            "target_audience": "general",
            "content_types": ["news", "announcements"],
            "content_tone": "newsy",
            "suggested_collection": "Tech & Startups",
            "ai_description": "Mainstream breaking news coverage spanning cybersecurity breaches, consumer electronics, and government tech regulation.",
            "evidence": ["Broad investigative links", "Consumer tech security alerts"],
            "article_count": 25,
        },
        {
            "feed_url": "https://www.reddit.com/r/rust/.rss",
            "site_url": "https://www.reddit.com/r/rust",
            "title": "r/rust",
            "description": "Discussions, crate releases, and learning resources for the Rust programming language community.",
            "publisher": "Reddit Community (r/rust)",
            "primary_topic": "Rust Programming",
            "sub_topics": ["Cargo", "Crates", "Memory Safety", "Systems Programming"],
            "target_audience": "intermediate",
            "content_types": ["announcements", "tutorial", "reviews"],
            "content_tone": "technical",
            "suggested_collection": "Programming Languages",
            "ai_description": "Vibrant community showcase of new Rust crates, unsafe code audits, compiler improvements, and production deployment stories.",
            "evidence": ["Crate release announcements", "Benchmarking discussions"],
            "article_count": 25,
        },
    ]

    for item in seeds:
        if not Feed.query.filter_by(feed_url=item["feed_url"]).first():
            f = Feed(
                feed_url=item["feed_url"],
                site_url=item["site_url"],
                title=item["title"],
                description=item["description"],
                publisher=item["publisher"],
                primary_topic=item["primary_topic"],
                sub_topics=item["sub_topics"],
                target_audience=item["target_audience"],
                content_types=item["content_types"],
                content_tone=item["content_tone"],
                suggested_collection=item["suggested_collection"],
                ai_description=item["ai_description"],
                evidence=item["evidence"],
                article_count=item["article_count"],
                last_fetched_at=datetime.now(timezone.utc),
            )
            db.session.add(f)
    db.session.commit()
