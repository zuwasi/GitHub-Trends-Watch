"""Rating and classification engine for GitHub trending repositories.

Produces structured scores, tiers, categories, and maturity levels
based on scraped repo metrics. Works without an agent — pure Python.
"""

from collections import Counter


# Category keywords for classification
CATEGORY_KEYWORDS = {
    "AI/ML": [
        "ai", "ml", "machine learning", "deep learning", "neural", "llm",
        "gpt", "transformer", "model", "inference", "training", "rag",
        "agent", "embedding", "vector", "tensor", "pytorch", "tensorflow",
        "diffusion", "stable diffusion", "langchain", "copilot", "gemini",
        "claude", "openai", "anthropic", "huggingface", "dataset",
    ],
    "Security": [
        "security", "vulnerability", "cve", "exploit", "pentest", "pentesting",
        "red team", "blue team", "soc", "siem", "firewall", "encryption",
        "crypto", "auth", "oauth", "jwt", "secret", "sbom", "malware",
        "ransomware", "phishing", "zero-day", "cryptography", "tls",
    ],
    "DevOps": [
        "ci/cd", "ci", "cd", "pipeline", "docker", "kubernetes", "k8s",
        "helm", "terraform", "ansible", "jenkins", "github actions",
        "deployment", "orchestration", "container", "registry", "argo",
        "monitoring", "observability", "grafana", "prometheus",
    ],
    "Web": [
        "web", "frontend", "backend", "react", "vue", "angular", "svelte",
        "nextjs", "next.js", "nuxt", "html", "css", "javascript", "typescript",
        "express", "fastapi", "flask", "django", "rails", "spring",
        "api", "rest", "graphql", "server", "http",
    ],
    "Data": [
        "data", "database", "sql", "nosql", "postgres", "mysql", "redis",
        "mongodb", "spark", "hadoop", "kafka", "etl", "warehouse",
        "analytics", "bi", "dashboard", "visualization", "pandas",
        "numpy", "jupyter", "notebook", "streaming",
    ],
    "Mobile": [
        "mobile", "ios", "android", "flutter", "react native", "swift",
        "kotlin", "xamarin", "expo", "app", "phone", "tablet",
    ],
    "Systems": [
        "system", "kernel", "driver", "embedded", "firmware", "rtos",
        "bare-metal", "hardware", "cpu", "gpu", "memory", "storage",
        "filesystem", "network", "protocol", "os", "linux", "windows",
        "assembly", "rust", "c/c++", "zig", "fpga",
    ],
    "Tools": [
        "tool", "cli", "command", "utility", "automation", "script",
        "productivity", "editor", "ide", "plugin", "extension",
        "linting", "formatting", "testing", "benchmark", "debugger",
        "build", "make", "cmake", "package", "dependency",
    ],
}


def classify_category(repo):
    """Classify a repo into a category based on description and name."""
    text = (repo.get("description", "") + " " + repo.get("name", "")).lower()
    scores = Counter()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[category] += 1
    if scores:
        return scores.most_common(1)[0][0]
    return "Other"


def compute_maturity(repo):
    """Determine maturity level based on total stars."""
    stars = repo.get("stars", 0)
    if stars < 100:
        return "Experimental"
    elif stars < 1000:
        return "Early-Stage"
    elif stars < 10000:
        return "Growing"
    elif stars < 50000:
        return "Mature"
    else:
        return "Established"


def compute_innovation_score(repo):
    """Compute innovation score (0-100) based on growth velocity.

    High stars_today relative to total stars indicates a rapidly
    emerging project (high innovation/buzz).
    """
    stars = repo.get("stars", 0)
    today = repo.get("stars_today", 0)
    if stars == 0:
        return 0
    ratio = today / stars
    # A ratio of 0.1+ (10% of total stars in one day) is extremely high
    score = min(100, ratio * 500)
    return round(score)


