"""Generate the offline SAMPLE dataset (data/sample_jobs.json and .csv).

All companies, jobs and links in this dataset are FICTIONAL and exist only so
the project can be demonstrated without internet access. Links use the
reserved example.com domain. Any resemblance to real organisations is
coincidental. The generator is deterministic (fixed random seed), and every
record is passed through the same extraction pipeline as scraped jobs.

Run:  python scripts/generate_sample_data.py
"""

from __future__ import annotations

import json
import random
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings  # noqa: E402
from src.deduplication import deduplicate  # noqa: E402
from src.extractors import build_job_record  # noqa: E402
from src.export import to_csv_bytes  # noqa: E402

import pandas as pd  # noqa: E402

RNG = random.Random(42)
REFERENCE_DAY = date(2026, 10, 24)

COMPANIES = [
    ("Arcadia Data Labs", "an analytics consultancy helping retailers make data-driven decisions"),
    ("Bluefin Systems", "a product company building cloud-native logistics software"),
    ("Cedarline Technologies", "an IT services firm delivering digital transformation projects"),
    ("Deltawave Software", "a SaaS start-up building collaboration tools for small businesses"),
    ("Evergreen FinServ Tech", "a fintech platform for digital lending and payments"),
    ("Foxglove Health AI", "a healthtech company applying AI to diagnostic imaging"),
    ("Granite Infra Solutions", "a cloud infrastructure and managed-services provider"),
    ("Helixon Robotics", "a robotics company building warehouse automation systems"),
    ("Indigo Retail Labs", "an e-commerce technology company serving fashion brands"),
    ("Juniper Learning Tech", "an edtech platform for school and college learners"),
    ("Kestrel Secure", "a cybersecurity firm offering managed detection and response"),
    ("Lotus Mobility Tech", "an electric-mobility company building connected-vehicle software"),
    ("Monsoon Media Labs", "a digital media company running streaming and content platforms"),
    ("Novachip Design", "a semiconductor design services company"),
    ("Orchid Consulting Group", "a management and technology consulting firm"),
    ("Peacock Payments", "a payments gateway for online merchants"),
    ("Quartz Quality Labs", "a software testing and quality-engineering services company"),
    ("Saffron Agritech", "an agritech start-up using IoT and analytics for farmers"),
    ("Teal Logistics Digital", "a supply-chain analytics company"),
    ("Umbra Insurance Digital", "the digital arm of an insurance group"),
    ("Vertex Cloudworks", "a DevOps and platform-engineering consultancy"),
    ("Willow Civic Tech", "a govtech company building citizen-service portals"),
]

LOCATIONS = ["Bengaluru, Karnataka", "Hyderabad, Telangana", "Pune, Maharashtra", "Chennai, Tamil Nadu",
             "Noida, Uttar Pradesh", "Gurugram, Haryana", "Mumbai, Maharashtra", "Kolkata, West Bengal",
             "Ahmedabad, Gujarat", "Jaipur, Rajasthan", "Kochi, Kerala", "Indore, Madhya Pradesh",
             "Remote (India)", "Hybrid — Bengaluru", "Hybrid — Pune", "New Delhi, Delhi"]

ELIGIBILITY = [
    "B.Tech / B.E. in Computer Science, IT, AI & ML or related branches (2025 or 2026 batch).",
    "B.Tech/B.E., BCA, MCA or M.Sc. in Computer Science or a related field.",
    "Bachelor's degree in Engineering or Science with a minimum CGPA of 6.5.",
    "B.Tech / M.Tech in Electronics, Electrical or Computer Engineering.",
    "Any graduate with strong analytical skills; B.Tech or B.Sc. preferred.",
]

