import os
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Tuple
from models import get_llm_client

def fuzzy_ratio(s1: str, s2: str) -> float:
    """Computes a simple Levenshtein-based fuzzy match score between two strings (0.0 to 1.0)."""
    # Normalize alphanumeric chars only
    s1 = "".join(c for c in s1.lower() if c.isalnum() or c.isspace()).strip()
    s2 = "".join(c for c in s2.lower() if c.isalnum() or c.isspace()).strip()
    
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
        
    # Build DP table for edit distance
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
        
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i-1] == s2[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + 1)
                
    distance = dp[m][n]
    max_len = max(len(s1), len(s2))
    return 1.0 - (distance / max_len)

def normalize_date(date_str: str) -> str:
    """Normalizes typical Indian bill date formats to YYYY-MM-DD."""
    if not date_str or str(date_str).lower() in ["n/a", "na", "none", "null"]:
        return "N/A"
    
    date_str = str(date_str).strip()
    
    # Try YYYY-MM-DD or YYYY/MM/DD
    match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", date_str)
    if match:
        return f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
        
    # Try DD-MM-YYYY or DD/MM/YYYY
    match = re.search(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", date_str)
    if match:
        return f"{match.group(3)}-{int(match.group(2)):02d}-{int(match.group(1)):02d}"
        
    # Try textual months (e.g. 18-July-2026, 18 July 2026, July 18 2026)
    months = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }
    match = re.search(r"(\d{1,2})[-/\s]+([A-Za-z]{3,10})[-/\s]+(\d{4})", date_str)
    if match:
        day = int(match.group(1))
        month_name = match.group(2).lower()[:3]
        year = match.group(3)
        if month_name in months:
            return f"{year}-{months[month_name]:02d}-{day:02d}"
            
    # Try reverse textual month (July 18 2026)
    match = re.search(r"([A-Za-z]{3,10})[-/\s]+(\d{1,2})[-/\s]+(\d{4})", date_str)
    if match:
        month_name = match.group(1).lower()[:3]
        day = int(match.group(2))
        year = match.group(3)
        if month_name in months:
            return f"{year}-{months[month_name]:02d}-{day:02d}"
            
    return date_str.lower()

def is_field_correct(field_name: str, extracted: Any, ground_truth: Any) -> Tuple[bool, float]:
    """
    Compares the extracted value to the ground truth value.
    Returns (is_correct, score_out_of_1).
    """
    if str(ground_truth).strip().lower() in ["n/a", "na", "none"] and str(extracted).strip().lower() in ["n/a", "na", "none", ""]:
        return True, 1.0
        
    if field_name == "amount":
        try:
            val_ext = float(extracted)
            val_gt = float(ground_truth)
            # Accept within 0.05 margin (small cents/rounding errors)
            correct = abs(val_ext - val_gt) < 0.05
            score = 1.0 if correct else 0.0
            return correct, score
        except ValueError:
            return False, 0.0
            
    elif field_name == "date":
        norm_ext = normalize_date(str(extracted))
        norm_gt = normalize_date(str(ground_truth))
        correct = norm_ext == norm_gt
        return correct, 1.0 if correct else 0.0
        
    elif field_name == "currency":
        correct = str(extracted).strip().upper() == str(ground_truth).strip().upper()
        return correct, 1.0 if correct else 0.0
        
    else:
        # String matching for vendor_name, invoice_number, tax_details
        score = fuzzy_ratio(str(extracted), str(ground_truth))
        # Threshold: 80% similarity is considered correct
        return score >= 0.80, score


