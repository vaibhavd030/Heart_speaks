import os
import sys
from typing import Any

# Ensure src in path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src"))
)

import json

from datasets import Dataset
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas import evaluate
from ragas.metrics import (
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)

from heart_speaks.config import settings
from heart_speaks.graph import app

# Define 5 Q&A pairs related to spiritual messages
eval_dataset = [
    {
        "question": "What is the true nature of the self according to the messages?",
        "ground_truth": "The true nature of the self is pure consciousness and eternal peace, detachment from material struggles.",
    },
    {
        "question": "How can one achieve inner peace?",
        "ground_truth": "Through meditation, selfless action, and surrendering attachments to the ego.",
    },
    {
        "question": "What is the meaning of karma?",
        "ground_truth": "Karma refers to the cycle of action and reaction, where selfless deeds liberate but selfish deeds bind.",
    },
    {
        "question": "Why is meditation important?",
        "ground_truth": "It quiets the restless mind, allowing one to connect with their inner divine essence.",
    },
    {
        "question": "What is the role of compassion in spiritual growth?",
        "ground_truth": "Compassion dissolves the barrier between self and others, which is fundamentally an illusion.",
    },
]


def load_dataset() -> Any:
    dataset_path = os.path.join(os.path.dirname(__file__), "eval_dataset.json")
    if os.path.exists(dataset_path):
        with open(dataset_path) as f:
            return json.load(f)
    print("Using default small dataset. Generate more using generate_dataset.py.")
    return eval_dataset


def generate_answers_for_eval() -> Dataset:
    data: dict[str, list[Any]] = {
        "user_input": [],
        "response": [],
        "retrieved_contexts": [],
        "reference": [],
    }

    current_dataset = load_dataset()
    for item in current_dataset:
        q = item["question"]
        inputs = {"messages": [HumanMessage(content=q)]}
        result = app.invoke(inputs)  # type: ignore

        final_resp = result.get("final_response", {})
        answer = final_resp.get("answer", "No answer generated.")

        # graph state returns context as List[str]
        contexts = result.get("context", [])

        data["user_input"].append(q)
        data["response"].append(answer)
        data["retrieved_contexts"].append(contexts)
        data["reference"].append(item["ground_truth"])

    return Dataset.from_dict(data)


def run_ragas_evaluation() -> None:
    print("Generating answers for evaluation dataset...")
    dataset = generate_answers_for_eval()

    from pydantic import SecretStr

    eval_llm = ChatOpenAI(model="gpt-4o", api_key=SecretStr(settings.openai_api_key))
    eval_embeddings = OpenAIEmbeddings(api_key=SecretStr(settings.openai_api_key))

    print("Running Ragas evaluation...")
    result = evaluate(
        dataset,
        metrics=[AnswerRelevancy(), Faithfulness(), ContextPrecision(), ContextRecall()],  # type: ignore
        llm=eval_llm,
        embeddings=eval_embeddings,
    )

    print("Evaluation Results:")
    print(result)

    os.makedirs("logs", exist_ok=True)
    df = result.to_pandas()  # type: ignore
    df.to_csv("logs/eval_metrics.csv", index=False)
    print("Saved detailed metrics to logs/eval_metrics.csv")

    # Enforce strict thresholds from improvement.md
    thresholds = {
        "context_precision": 0.75,
        "context_recall": 0.75,
        "faithfulness": 0.85,
        "answer_relevancy": 0.80,
    }

    failed = False
    print("\n--- Threshold Check ---")

    # Extract overall metrics from the result object (Ragas 0.1.x compatible)
    # result behaves like a dictionary of aggregated scores
    for metric_name, required_score in thresholds.items():
        # Handle the new Ragas metric class names mapping (e.g. answer_relevancy)
        actual_score = 0.0

        # In ragas 0.1.0, result acts like a mapped dict with object names
        # Let's read from the pandas dataframe as a fallback which has predictable naming
        if metric_name in df.columns:
            actual_score = df[metric_name].mean()
        else:
            # Ragas 0.1.0 metrics might have the exact class name or slightly different formatting
            for col in df.columns:
                if (
                    metric_name.lower() in col.lower()
                    or col.lower() in metric_name.lower()
                ):
                    actual_score = df[col].mean()
                    break

        status = "✅ PASS" if actual_score >= required_score else "❌ FAIL"
        print(
            f"{metric_name}: {actual_score:.3f} (Required: {required_score}) -> {status}"
        )

        if actual_score < required_score:
            failed = True

    if failed:
        print(
            "\nERROR: One or more evaluation metrics failed to meet the strict thresholds!"
        )
        sys.exit(1)
    else:
        print("\nSUCCESS: All evaluation metrics met the required thresholds.")


if __name__ == "__main__":
    if "OPENAI_API_KEY" not in os.environ:
        print(
            "Please set OPENAI_API_KEY environment variable. Assuming loaded through .env by config"
        )

    run_ragas_evaluation()
