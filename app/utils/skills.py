import re

# Common technical and professional skills for extraction and matching.
KNOWN_SKILLS: set[str] = {
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "ruby", "php",
    "swift", "kotlin", "scala", "r", "matlab", "sql", "html", "css", "react", "angular",
    "vue", "next.js", "node.js", "django", "flask", "fastapi", "spring", "spring boot",
    ".net", "asp.net", "express", "graphql", "rest", "api", "microservices", "docker",
    "kubernetes", "aws", "azure", "gcp", "google cloud", "terraform", "ansible", "jenkins",
    "ci/cd", "git", "github", "gitlab", "linux", "unix", "bash", "shell", "powershell",
    "mongodb", "postgresql", "mysql", "redis", "elasticsearch", "kafka", "rabbitmq",
    "spark", "hadoop", "airflow", "dbt", "snowflake", "databricks", "tableau", "power bi",
    "excel", "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "keras",
    "machine learning", "deep learning", "nlp", "computer vision", "data analysis",
    "data engineering", "data science", "statistics", "agile", "scrum", "jira", "confluence",
    "project management", "leadership", "communication", "problem solving", "teamwork",
    "figma", "sketch", "ui/ux", "product management", "salesforce", "sap", "oracle",
    "selenium", "pytest", "junit", "unit testing", "integration testing", "tdd",
    "security", "oauth", "jwt", "sso", "devops", "sre", "monitoring", "prometheus",
    "grafana", "datadog", "splunk", "elk", "nginx", "apache", "websocket", "grpc",
    "protobuf", "json", "xml", "yaml", "etl", "elt", "bi", "analytics", "a/b testing",
    "seo", "sem", "marketing", "content strategy", "copywriting", "customer success",
    "account management", "negotiation", "presentation", "public speaking", "mentoring",
    "coaching", "budgeting", "forecasting", "financial modeling", "accounting", "audit",
    "compliance", "gdpr", "hipaa", "soc 2", "pci dss", "blockchain", "solidity", "web3",
    "ios", "android", "flutter", "react native", "xamarin", "unity", "unreal engine",
    "game development", "embedded systems", "iot", "arduino", "raspberry pi", "fpga",
    "verilog", "vhdl", "cad", "autocad", "solidworks", "matlab simulink", "simulation",
    "control systems", "robotics", "computer architecture", "operating systems",
    "networking", "tcp/ip", "dns", "load balancing", "cdn", "cloudflare", "vercel",
    "heroku", "render", "netlify", "firebase", "supabase", "prisma", "sequelize",
    "typeorm", "hibernate", "orm", "sqlalchemy", "celery", "rq", "asyncio", "multithreading",
    "concurrency", "distributed systems", "system design", "architecture", "design patterns",
    "clean code", "refactoring", "code review", "pair programming", "technical writing",
    "documentation", "stakeholder management", "cross-functional", "vendor management",
    "procurement", "supply chain", "logistics", "inventory management", "erp", "crm",
    "hubspot", "marketo", "google analytics", "mixpanel", "amplitude", "segment",
    "looker", "mode", "metabase", "qlik", "sas", "spss", "stata", "econometrics",
    "quantitative analysis", "qualitative research", "user research", "usability testing",
    "wireframing", "prototyping", "design thinking", "lean startup", "six sigma",
    "process improvement", "kaizen", "itil", "cobit", "pmp", "prince2", "csm", "psm",
    "aws certified", "azure certified", "gcp certified", "cissp", "cisa", "comptia",
    "ccna", "ccnp", "cka", "ckad", "terraform associate", "hashicorp",
}

SKILL_ALIASES: dict[str, str] = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "k8s": "kubernetes",
    "postgres": "postgresql",
    "pg": "postgresql",
    "ml": "machine learning",
    "dl": "deep learning",
    "ai": "machine learning",
    "gcp": "google cloud",
    "amazon web services": "aws",
    "microsoft azure": "azure",
    "reactjs": "react",
    "react.js": "react",
    "nodejs": "node.js",
    "node": "node.js",
    "vuejs": "vue",
    "nextjs": "next.js",
    "fast api": "fastapi",
    "ci cd": "ci/cd",
    "cicd": "ci/cd",
    "rest api": "rest",
    "restful": "rest",
    "restful api": "rest",
    "scikit learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "powerbi": "power bi",
    "power-bi": "power bi",
    "google cloud platform": "google cloud",
}


def normalize_skill(skill: str) -> str:
    cleaned = skill.strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return SKILL_ALIASES.get(cleaned, cleaned)


def extract_skills_from_text(text: str) -> list[str]:
    if not text:
        return []

    text_lower = text.lower()
    found: set[str] = set()

    for skill in KNOWN_SKILLS:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text_lower):
            found.add(normalize_skill(skill))

    for alias, canonical in SKILL_ALIASES.items():
        pattern = r"\b" + re.escape(alias) + r"\b"
        if re.search(pattern, text_lower):
            found.add(canonical)

    return sorted(found)


def clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