class BillEvaluator:
    def __init__(self, dataset_dir: str):
        self.dataset_dir = dataset_dir
        self.gt_path = os.path.join(dataset_dir, "ground_truth.json")
        self.images_dir = os.path.join(dataset_dir, "images")
        
        with open(self.gt_path, "r") as f:
            self.ground_truth = json.load(f)

    def evaluate_model(self, model_name: str) -> Dict[str, Any]:
        """Runs the entire dataset through a specific model and evaluates accuracy and cost."""
        client = get_llm_client(model_name)
        results = []
        
        total_fields = 0
        correct_fields = 0
        field_accuracies = {
            "vendor_name": {"correct": 0, "total": 0},
            "invoice_number": {"correct": 0, "total": 0},
            "date": {"correct": 0, "total": 0},
            "amount": {"correct": 0, "total": 0},
            "currency": {"correct": 0, "total": 0},
            "tax_details": {"correct": 0, "total": 0}
        }
        
        total_cost = 0.0
        total_latency = 0.0
        is_mock_run = True
        
        for filename, gt_val in self.ground_truth.items():
            image_path = os.path.join(self.images_dir, filename)
            if not os.path.exists(image_path):
                continue
                
            # Perform extraction
            extracted, metadata = client.extract_expense(image_path)
            
            # Update metrics
            total_cost += metadata.get("cost", 0.0)
            total_latency += metadata.get("latency", 0.0)
            if not metadata.get("is_mock", False):
                is_mock_run = False
                
            bill_fields_correct = 0
            bill_fields_total = len(field_accuracies)
            
            bill_results = {}
            for field in field_accuracies.keys():
                ext_val = getattr(extracted, field, "N/A")
                gt_val_field = gt_val.get(field, "N/A")
                
                correct, score = is_field_correct(field, ext_val, gt_val_field)
                
                field_accuracies[field]["total"] += 1
                if correct:
                    field_accuracies[field]["correct"] += 1
                    correct_fields += 1
                    bill_fields_correct += 1
                    
                total_fields += 1
                bill_results[field] = {
                    "extracted": ext_val,
                    "ground_truth": gt_val_field,
                    "correct": correct,
                    "score": score
                }
                
            results.append({
                "filename": filename,
                "fields": bill_results,
                "accuracy": bill_fields_correct / bill_fields_total,
                "latency": metadata.get("latency", 0.0),
                "cost": metadata.get("cost", 0.0)
            })
            
        # Calculate summary accuracies
        overall_accuracy = correct_fields / total_fields if total_fields > 0 else 0.0
        field_accuracy_pct = {}
        for f, count in field_accuracies.items():
            field_accuracy_pct[f] = count["correct"] / count["total"] if count["total"] > 0 else 0.0
            
        num_bills = len(results)
        avg_latency = total_latency / num_bills if num_bills > 0 else 0.0
        avg_cost = total_cost / num_bills if num_bills > 0 else 0.0
        
        return {
            "model_name": model_name,
            "overall_accuracy": overall_accuracy,
            "field_accuracies": field_accuracy_pct,
            "total_cost": total_cost,
            "avg_cost_per_bill": avg_cost,
            "extrapolated_cost_100_bills": avg_cost * 100,
            "avg_latency": avg_latency,
            "is_mock": is_mock_run,
            "results": results
        }

    def generate_report(self, eval_results: List[Dict[str, Any]]) -> str:
        """Generates a comparison Markdown report of all evaluated models."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report = []
        report.append("# Model Evaluation Report - Handwritten Bill Extraction")
        report.append(f"*Generated at: {timestamp}*\n")
        
        # Summary table
        report.append("## Overview Comparison")
        report.append("| Model | Overall Accuracy | Avg Latency (s) | Avg Cost / Bill | Cost per 100 Bills | Run Type |")
        report.append("|---|---|---|---|---|---|")
        for res in eval_results:
            run_type = "Mock" if res["is_mock"] else "Live API"
            report.append(
                f"| **{res['model_name']}** | {res['overall_accuracy']:.2%} | {res['avg_latency']:.2f}s | "
                f"${res['avg_cost_per_bill']:.5f} | ${res['extrapolated_cost_100_bills']:.3f} | {run_type} |"
            )
        report.append("")
        
        # Field-level accuracy table
        report.append("## Field-Level Accuracy Comparison")
        fields = ["vendor_name", "invoice_number", "date", "amount", "currency", "tax_details"]
        headers = ["Model"] + [f.replace("_", " ").title() for f in fields]
        report.append("| " + " | ".join(headers) + " |")
        report.append("|" + "|".join(["---"] * len(headers)) + "|")
        for res in eval_results:
            row = [f"**{res['model_name']}**"]
            for f in fields:
                row.append(f"{res['field_accuracies'].get(f, 0.0):.1%}")
            report.append("| " + " | ".join(row) + " |")
        report.append("")
        
        # Detailed feedback / methodology
        report.append("## Evaluation Methodology & Correctness Criteria")
        report.append("1. **Vendor Name**: String similarity score using Levenshtein distance normalized (threshold: >= 80%).")
        report.append("2. **Invoice Number**: Text comparison after trimming spaces/symbols. Case-insensitive.")
        report.append("3. **Date**: Normalizes Indian dates (e.g. DD-MM-YYYY, DD/MM/YYYY, DD-Month-YYYY) to standard ISO format (`YYYY-MM-DD`) before exact matching.")
        report.append("4. **Amount**: Floating-point comparison (difference < 0.05 is correct).")
        report.append("5. **Currency**: Exact case-insensitive match (e.g. INR).")
        report.append("6. **Tax Details**: Fuzzy string matching (threshold: >= 80%). If ground truth is N/A and extracted is N/A/empty, it counts as correct.")
        
        return "\n".join(report)
