import os
import argparse
import json
from dotenv import load_dotenv

# Local imports
from models import get_llm_client
from evaluator.evaluator import BillEvaluator

def main():
    # Load environment variables from .env
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Taxor Handwritten Bill Extraction Pipeline")
    parser.add_argument("--run-eval", action="store_true", help="Run batch evaluation over the dataset for all models")
    parser.add_argument("--image", type=str, help="Path to a single receipt image to extract details from")
    parser.add_argument("--model", type=str, default="gemini-1.5-flash", help="Model to use for single extraction")
    
    args = parser.parse_args()
    
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_dir = os.path.join(workspace_dir, "dataset")
    
    if args.run_eval:
        print("Starting batch evaluation over dataset...")
        evaluator = BillEvaluator(dataset_dir)
        models = ["gemini-1.5-flash", "gpt-4o-mini", "claude-3-5-sonnet"]
        
        results = []
        for model in models:
            print(f"Evaluating {model}...")
            res = evaluator.evaluate_model(model)
            results.append(res)
            
        report_md = evaluator.generate_report(results)
        
        outputs_dir = os.path.join(workspace_dir, "outputs")
        os.makedirs(outputs_dir, exist_ok=True)
        report_path = os.path.join(outputs_dir, "evaluation_report.md")
        
        with open(report_path, "w") as f:
            f.write(report_md)
            
        print(f"\nBatch evaluation completed! Report written to: {report_path}")
        print("\nOverview Summary:")
        for res in results:
            print(f"- {res['model_name']}: Accuracy = {res['overall_accuracy']:.2%}, Avg Latency = {res['avg_latency']:.2f}s, Avg Cost = ${res['avg_cost_per_bill']:.5f}")
            
    elif args.image:
        if not os.path.exists(args.image):
            print(f"Error: Image path '{args.image}' does not exist.")
            return
            
        print(f"Running extraction on '{args.image}' using model '{args.model}'...")
        client = get_llm_client(args.model)
        expense, metadata = client.extract_expense(args.image)
        
        print("\nExtracted Details:")
        print(json.dumps(expense.model_dump(), indent=2))
        print("\nRun Metadata:")
        print(json.dumps(metadata, indent=2))
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
