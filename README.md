# learning-ai

My build-first path from zero to AI engineering and training my own small LLM.

Plan: see `../LEARNING-PLAN.md` (based on the webridgeAI roadmap and LLM-from-scratch map).

| Stage | Topic | Project | Status |
|---|---|---|---|
| 0 | Workbench: Python, git, editor, WSL | This repo + `LEARNING.md` | in progress |
| 1 | Python + just enough maths | `stage1-*` script (e.g. spending chart from a CSV) | |
| 1.5 | CS50 AI (lectures in my NotebookLM) | CS50 AI projects (search, logic, ML, NN, language) | |
| 2 | ML foundations | Kaggle Titanic + model on my own data | |
| 3 | Deep learning by hand | micrograd, makemore, own PyTorch loop | |
| 4 | Transformers and my own LLM | Karpathy GPT, Raschka ch. 1–7, nanochat, a measured fine-tune | |
| 5 | AI applications | notes chat (RAG), 2-tool agent, eval harness, shipped app | |

## My AI Cohort (study app)

A small local web app (`study-app/`, FastAPI) over all my courses: CS50P, CS50 AI and AI Path 01 to 25.

- **Start:** double-click `Start Study.bat` (or the desktop shortcut). It opens http://localhost:8000.
- **Plays** today's video and **resumes** where I stopped.
- **Quiz me:** 5 questions from the course's NotebookLM notebook (needs `nlm` logged in).
- **Journal:** appends to `LEARNING.md`.
- **Finish for today:** commits and pushes everything to GitHub.
- Progress lives in `progress/`. To rebuild the course list: `python study-app/tools/build_catalog.py`.

## Layout

One folder per stage (`stage1/`, `stage2/`, ...). Each project gets its own subfolder with a short README saying what it does and how I measured it.

## Notes

- Large files (datasets, model weights, checkpoints) stay out of git; see `.gitignore`.
- Python virtual environment: `python -m venv .venv`, then `.venv\Scripts\activate`.
