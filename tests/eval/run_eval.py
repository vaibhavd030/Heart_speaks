import os
import sys

# Ensure src in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from datasets import Dataset
from langchain_core.messages import HumanMessage
from ragas import evaluate
from ragas.metrics import answer_relevancy, faithfulness

from heart_speaks.graph import app

# Define 5 Q&A pairs related to spiritual messages
eval_dataset = [
    {
        "question": "What is the true nature of the self according to the messages?",
        "ground_truth": "The true nature of the self is pure consciousness and eternal peace, detachment from material struggles."
    },
    {
        "question": "How can one achieve inner peace?",
        "ground_truth": "Through meditation, selfless action, and surrendering attachments to the ego."
    },
    {
        "question": "What is the meaning of karma?",
        "ground_truth": "Karma refers to the cycle of action and reaction, where selfless deeds liberate but selfish deeds bind."
    },
    {
        "question": "Why is meditation important?",
        "ground_truth": "It quiets the restless mind, allowing one to connect with their inner divine essence."
    },
    {
        "question": "What is the role of compassion in spiritual growth?",
        "ground_truth": "Compassion dissolves the barrier between self and others, which is fundamentally an illusion."
    }
]

def generate_answers_for_eval():
    data = {"question": [], "answer": [], "contexts": [], "ground_truth": []}
    
    for item in eval_dataset:
        q = item["question"]
        inputs = {"messages": [HumanMessage(content=q)]}
        result = app.invoke(inputs)
        
        final_resp = result.get("final_response", {})
        answer = final_resp.get("answer", "No answer generated.")
        
        # graph state returns context as List[str]
        contexts = result.get("context", [])
        
        data["question"].append(q)
        data["answer"].append(answer)
        data["contexts"].append(contexts)
        data["ground_truth"].append(item["ground_truth"])
        
    return Dataset.from_dict(data)

def run_ragas_evaluation():
    print("Generating answers for evaluation dataset...")
    dataset = generate_answers_for_eval()
    
    print("Running Ragas evaluation...")
    result = evaluate(
        dataset,
        metrics=[answer_relevancy, faithfulness],
    )
    
    print("Evaluation Results:")
    print(result)
    
    os.makedirs("logs", exist_ok=True)
    df = result.to_pandas()
    df.to_csv("logs/eval_metrics.csv", index=False)
    print("Saved detailed metrics to logs/eval_metrics.csv")

if __name__ == "__main__":
    if "OPENAI_API_KEY" not in os.environ:
        print("Please set OPENAI_API_KEY environment variable. Assuming loaded through .env by config")
        
    run_ragas_evaluation()
