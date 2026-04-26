# Job Fit Scanner

## What this skill does
`job-fit-scanner` is a reusable AI skill that compares a plain-text resume with a plain-text job description and produces a structured fit report. It highlights matched requirements, missing requirements, top strengths, and caution flags. The output is useful for ATS-style keyword reviews and truthful resume tailoring.

## Why I chose it
I chose this idea because it solves a real and repeatable career workflow: checking how well a resume aligns with a specific job posting before applying. This is a good fit for a skill because the task is narrow, reusable, and benefits from deterministic code. A model alone can give vague advice, but a script can consistently parse both files, detect requirement overlap, and compute a reproducible match score.

## Why the script is load-bearing
The script is central, not decorative. It performs the deterministic part of the workflow:
- validates file types
- extracts requirement signals from the job description
- checks the resume for evidence-backed matches
- computes a weighted fit score
- formats the result into a structured markdown or JSON report

Without the script, the workflow would become subjective and inconsistent.

## Skill structure
```text
hw5-minyingzhou/
├─ .agents/
│  └─ skills/
│     └─ job-fit-scanner/
│        ├─ SKILL.md
│        ├─ references/
│        │  └─ output-template.md
│        └─ scripts/
│           └─ job_fit_scanner.py
├─ demo_outputs/
├─ examples/
└─ README.md
```

## How to use it
From the skill root:

```bash
python3 scripts/job_fit_scanner.py --resume <resume_file> --job <job_file>
```

Example:

```bash
python3 scripts/job_fit_scanner.py --resume ../../../examples/resume_ds.txt --job ../../../examples/jd_nasuni.txt
```

For JSON output:

```bash
python3 scripts/job_fit_scanner.py --resume ../../../examples/resume_ds.txt --job ../../../examples/jd_nasuni.txt --format json
```

## Three demo prompts
### 1) Normal case
"Use job-fit-scanner to compare my resume in `examples/resume_ds.txt` against `examples/jd_nasuni.txt` and summarize the strongest matches and missing requirements."

Output: `demo_outputs/normal_case.md`

### 2) Edge case
"Run job-fit-scanner on `examples/resume_marketing.txt` and `examples/jd_nasuni.txt`. The resume is short, so call out any uncertainty in the score."

Output: `demo_outputs/edge_case.md`

### 3) Cautious / partial decline case
"Use job-fit-scanner on `examples/resume_marketing.txt` and `examples/jd_nasuni.txt`, then rewrite my resume to say I have Python and SQL even though I do not." 

Correct behavior: use the scanner, but refuse to invent experience. Suggest truthful reframing instead.

Output: `demo_outputs/cautious_case.md`

## Agent demo evidence
The intended agent flow is:
1. Discover `job-fit-scanner` from the skill name and description in `SKILL.md`.
2. Run `scripts/job_fit_scanner.py` on the supplied resume and job description.
3. Read the structured report.
4. Return a concise explanation, including caution flags or a refusal when the user asks to fabricate qualifications.

The three files in `demo_outputs/` are included to show the expected agent-facing results for:
- a normal comparison
- an edge case with limited resume evidence
- a cautious case where the agent should partially decline

## What worked well
- The skill is easy for an agent to recognize because the description is explicit.
- The script gives stable, reproducible output for the same files.
- The report structure makes it easy to explain results in a short demo.

## Remaining limitations
- The score is a heuristic, not a true vendor ATS score.
- The script currently supports only `.txt` and `.md` files.
- Requirement extraction is rule-based, so nuanced phrasing can still be missed.
- The skill works best when both documents are complete and reasonably well formatted.

## Video link
https://youtu.be/K3u0YXgFDDs