# (titles, category hint, skills, intro, responsibilities, experience phrase, employment phrase, salary options)
TEMPLATES = [
    (["Machine Learning Engineer Intern", "AI/ML Intern"], ["python", "machine learning", "scikit-learn", "pandas", "numpy", "sql"],
     "Join our applied-ML team to prototype models that solve real business problems.",
     ["Clean and explore datasets with pandas and NumPy", "Train and evaluate classification and regression models",
      "Write reproducible experiments and document results", "Help deploy models behind simple REST APIs",
      "Present findings to product teams", "Monitor model quality after release"],
     "Freshers and final-year students are welcome; no prior work experience required.", "6-month internship",
     ["Stipend: ₹25,000 per month", "Stipend: ₹30,000 per month", ""]),
    (["Graduate Engineer Trainee – Data Science", "Data Science Trainee"], ["python", "statistics", "machine learning", "sql", "data visualization"],
     "Our graduate programme trains new engineers in end-to-end data-science projects.",
     ["Build statistical models for demand forecasting", "Create dashboards for business stakeholders",
      "Work on feature engineering and model validation", "Learn MLOps practices from senior mentors",
      "Participate in code reviews and knowledge-sharing sessions", "Automate recurring analysis with Python"],
     "Experience: 0-1 years.", "Full-time graduate trainee programme", ["CTC: 6-8 LPA", "CTC: 5.5 LPA", ""]),
    (["Junior Data Analyst", "Data Analyst – Fresher", "Associate Data Analyst"], ["sql", "excel", "power bi", "python", "data analysis"],
     "We are looking for curious analysts who enjoy turning raw data into clear insights.",
     ["Write SQL queries to extract and validate data", "Build Power BI dashboards and weekly reports",
      "Analyse trends and present recommendations", "Maintain data-quality checks", "Work closely with operations teams",
      "Document metric definitions"], "Experience: 0-2 years in analytics (freshers can apply).", "Full-time",
     ["CTC: 4-6 LPA", "Salary: ₹4,50,000 per annum", ""]),
    (["Business Intelligence Intern", "BI Analyst Intern"], ["tableau", "sql", "excel", "data visualization", "communication"],
     "Help our BI team design dashboards used by leadership every week.",
     ["Design Tableau dashboards", "Gather reporting requirements", "Automate Excel reports", "Validate KPI calculations",
      "Prepare presentation decks", "Support ad-hoc analysis requests"], "Open to final-year students and freshers.", "Internship (3 months)",
     ["Stipend: ₹15,000 per month", ""]),
    (["Associate Software Engineer", "Software Engineer – Fresher", "Software Engineer I"], ["java", "spring boot", "sql", "rest api", "git", "data structures"],
     "Build and maintain backend services used by thousands of customers.",
     ["Develop REST APIs with Java and Spring Boot", "Write unit and integration tests", "Fix bugs and improve performance",
      "Participate in agile ceremonies", "Review code and follow clean-code practices", "Work with relational databases"],
     "Experience: 0-1 years. Freshers with strong fundamentals in data structures are encouraged to apply.", "Full-time, permanent",
     ["CTC: 7-9 LPA", "CTC: 6.5 LPA", ""]),
    (["Python Developer – Entry Level", "Junior Python Developer"], ["python", "django", "rest api", "postgresql", "git", "docker"],
     "Work on Django-based web applications and internal automation tools.",
     ["Develop features in Django and Django REST Framework", "Write automated tests with pytest", "Containerise services with Docker",
      "Optimise PostgreSQL queries", "Maintain CI pipelines", "Collaborate with front-end developers"],
     "0-2 years of experience in Python development.", "Full-time", ["CTC: 5-7 LPA", ""]),
    (["Frontend Developer Intern", "React Developer Intern"], ["javascript", "react", "html", "css", "git", "typescript"],
     "Help us craft fast, accessible web interfaces.",
     ["Build reusable React components", "Translate Figma designs into responsive pages", "Improve accessibility and performance",
      "Write component tests", "Integrate REST APIs", "Fix cross-browser issues"], "No prior experience required; a portfolio or GitHub profile helps.",
     "Internship (6 months) with possible full-time conversion", ["Stipend: ₹20,000 per month", ""]),
    (["Full Stack Developer – Graduate", "Junior Full Stack Engineer"], ["javascript", "node.js", "react", "mongodb", "rest api", "git"],
     "Own features end to end across our MERN-stack product.",
     ["Build APIs with Node.js and Express", "Create React user interfaces", "Model data in MongoDB", "Deploy to cloud environments",
      "Monitor and debug production issues", "Write technical documentation"], "Experience: 0-2 years.", "Full-time", ["CTC: 6-8 LPA", ""]),
    (["Android Developer Trainee", "Mobile App Developer – Fresher"], ["kotlin", "android", "java", "rest api", "git"],
     "Build Android apps used daily by our customers.",
     ["Develop Android features in Kotlin", "Integrate REST APIs and handle offline caching", "Write UI and unit tests",
      "Fix crashes reported in production", "Collaborate with designers", "Publish releases to the Play Store"],
     "Freshers are welcome to apply.", "Full-time trainee", ["", "CTC: 5 LPA"]),
    (["QA Engineer – Fresher", "Software Test Engineer Trainee"], ["manual testing", "automation testing", "selenium", "sql", "api testing"],
     "Ensure every release meets our quality bar.",
     ["Write and execute test cases", "Automate regression suites with Selenium", "Test REST APIs with Postman",
      "Log and track defects in Jira", "Validate data with SQL", "Participate in release sign-offs"],
     "Experience: 0-1 years.", "Full-time", ["CTC: 3.5-5 LPA", ""]),
    (["SDET Intern", "Test Automation Intern"], ["python", "playwright", "pytest", "automation testing", "git", "ci/cd"],
     "Help build our next-generation browser test automation framework.",
     ["Write end-to-end tests with Playwright and pytest", "Integrate tests into CI/CD pipelines", "Reduce flaky tests",
      "Create test-data utilities", "Report test coverage", "Pair with developers on testability"],
     "Open to students graduating in 2026; no experience required.", "Internship", ["Stipend: ₹18,000 per month", ""]),
    (["DevOps Engineer Trainee", "Cloud Operations Trainee"], ["linux", "aws", "docker", "kubernetes", "ci/cd", "bash"],
     "Learn to run reliable cloud infrastructure at scale.",
     ["Automate deployments with CI/CD pipelines", "Manage Linux servers and containers", "Monitor services and respond to alerts",
      "Write infrastructure scripts in Bash", "Work with Kubernetes clusters", "Document runbooks"],
     "Experience: 0-1 years; AWS certification is a plus.", "Full-time graduate trainee", ["CTC: 5-6 LPA", ""]),
    (["Cloud Support Associate", "Associate Cloud Engineer"], ["aws", "azure", "linux", "networking", "communication"],
     "Help customers solve cloud infrastructure issues.",
     ["Troubleshoot customer issues on AWS and Azure", "Explain technical concepts clearly", "Escalate complex problems",
      "Contribute to the knowledge base", "Monitor service health", "Work in rotational shifts"],
     "0 to 2 years of experience.", "Full-time", ["", "CTC: 4.5 LPA"]),
    (["Cybersecurity Analyst – Graduate", "SOC Analyst Trainee"], ["cybersecurity", "network security", "siem", "linux", "networking"],
     "Protect our clients by monitoring and responding to security events.",
     ["Monitor alerts in the SIEM", "Investigate suspicious activity", "Document incidents", "Assist with vulnerability assessments",
      "Keep up with threat intelligence", "Support compliance audits"], "Freshers with security certifications are encouraged to apply.",
     "Full-time", ["CTC: 4-6 LPA", ""]),
    (["Security Engineering Intern"], ["python", "penetration testing", "cybersecurity", "linux", "cryptography"],
     "Work with our red team on application-security assessments.",
     ["Assist with penetration tests", "Write Python scripts for security automation", "Review code for vulnerabilities",
      "Research new attack techniques", "Prepare assessment reports", "Harden Linux servers"], "Final-year students only.", "Internship",
     ["Stipend: ₹20,000 per month"]),
    (["NLP Engineer Intern", "Generative AI Intern"], ["python", "natural language processing", "pytorch", "hugging face", "large language models"],
     "Build language features such as search, summarisation and chat assistants.",
     ["Fine-tune transformer models", "Build retrieval pipelines over documents", "Evaluate model outputs for quality and bias",
      "Prototype LLM-powered features", "Clean and label text data", "Write evaluation reports"],
     "No prior industry experience required.", "Internship (6 months)", ["Stipend: ₹35,000 per month", ""]),
    (["Computer Vision Engineer – Fresher"], ["python", "computer vision", "deep learning", "pytorch", "numpy"],
     "Develop vision models for medical-image analysis.",
     ["Train image-classification and segmentation models", "Prepare and augment image datasets", "Optimise inference speed",
      "Collaborate with domain experts", "Track experiments", "Write technical reports"], "Experience: 0-1 years.", "Full-time",
     ["CTC: 8-10 LPA", ""]),
    (["Data Engineer – Graduate Trainee", "Junior Data Engineer"], ["python", "sql", "spark", "etl", "aws", "data engineering"],
     "Build pipelines that move and transform data reliably.",
     ["Develop ETL jobs with Spark and Python", "Model data in the warehouse", "Write data-quality checks", "Schedule workflows",
      "Optimise query performance", "Document data lineage"], "0-1 years of experience.", "Full-time graduate trainee",
     ["CTC: 7 LPA", ""]),
    (["Embedded Software Engineer Trainee", "Firmware Engineer – Fresher"], ["embedded c", "embedded systems", "c++", "iot", "linux"],
     "Develop firmware for connected devices.",
     ["Write embedded C code for microcontrollers", "Debug hardware-software integration issues", "Develop IoT communication modules",
      "Test firmware on real devices", "Write technical documentation", "Work with hardware engineers"],
     "Freshers from ECE/EEE backgrounds are welcome.", "Full-time", ["CTC: 4.5-6 LPA", ""]),
    (["VLSI Design Engineer – Graduate", "RTL Design Trainee"], ["verilog", "vlsi", "c programming", "linux", "shell scripting"],
     "Join our silicon team working on SoC design and verification.",
     ["Write RTL in Verilog/SystemVerilog", "Run simulations and analyse waveforms", "Build verification test benches",
      "Automate flows with scripts", "Participate in design reviews", "Learn physical-design basics"],
     "Experience: 0-1 years.", "Full-time graduate trainee", ["", "CTC: 9 LPA"]),
    (["Robotics Software Intern"], ["python", "c++", "robotics", "computer vision", "linux"],
     "Program robots that automate warehouse operations.",
     ["Develop ROS nodes in C++ and Python", "Integrate sensors and cameras", "Test algorithms in simulation",
      "Tune motion-planning parameters", "Analyse robot logs", "Document experiments"], "Open to final-year students.", "Internship",
     ["Stipend: ₹22,000 per month", ""]),
    (["UI/UX Design Intern", "Product Design Intern"], ["figma", "ui/ux design", "communication", "html", "css"],
     "Design intuitive experiences for our web and mobile products.",
     ["Create wireframes and prototypes in Figma", "Conduct usability tests", "Maintain the design system",
      "Collaborate with developers", "Present design rationale", "Analyse user feedback"], "No experience required; portfolio mandatory.",
     "Internship (3 months)", ["Stipend: ₹12,000 per month", ""]),
    (["Business Analyst – Fresher", "Associate Business Analyst"], ["business analysis", "sql", "excel", "communication", "agile"],
     "Bridge business needs and technology solutions.",
     ["Gather and document requirements", "Write user stories", "Analyse data with SQL and Excel", "Support user-acceptance testing",
      "Prepare process flow diagrams", "Coordinate with stakeholders"], "Experience: 0-2 years.", "Full-time",
     ["CTC: 5-7 LPA", ""]),
    (["Technology Consultant – Graduate Program", "Analyst – Technology Consulting"], ["communication", "problem solving", "sql", "excel", "agile"],
     "Start your consulting career on digital-transformation projects.",
     ["Analyse client processes", "Support solution design", "Prepare client presentations", "Test and validate solutions",
      "Research industry trends", "Work in cross-functional teams"], "Freshers from the 2026 batch are eligible.",
     "Full-time graduate program", ["CTC: 8 LPA", ""]),
    (["Product Management Intern", "Associate Product Manager – Fresher"], ["product management", "sql", "communication", "data analysis", "agile"],
     "Help define and ship features that customers love.",
     ["Write product requirement documents", "Analyse product metrics", "Run user interviews", "Prioritise the backlog",
      "Coordinate launches", "Track competitor products"], "No prior experience required.", "Internship", ["Stipend: ₹25,000 per month", ""]),
    (["IT Support Engineer – Fresher", "Technical Support Associate"], ["linux", "networking", "communication", "windows", "problem solving"],
     "Keep our employees productive with fast, friendly IT support.",
     ["Resolve hardware and software issues", "Manage user accounts", "Maintain the asset inventory", "Configure network devices",
      "Document solutions", "Support new-joiner onboarding"], "0-1 years of experience.", "Full-time", ["CTC: 3-4 LPA", ""]),
    (["Digital Marketing Analyst – Fresher"], ["digital marketing", "excel", "data analysis", "communication"],
     "Measure and improve our online marketing campaigns.",
     ["Track campaign performance", "Run A/B experiments on landing pages", "Prepare weekly reports", "Optimise SEO content",
      "Manage social-media calendars", "Analyse customer funnels"], "Freshers can apply.", "Full-time", ["", "CTC: 3.6 LPA"]),
    (["Financial Analyst – Graduate Trainee"], ["financial analysis", "excel", "sql", "power bi", "communication"],
     "Support budgeting, forecasting and reporting for our lending business.",
     ["Build financial models in Excel", "Prepare MIS reports", "Analyse loan-portfolio performance", "Automate dashboards in Power BI",
      "Support audits", "Track monthly variances"], "Experience: 0-1 years.", "Full-time graduate trainee", ["CTC: 6 LPA", ""]),
    # A few experienced roles so the fresher filter and eligibility check can be demonstrated.
    (["Senior Data Scientist"], ["python", "machine learning", "deep learning", "spark", "mlops"],
     "Lead the design of large-scale recommendation models.",
     ["Lead model design and experimentation", "Mentor junior data scientists", "Own production ML systems",
      "Define the team's technical roadmap", "Partner with product leadership", "Publish internal research"],
     "Minimum 5 years of experience in applied machine learning.", "Full-time", [""]),
    (["Backend Engineer (2-4 years)", "Software Engineer II"], ["java", "microservices", "kubernetes", "system design", "aws"],
     "Scale our payments platform to millions of transactions.",
     ["Design microservices", "Improve reliability and latency", "Own on-call rotations", "Review designs and code",
      "Mentor new engineers", "Drive technical decisions"], "2-4 years of experience in backend development.", "Full-time", [""]),
    (["DevOps Lead"], ["kubernetes", "terraform", "aws", "ci/cd", "linux"],
     "Lead our platform team's infrastructure strategy.",
     ["Lead a team of DevOps engineers", "Design multi-region infrastructure", "Own the security posture", "Manage cloud costs",
      "Define SRE practices", "Plan capacity"], "7+ years of experience in DevOps.", "Full-time", [""]),
    (["Data Analyst (3+ years)"], ["sql", "tableau", "python", "statistics", "a/b testing"],
     "Drive experimentation and product analytics.",
     ["Design A/B tests", "Own core product metrics", "Partner with product managers", "Build self-serve dashboards",
      "Mentor junior analysts", "Present to leadership"], "3+ years of experience in product analytics.", "Full-time", [""]),
]


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def make_description(company: str, blurb: str, tpl, extra_skills: list[str], location: str, deadline: date | None, salary: str) -> str:
    titles, skills, intro, resp, exp, emp, _ = tpl
    lines = [f"About {company}: {company} is {blurb}.", intro, "", "What you will do:"]
    lines += [f"• {r}" for r in RNG.sample(resp, k=4)]
    lines += ["", "What we are looking for:",
              f"• Skills: {', '.join(skills + extra_skills)}",
              f"• {exp}", f"• Eligibility: {RNG.choice(ELIGIBILITY)}", "", f"Employment type: {emp}.", f"Location: {location}."]
    if "Remote" in location:
        lines.append("This is a fully remote role open to candidates across India.")
    elif "Hybrid" in location:
        lines.append("This is a hybrid role with three days a week in the office.")
    elif RNG.random() < 0.6:
        lines.append("Work mode: on-site, five days a week from our office.")
    if salary:
        lines.append(salary + ".")
    if deadline:
        lines.append(f"Apply by {deadline.strftime('%d %B %Y')}.")
    return "\n".join(lines)


