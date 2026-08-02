import streamlit as st
import os
import json
import pandas as pd
from PIL import Image
from datetime import datetime
from dotenv import load_dotenv

# Load env variables at startup (override=True ensures latest .env values are always used)
load_dotenv(override=True)

# Local imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import get_llm_client
from evaluator.evaluator import BillEvaluator, is_field_correct, normalize_date
from zoho.zoho_client import ZohoBooksClient

# Set up page configurations for a premium feel
st.set_page_config(
    page_title="Taxor - Handwritten Bill Extraction",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
        color: #1E293B;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        font-size: 1.1rem;
        color: #64748B;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .success-text {
        color: #10B981;
        font-weight: 600;
    }
    .fail-text {
        color: #EF4444;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session States
if "eval_results" not in st.session_state:
    st.session_state.eval_results = None

# Sidebar Content
st.sidebar.image("https://img.icons8.com/color/96/bill.png", width=60)
st.sidebar.markdown("### **Taxor Extraction Engine**")
st.sidebar.markdown("Evaluate multimodal LLMs on handwritten bills and export directly to Zoho Books.")

st.sidebar.divider()

# Check Environment API Keys
keys = {
    "Gemini API": os.environ.get("GEMINI_API_KEY", ""),
    "OpenAI API": os.environ.get("OPENAI_API_KEY", ""),
    "Claude API": os.environ.get("ANTHROPIC_API_KEY", ""),
    "Groq API": os.environ.get("GROQ_API_KEY", ""),
    "Zoho Client ID": os.environ.get("ZOHO_CLIENT_ID", ""),
}

st.sidebar.markdown("#### **API Connection Status**")
for key_name, value in keys.items():
    if value and "your_" not in value:
        st.sidebar.markdown(f"🟢 **{key_name}**: Configured")
    else:
        st.sidebar.markdown(f"🟡 **{key_name}**: Mock Mode")

st.sidebar.info("💡 Placeholders detected in `.env`. Live APIs will automatically fallback to high-fidelity mocks to showcase framework functionalities.")

st.sidebar.divider()

# Main Application Structure
st.markdown("<div class='main-title'>🧾 Taxor: Bill Extraction & Model Evaluator</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Handwritten Bill Extraction, Model Benchmarking, and Zoho Books Syncing.</div>", unsafe_allow_html=True)

# Define Tabs
tab1, tab2 = st.tabs(["⚡ Single Bill Extraction & Sync", "📊 Batch Benchmark & Analytics"])

# Setup Paths
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dataset_dir = os.path.join(workspace_dir, "dataset")
images_dir = os.path.join(dataset_dir, "images")

# Load Ground Truth
try:
    with open(os.path.join(dataset_dir, "ground_truth.json"), "r") as f:
        ground_truth = json.load(f)
except Exception:
    st.error("Ground truth file dataset/ground_truth.json not found.")
    ground_truth = {}

# --- TAB 1: SINGLE BILL EXTRACTION & SYNC ---
with tab1:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### **Select / Upload Bill**")
        
        # Select dataset bill
        bill_options = list(ground_truth.keys())
        selected_filename = st.selectbox("Choose a dataset bill", bill_options)
        
        # File uploader for custom bills
        uploaded_file = st.file_uploader("Or upload your own handwritten receipt", type=["png", "jpg", "jpeg"])
        
        # Determine image to show and process
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            temp_image_path = os.path.join(images_dir, f"temp_{uploaded_file.name}")
            image.save(temp_image_path)
            active_image_path = temp_image_path
            active_filename = uploaded_file.name
            gt_data = None
        else:
            active_image_path = os.path.join(images_dir, selected_filename)
            active_filename = selected_filename
            gt_data = ground_truth.get(selected_filename)
            if os.path.exists(active_image_path):
                image = Image.open(active_image_path)
            else:
                image = None
                st.warning(f"Image {selected_filename} not found in dataset/images/")

        if image:
            st.image(image, caption=active_filename, use_container_width=True)

    with col2:
        st.markdown("### **Extraction Comparison**")
        
        # Selection of models to compare
        models_to_run = st.multiselect(
    "Select models for processing",
    [
        "gemini-1.5-flash",
        "gpt-4o-mini",
        "claude-3-5-sonnet",
        "llama-3.3-70b-versatile"
    ],
    default=[
        "gemini-1.5-flash",
        "gpt-4o-mini",
        "llama-3.3-70b-versatile"
    ]
)
        run_extraction = st.button("🚀 Process Bill")
        
        extracted_results = {}
        
        if run_extraction:
            if not models_to_run:
                st.error("Please select at least one model.")
            else:
                with st.spinner("Analyzing handwriting with multimodal vision..."):
                    for model in models_to_run:
                        client = get_llm_client(model)
                        exp, meta = client.extract_expense(active_image_path)
                        extracted_results[model] = (exp, meta)
                
                st.success("Analysis complete!")
                
                # Render Comparison Table
                st.markdown("#### **Field Comparison**")
                comparison_rows = []
                
                fields = ["vendor_name", "invoice_number", "date", "amount", "currency", "tax_details"]
                
                for field in fields:
                    row = {"Field": field.replace("_", " ").title()}
                    
                    if gt_data:
                        row["Ground Truth"] = gt_data.get(field, "N/A")
                    else:
                        row["Ground Truth"] = "N/A (Uploaded)"
                        
                    for model in models_to_run:
                        exp, meta = extracted_results[model]
                        val = getattr(exp, field)
                        
                        # Add indicator icons
                        if gt_data:
                            correct, _ = is_field_correct(field, val, gt_data.get(field))
                            icon = "🟢" if correct else "🔴"
                            row[f"{model}"] = f"{icon} {val}"
                        else:
                            row[f"{model}"] = f"{val}"
                            
                    comparison_rows.append(row)
                    
                df_comparison = pd.DataFrame(comparison_rows)
                st.table(df_comparison)
                
                # Show Latency / Cost info
                st.markdown("#### **Performance Metrics**")
                metric_cols = st.columns(len(models_to_run))
                for i, model in enumerate(models_to_run):
                    exp, meta = extracted_results[model]
                    with metric_cols[i]:
                        st.markdown(f"**{model}**")
                        st.markdown(f"- Latency: `{meta.get('latency', 0.0):.2f}s`")
                        st.markdown(f"- API Cost: `${meta.get('cost', 0.0):.5f}`")
                        st.markdown(f"- Tokens Used: `in: {meta.get('tokens_input', 0)}, out: {meta.get('tokens_output', 0)}`")
                
                # Cache results for Zoho Books export
                st.session_state.last_extraction = {
                    "bill": active_filename,
                    "models": extracted_results
                }

        # --- ZOHO BOOKS INTEGRATION SECTION ---
        st.divider()
        st.markdown("### **Sync to Zoho Books**")
        
        if "last_extraction" in st.session_state:
            cached = st.session_state.last_extraction
            st.info(f"Syncing extracted data from bill: `{cached['bill']}`")
            
            # Select model output to use for Zoho
            available_models = list(cached["models"].keys())
            selected_model = st.selectbox("Select model output to use for Zoho Books", available_models)
            
            # Retrieve values
            chosen_expense, _ = cached["models"][selected_model]
            
            # Initialize Zoho Client
            zoho_client = ZohoBooksClient()
            
            # Fetch Org & Accounts dynamically
            orgs = zoho_client.get_organizations()
            
            if not orgs:
                st.warning("No Zoho organizations available. Mock settings will be used.")
                org_options = {"mock_org": "Mock Organization"}
            else:
                org_options = {o["organization_id"]: o["name"] for o in orgs}
                
            selected_org_id = st.selectbox("Select Zoho Organization", list(org_options.keys()), format_func=lambda x: org_options[x])
            
            accounts = zoho_client.get_expense_accounts(selected_org_id)
            if not accounts:
                account_options = {"mock_acc": "Mock Expense Account"}
            else:
                account_options = {a["account_id"]: a["account_name"] for a in accounts}
                
            selected_acc_id = st.selectbox("Select Expense Account", list(account_options.keys()), format_func=lambda x: account_options[x])
            
            # Form to edit fields before sending
            col_form_1, col_form_2 = st.columns(2)
            with col_form_1:
                form_vendor = st.text_input("Vendor Name", chosen_expense.vendor_name)
                form_amount = st.number_input("Amount", value=float(chosen_expense.amount), min_value=0.0)
            with col_form_2:
                form_date = st.text_input("Date (YYYY-MM-DD)", normalize_date(chosen_expense.date))
                form_desc = st.text_input("Description", f"Handwritten bill extraction via {selected_model}")
                
            # Submit to Zoho button
            if st.button("💳 Export to Zoho Books"):
                with st.spinner("Syncing with Zoho Books API..."):
                    resp = zoho_client.create_expense(
                        organization_id=selected_org_id,
                        account_id=selected_acc_id,
                        amount=form_amount,
                        date=form_date,
                        vendor_name=form_vendor,
                        description=form_desc
                    )
                    
                if resp.get("success"):
                    st.balloons()
                    st.success(f"🎉 {resp.get('message')}")
                    st.json(resp.get("expense", {}))
                else:
                    st.error(f"❌ Failed to export: {resp.get('message')}")
                    if "details" in resp:
                        st.json(resp["details"])
        else:
            st.info("Process a bill above first to enable Zoho Books syncing.")

# --- TAB 2: BATCH BENCHMARK & ANALYTICS ---
with tab2:
    st.markdown("### **Batch Evaluation Benchmark**")
    st.markdown("Run the entire dataset of handwritten bills through the selected models to benchmark field accuracies and token costs.")
    
    eval_models = st.multiselect(
    "Benchmarking models",
    [
        "gemini-1.5-flash",
        "gpt-4o-mini",
        "claude-3-5-sonnet",
        "llama-3.3-70b-versatile"
    ],
    default=[
        "gemini-1.5-flash",
        "gpt-4o-mini",
        "claude-3-5-sonnet",
        "llama-3.3-70b-versatile"
    ]
)
    
    run_eval_btn = st.button("📊 Run Batch Evaluation")
    
    if run_eval_btn:
        evaluator = BillEvaluator(dataset_dir)
        eval_results = []
        
        progress_bar = st.progress(0.0)
        for idx, model in enumerate(eval_models):
            st.write(f"Evaluating `{model}`...")
            res = evaluator.evaluate_model(model)
            eval_results.append(res)
            progress_bar.progress((idx + 1) / len(eval_models))
            
        st.session_state.eval_results = eval_results
        st.success("Batch benchmarking complete!")
        
    if st.session_state.eval_results is not None:
        results = st.session_state.eval_results
        
        # Overview Cards
        st.markdown("#### **Performance Benchmarks**")
        
        card_cols = st.columns(len(results))
        for idx, r in enumerate(results):
            with card_cols[idx]:
                st.markdown(f"""
                <div class="metric-card">
                    <h4><b>{r['model_name']}</b></h4>
                    <p>Overall Accuracy: <span class="success-text">{r['overall_accuracy']:.1%}</span></p>
                    <p>Avg Latency: <b>{r['avg_latency']:.2f}s</b></p>
                    <p>Avg Cost/Bill: <b>${r['avg_cost_per_bill']:.5f}</b></p>
                    <p>Cost / 100 Bills: <b>${r['extrapolated_cost_100_bills']:.3f}</b></p>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("#### **Accuracy Comparison Chart**")
        # Build DataFrame for charts
        acc_dict = {
            "Model": [r["model_name"] for r in results],
            "Overall Accuracy": [r["overall_accuracy"] for r in results]
        }
        df_acc = pd.DataFrame(acc_dict).set_index("Model")
        st.bar_chart(df_acc)
        
        # Field Level Breakdown Table
        st.markdown("#### **Field-Level Accuracies**")
        field_rows = []
        for r in results:
            row = {"Model": r["model_name"]}
            row.update({k.replace("_", " ").title(): v for k, v in r["field_accuracies"].items()})
            field_rows.append(row)
        st.table(pd.DataFrame(field_rows).set_index("Model"))
        
        # Save evaluation report file
        st.divider()
        st.markdown("#### **Generated Evaluation Report**")
        evaluator = BillEvaluator(dataset_dir)
        report_md = evaluator.generate_report(results)
        
        st.markdown(report_md)
        
        # Save to outputs folder
        outputs_dir = os.path.join(workspace_dir, "outputs")
        os.makedirs(outputs_dir, exist_ok=True)
        with open(os.path.join(outputs_dir, "evaluation_report.md"), "w") as f:
            f.write(report_md)
        st.success(f"Report exported to [outputs/evaluation_report.md](file:///{outputs_dir.replace('\\', '/')}/evaluation_report.md)")