def compute_security_score(repo):
    """Estimate security posture (0-100) based on available signals.

    Without deep repo inspection, we use heuristics:
    - More mature projects tend to be more security-hardened
    - More forks suggest more scrutiny
    - More contributors suggest more review
    """
    stars = repo.get("stars", 0)
    forks = repo.get("forks", 0)
    contribs = len(repo.get("contributors", []))

    # Maturity component (0-40)
    if stars >= 50000:
        maturity = 40
    elif stars >= 10000:
        maturity = 30
    elif stars >= 1000:
        maturity = 20
    elif stars >= 100:
        maturity = 10
    else:
        maturity = 5

    # Fork scrutiny component (0-30)
    if forks >= 1000:
        scrutiny = 30
    elif forks >= 100:
        scrutiny = 20
    elif forks >= 10:
        scrutiny = 10
    else:
        scrutiny = 5

    # Contributor diversity (0-30)
    if contribs >= 5:
        diversity = 30
    elif contribs >= 3:
        diversity = 20
    elif contribs >= 1:
        diversity = 10
    else:
        diversity = 5  # Unknown contributors, give benefit of the doubt

    return maturity + scrutiny + diversity


def compute_overall_score(repo):
    """Compute overall score (0-100) from weighted sub-scores.

    Weights:
    - Popularity (stars): 30%
    - Growth velocity (stars today): 25%
    - Maturity: 20%
    - Security signals: 15%
    - Community (forks + contributors): 10%
    """
    stars = repo.get("stars", 0)
    today = repo.get("stars_today", 0)
    forks = repo.get("forks", 0)
    contribs = len(repo.get("contributors", []))

    # Popularity score (0-100) — logarithmic scaling
    if stars >= 100000:
        pop = 100
    elif stars >= 10000:
        pop = 70 + min(30, (stars - 10000) / 3000)
    elif stars >= 1000:
        pop = 40 + min(30, (stars - 1000) / 300)
    elif stars >= 100:
        pop = 20 + min(20, (stars - 100) / 5)
    else:
        pop = stars / 5
    pop = min(100, pop)

    # Growth velocity (0-100)
    if today >= 1000:
        growth = 100
    elif today >= 500:
        growth = 80
    elif today >= 200:
        growth = 60
    elif today >= 100:
        growth = 40
    elif today >= 50:
        growth = 25
    else:
        growth = max(0, today)

    # Maturity (0-100)
    maturity_label = compute_maturity(repo)
    maturity_map = {
        "Experimental": 10, "Early-Stage": 30, "Growing": 55,
        "Mature": 80, "Established": 100,
    }
    maturity = maturity_map.get(maturity_label, 30)

    # Security (0-100)
    security = compute_security_score(repo)

    # Community (0-100)
    community = min(100, forks / 10 + contribs * 10)

    # Weighted sum
    overall = (
        pop * 0.30 +
        growth * 0.25 +
        maturity * 0.20 +
        security * 0.15 +
        community * 0.10
    )

    return round(overall)


def classify_tier(score):
    """Map a 0-100 score to a letter tier."""
    if score >= 85:
        return "S"
    elif score >= 70:
        return "A"
    elif score >= 50:
        return "B"
    elif score >= 30:
        return "C"
    else:
        return "D"


def rate_repo(repo):
    """Compute full rating for a single repo.

    Returns a dict with: overall_score, tier, category, maturity,
    innovation_score, security_score, popularity_score.
    """
    overall = compute_overall_score(repo)
    return {
        "overall_score": overall,
        "tier": classify_tier(overall),
        "category": classify_category(repo),
        "maturity": compute_maturity(repo),
        "innovation_score": compute_innovation_score(repo),
        "security_score": compute_security_score(repo),
        "popularity_score": round(min(100, _popularity_raw(repo)), 1),
    }


def _popularity_raw(repo):
    """Internal: raw popularity score before rounding."""
    stars = repo.get("stars", 0)
    if stars >= 100000:
        return 100
    elif stars >= 10000:
        return 70 + min(30, (stars - 10000) / 3000)
    elif stars >= 1000:
        return 40 + min(30, (stars - 1000) / 300)
    elif stars >= 100:
        return 20 + min(20, (stars - 100) / 5)
    else:
        return stars / 5


def rate_all_repos(repos):
    """Rate all repos and return list of (repo, rating) tuples, sorted by score."""
    rated = []
    for repo in repos:
        rating = rate_repo(repo)
        rated.append((repo, rating))
    # Sort by overall score descending
    rated.sort(key=lambda x: x[1]["overall_score"], reverse=True)
    return rated


def get_category_summary(rated_repos):
    """Return a summary dict of categories and their counts."""
    counts = Counter()
    for repo, rating in rated_repos:
        counts[rating["category"]] += 1
    return dict(counts)


def get_tier_distribution(rated_repos):
    """Return a dict of tier -> count."""
    counts = Counter()
    for repo, rating in rated_repos:
        counts[rating["tier"]] += 1
    return dict(counts)
