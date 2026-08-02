# Taxor - Evaluation of Multimodal LLMs for Handwritten Bill Extraction

This repository contains the screening task for the Software Engineering Internship at Taxor.

## Project Location

The complete codebase, dataset, evaluation framework, and dashboard are located inside the subfolder:
👉 **[taxor-handwritten-bill-extraction/](file:///c:/Users/G15/Desktop/taxorr/taxorr/taxor-handwritten-bill-extraction)**

## Quick Start Instructions

To run the project locally, navigate to the project directory and follow these steps:

1. **Navigate to project directory:**
   ```bash
   cd taxor-handwritten-bill-extraction
   ```

2. **Create a virtual environment & install requirements:**
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Mac/Linux:
   source venv/bin/activate
   
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Copy `.env.example` to `.env` and fill in API keys if you want live extractions.
   *(Note: The framework defaults to high-fidelity mocks if keys are missing so it's fully testable out of the box!)*
   ```bash
   copy .env.example .env
   ```

4. **Run the Streamlit Dashboard UI:**
   ```bash
   streamlit run ui/app.py
   ```

5. **Run Batch Benchmarking CLI:**
   ```bash
   python main.py --run-eval
   ```

For detailed documentation, evaluation reports, and design choices, please refer to the project [README.md](file:///c:/Users/G15/Desktop/taxorr/taxorr/taxor-handwritten-bill-extraction/README.md) and [evaluation_report.md](file:///c:/Users/G15/Desktop/taxorr/taxorr/taxor-handwritten-bill-extraction/outputs/evaluation_report.md).