def generate(n_per_template: tuple[int, int] = (4, 5)) -> list[dict]:
    jobs, counter = [], 0
    optional_skills = ["git", "communication", "problem solving", "teamwork", "agile", "linux"]
    for tpl in TEMPLATES:
        titles, skills, _, _, _, emp, salaries = tpl
        is_senior = any(w in titles[0].lower() for w in ("senior", "lead", "3+", "2-4", " ii"))
        count = 2 if is_senior else RNG.randint(*n_per_template)
        for _ in range(count):
            counter += 1
            company, blurb = RNG.choice(COMPANIES)
            title = RNG.choice(titles)
            location = RNG.choice(LOCATIONS)
            discovered = REFERENCE_DAY - timedelta(days=RNG.randint(0, 29))
            r = RNG.random()
            deadline = None if r < 0.45 else discovered + timedelta(days=RNG.randint(-20, 50))
            salary = RNG.choice(salaries)
            extra = RNG.sample(optional_skills, k=RNG.randint(0, 2))
            desc = make_description(company, blurb, tpl, [s for s in extra if s not in skills], location, deadline, salary)
            raw = {
                "title": title,
                "company": company,
                "location": location,
                "description": desc,
                "apply_url": f"https://example.com/sample-jobs/{slug(company)}/{slug(title)}-{counter:03d}",
                "employment_hint": emp,
                "discovered_at": f"{discovered.isoformat()}T09:00:00+00:00",
            }
            rec = build_job_record(raw, source="Sample dataset (fictional)", source_type="sample", data_mode="sample")
            jobs.append(rec)
    unique, removed = deduplicate(jobs)  # same company + title + location drawn twice
    if removed:
        print(f"Removed {removed} generated duplicate(s)")
    return [r.to_dict() for r in unique]


def main() -> None:
    jobs = generate()
    payload = {
        "dataset": "SAMPLE — fictional companies and jobs for offline demonstration only",
        "generated_by": "scripts/generate_sample_data.py (random seed 42)",
        "reference_date": REFERENCE_DAY.isoformat(),
        "record_count": len(jobs),
        "jobs": jobs,
    }
    settings.SAMPLE_JOBS_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    settings.SAMPLE_JOBS_CSV.write_bytes(to_csv_bytes(pd.DataFrame(jobs)))
    print(f"Wrote {len(jobs)} sample jobs to {settings.SAMPLE_JOBS_JSON.name} and {settings.SAMPLE_JOBS_CSV.name}")


if __name__ == "__main__":
    main()
