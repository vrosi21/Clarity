"""NLP / semantic layer for Clarity's ML pipeline.

Provides:
- SemanticEncoder: text → embedding (all-MiniLM-L6-v2, 384-dim)
- skill_match: cosine similarity in [0, 1] between worker and task embeddings
- task_to_text / worker_to_text: structured data → embeddable text
- sim_worker_to_text: bridge from SimWorker.category_proficiency to NLP layer
- RidgeComplexityPredictor: embedding → complexity bucket 1–5
"""

from app.ml.nlp.complexity_predictor import BaseComplexityPredictor, RidgeComplexityPredictor
from app.ml.nlp.encoder import SemanticEncoder
from app.ml.nlp.skill_match import skill_match
from app.ml.nlp.task_text import task_to_text
from app.ml.nlp.worker_text import sim_worker_to_text, worker_to_text

__all__ = [
    "BaseComplexityPredictor",
    "RidgeComplexityPredictor",
    "SemanticEncoder",
    "skill_match",
    "sim_worker_to_text",
    "task_to_text",
    "worker_to_text",
]
