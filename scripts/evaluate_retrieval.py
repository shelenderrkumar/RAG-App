"""Evaluate retrieval quality on a small labelled question set.

For each question in data/eval_questions.json we check whether the retrieved chunks
(top-k) come from the expected page and contain the expected answer span, and report
hit rate @k and mean reciprocal rank (MRR). Compare chunking settings with flags:

    python scripts/evaluate_retrieval.py --chunk-size 800 --overlap 120 --k 4
    python scripts/evaluate_retrieval.py --chunk-size 300 --overlap 50  --k 4

Each run also writes its metrics and per-question ranks to results/ as JSON.
"""

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from langchain_openai import OpenAIEmbeddings

from ragchat.config import DATA_DIR, get_settings
from ragchat.knowledge_base import KnowledgeBase

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"


async def evaluate(chunk_size: int, overlap: int, k: int) -> None:
    settings = get_settings()
    kb = KnowledgeBase.build(
        DATA_DIR,
        OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.openai_api_key),
        index_dir=None,  # always rebuild so chunking settings take effect
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        top_k=k,
    )
    cases = json.loads((DATA_DIR / "eval_questions.json").read_text())
    page_hits = span_hits = 0
    reciprocal_ranks = []
    per_question = []
    for case in cases:
        docs = await kb.search(case["question"])
        ranks = [
            rank
            for rank, doc in enumerate(docs, start=1)
            if case["answer_contains"].lower() in " ".join(doc.page_content.split()).lower()
        ]
        page_hits += any(d.metadata.get("page") == case["expected_page"] for d in docs)
        span_hits += bool(ranks)
        reciprocal_ranks.append(1 / ranks[0] if ranks else 0.0)
        per_question.append(
            {
                "question": case["question"],
                "answer_rank": ranks[0] if ranks else None,
                "page_hit": any(d.metadata.get("page") == case["expected_page"] for d in docs),
            }
        )
        status = f"rank {ranks[0]}" if ranks else "MISS"
        print(f"  [{status:>6}] {case['question']}")

    n = len(cases)
    print(f"\nchunk_size={chunk_size} overlap={overlap} k={k} questions={n}")
    print(f"  page hit rate@{k}:   {page_hits / n:.2f}")
    print(f"  answer hit rate@{k}: {span_hits / n:.2f}")
    print(f"  MRR:                {sum(reciprocal_ranks) / n:.2f}")
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"retrieval_chunk{chunk_size}_overlap{overlap}_k{k}.json"
    out.write_text(
        json.dumps(
            {
                "settings": {
                    "chunk_size": chunk_size,
                    "overlap": overlap,
                    "k": k,
                    "embedding_model": settings.embedding_model,
                },
                "questions": n,
                "page_hit_rate": page_hits / n,
                "answer_hit_rate": span_hits / n,
                "mrr": sum(reciprocal_ranks) / n,
                "per_question": per_question,
                "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            },
            indent=2,
        )
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunk-size", type=int, default=800)
    parser.add_argument("--overlap", type=int, default=120)
    parser.add_argument("--k", type=int, default=4)
    args = parser.parse_args()
    asyncio.run(evaluate(args.chunk_size, args.overlap, args.k))
