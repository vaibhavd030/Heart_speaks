import json
import os
import random
import sys

from loguru import logger
from pydantic import BaseModel, Field

# Ensure src in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from heart_speaks.config import settings
from heart_speaks.ingest import get_vector_store
from typing import Any


class QAPair(BaseModel):
    question: str = Field(description="A question that can be fully answered using ONLY the provided text.")
    ground_truth: str = Field(description="The correct answer to the question based ONLY on the provided text.")

def generate_synthetic_dataset(num_questions: int = 50, output_file: str = "eval_dataset.json") -> None:
    vectorstore = get_vector_store()
    
    # Try to get existing documents
    try:
        data = vectorstore.get()
        docs = data.get("documents", [])
    except Exception as e:
        logger.error(f"Failed to fetch documents from Chroma: {e}")
        return
        
    if not docs:
        logger.error("No documents found in the vector store. Run `make ingest` first.")
        return
        
    logger.info(f"Found {len(docs)} chunks in the vector store. Sampling for dataset generation...")
    
    # Sample chunks randomly
    num_samples = min(num_questions, len(docs))
    sampled_docs = random.sample(docs, num_samples)
    
    from pydantic import SecretStr
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, api_key=SecretStr(settings.openai_api_key))
    structured_llm = llm.with_structured_output(QAPair)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert at creating evaluation datasets for a RAG chatbot. "
                   "Given a chunk of spiritual text, generate exactly one Question and Answer pair. "
                   "The question must be self-contained and answerable ONLY using the text. "
                   "The answer should be comprehensive but concise."),
        ("human", "Text chunk: \n\n{text}")
    ])
    
    chain = prompt | structured_llm
    
    dataset = []
    
    # Check if existing dataset to append or overwrite
    output_path = os.path.join(os.path.dirname(__file__), output_file)
    if os.path.exists(output_path):
        with open(output_path) as f:
            try:
                dataset = json.load(f)
                logger.info(f"Loaded {len(dataset)} existing questions from {output_file}")
            except json.JSONDecodeError:
                pass
                
    generated_count = 0
    logger.info(f"Generating {num_questions} new questions...")
    
    for i, doc in enumerate(sampled_docs):
        try:
            qa_result: Any = chain.invoke({"text": doc})
            qa: QAPair = qa_result
            dataset.append({
                "question": qa.question,
                "ground_truth": qa.ground_truth
            })
            generated_count += 1
            print(f"Generated {generated_count}/{num_samples}")
        except Exception as e:
            logger.warning(f"Failed to generate QA for chunk {i}: {e}")
            
    # Save the updated dataset
    with open(output_path, "w") as f:
        json.dump(dataset, f, indent=4)
        
    logger.info(f"Successfully added {generated_count} questions. Total dataset size: {len(dataset)}. Saved to {output_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate synthetic evaluation dataset")
    parser.add_argument("--num", type=int, default=5, help="Number of questions to generate")
    args = parser.parse_args()
    
    generate_synthetic_dataset(num_questions=args.num)
