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

## Layout

One folder per stage (`stage1/`, `stage2/`, ...). Each project gets its own subfolder with a short README saying what it does and how I measured it.

## Notes

- Large files (datasets, model weights, checkpoints) stay out of git; see `.gitignore`.
- Python virtual environment: `python -m venv .venv`, then `.venv\Scripts\activate`.
