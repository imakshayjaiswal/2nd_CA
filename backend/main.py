"""
AeroTax Backend — main.py
==========================
FastAPI orchestrator that bridges the C calculation engine,
LLM-powered tax optimizer, and Vector DB RAG pipeline.

Run:
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000
"""

import os
import io
import ctypes
import platform
import csv
import time
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ──────────────────────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger("aerotax")

# ──────────────────────────────────────────────────────────────
# SECTION 1: LOAD C SHARED LIBRARY VIA CTYPES
# ──────────────────────────────────────────────────────────────
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
from engine_py import py_calculate_tax, py_detect_outliers, py_compare_regimes

log.info("✅ Python engine loaded (engine_py.py)")

# Compatibility wrapper so the rest of main.py is unchanged
def c_calculate_tax(income: float, deductions: float) -> float:
    return py_calculate_tax(income, deductions)

def c_detect_outliers(transactions: list, threshold: float):
    result = py_detect_outliers(transactions, threshold)
    return result["flags"], result["count"], result["mean"], result["std_dev"]




# ──────────────────────────────────────────────────────────────
# SECTION 2: VECTOR DB PLACEHOLDER (Pinecone RAG — Income Tax Act 1961)
# ──────────────────────────────────────────────────────────────
class TaxActRAG:
    """
    Placeholder for Pinecone + Sentence-Transformers RAG pipeline.
    In production: embed chunks of Income Tax Act 1961 → store in Pinecone
    → query with user's financial context → inject into LLM prompt.
    """

    # Mock knowledge base — replace with real Pinecone index
    MOCK_SECTIONS = {
        "80C":  "Deductions up to ₹1.5L for ELSS, PPF, LIC, NSC, tuition fees.",
        "80D":  "Medical insurance premium: ₹25,000 (self) + ₹50,000 (parents 60+).",
        "80E":  "Interest on education loan — no upper limit, 8 years.",
        "80G":  "Donations to approved funds: 50%-100% deduction.",
        "24B":  "Home loan interest deduction up to ₹2L for self-occupied property.",
        "10(14)": "HRA exemption based on actual rent, salary, and city.",
        "87A":  "Full tax rebate if taxable income ≤ ₹7L (new regime) / ₹5L (old).",
    }

    def query(self, user_context: str, top_k: int = 3) -> list[dict]:
        """
        Mock RAG query. Replace with:
            import pinecone
            index = pinecone.Index("income-tax-act")
            results = index.query(vector=embed(user_context), top_k=top_k)
        """
        log.info("🔍 RAG query (mock): %s", user_context[:80])
        # Naive keyword match for demo
        relevant = []
        for section, text in self.MOCK_SECTIONS.items():
            if any(kw in user_context.lower() for kw in ["insurance", "education", "home", "donate", "hra", "elss", "ppf"]):
                relevant.append({"section": section, "text": text, "score": 0.92})
        return relevant[:top_k] if relevant else list(
            {"section": k, "text": v, "score": 0.70} for k, v in
            list(self.MOCK_SECTIONS.items())[:top_k]
        )


rag = TaxActRAG()


# ──────────────────────────────────────────────────────────────
# SECTION 3: LLM CLIENT PLACEHOLDER (Gemini 1.5 Pro)
# ──────────────────────────────────────────────────────────────
class GeminiClient:
    """
    Mock Gemini 1.5 Pro integration.

    In production, replace with:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel("gemini-1.5-pro-latest")
        response = model.generate_content(prompt)
    """

    def analyze_tax(self, income: float, spending: dict, rag_context: list[dict]) -> dict:
        """Generates tax optimization suggestions using LLM + RAG context."""
        # Build RAG-enriched prompt
        context_str = "\n".join(
            f"  - Section {r['section']}: {r['text']}" for r in rag_context
        )
        prompt = f"""
        You are AeroTax AI, an expert Indian CA. Analyze the following:
        Income: ₹{income:,.0f}
        Spending Categories: {spending}
        Relevant Tax Sections:
        {context_str}
        Provide specific, actionable deduction strategies in JSON format.
        """
        log.info("🤖 LLM call (MOCK): prompt length=%d chars", len(prompt))

        # ── MOCK RESPONSE (replace with real API call) ──
        return {
            "model": "gemini-1.5-pro-latest (mock)",
            "suggestions": [
                {
                    "section": "80C",
                    "action": "Invest ₹1,50,000 in ELSS mutual funds",
                    "max_saving": round(income * 0.30 * 0.04, 2),
                    "priority": "HIGH",
                },
                {
                    "section": "80D",
                    "action": "Buy health insurance plan covering self + family",
                    "max_saving": round(25000 * 0.30, 2),
                    "priority": "HIGH",
                },
                {
                    "section": "24B",
                    "action": "Consider home loan: deduct up to ₹2L on interest",
                    "max_saving": 60000.0,
                    "priority": "MEDIUM",
                },
            ],
            "effective_tax_rate_before": f"{(income * 0.15):.1f}%",
            "projected_savings": 95_000,
        }


gemini = GeminiClient()


# ──────────────────────────────────────────────────────────────
# SECTION 4: PYDANTIC SCHEMAS
# ──────────────────────────────────────────────────────────────
class TaxRequest(BaseModel):
    income: float = Field(..., gt=0, description="Gross annual income in INR")
    deductions: float = Field(0.0, ge=0, description="Total claimed deductions")
    spending: dict = Field(default_factory=dict, description="Category → amount map")


class RegimeCompareRequest(BaseModel):
    income: float = Field(..., gt=0)
    deductions: float = Field(0.0, ge=0)


class AnomalyRequest(BaseModel):
    transactions: list[float] = Field(..., min_items=1)
    threshold: float = Field(3.0, gt=0, description="Z-score threshold (default=3)")


# ──────────────────────────────────────────────────────────────
# SECTION 5: FASTAPI APP
# ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="AeroTax API",
    description="AI-powered CA alternative — FastAPI + C Engine + Gemini RAG",
    version="1.0.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────
# SECTION 6: HELPER — C ENGINE CALLS
# ──────────────────────────────────────────────────────────────
def c_calculate_tax(income: float, deductions: float) -> float:
    """Calls C engine; falls back to Python implementation if unavailable."""
    if ENGINE:
        return ENGINE.py_calculate_tax(income, deductions)
    # Python fallback (simplified)
    log.warning("Using Python fallback for tax calculation")
    taxable = max(0.0, income - deductions - 75000)
    if taxable <= 700000:
        return 0.0
    if taxable <= 1500000:
        return taxable * 0.20 * 1.04
    return (taxable * 0.30) * 1.04


def c_detect_outliers(transactions: list[float], threshold: float):
    """Calls C engine for Z-score anomaly detection."""
    size = len(transactions)
    arr   = (ctypes.c_double * size)(*transactions)
    flags = (ctypes.c_int    * size)()
    mean  = ctypes.c_double(0.0)
    std   = ctypes.c_double(0.0)

    if ENGINE:
        count = ENGINE.py_detect_outliers(arr, size, threshold, flags, ctypes.byref(mean), ctypes.byref(std))
        return list(flags), count, mean.value, std.value

    # Python NumPy fallback
    log.warning("Using NumPy fallback for outlier detection")
    arr_np = np.array(transactions)
    m, s   = arr_np.mean(), arr_np.std()
    flag_list = [1 if abs(x - m) / (s + 1e-9) > threshold else 0 for x in transactions]
    return flag_list, sum(flag_list), float(m), float(s)


# ──────────────────────────────────────────────────────────────
# SECTION 7: ENDPOINTS
# ──────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "🚀 AeroTax API Online",
        "engine": "C-native" if ENGINE else "Python-fallback",
        "version": "1.0.0",
    }


@app.post("/calculate-tax", tags=["Tax Engine"])
async def calculate_tax(req: TaxRequest):
    """
    Calculates tax liability using the C engine (Indian New Tax Regime).
    Returns tax amount, effective rate, and regime comparison.
    """
    t0 = time.perf_counter()

    new_tax = c_calculate_tax(req.income, req.deductions)

    # Old regime comparison
    old_new = ctypes.c_double(0.0)
    old_old = ctypes.c_double(0.0)
    if ENGINE:
        ENGINE.py_compare_regimes(req.income, req.deductions,
                                   ctypes.byref(old_new), ctypes.byref(old_old))
        old_tax = old_old.value
    else:
        old_tax = c_calculate_tax(req.income, req.deductions * 0.8)  # rough fallback

    elapsed_ms = (time.perf_counter() - t0) * 1000

    return {
        "income": req.income,
        "deductions": req.deductions,
        "new_regime_tax": round(new_tax, 2),
        "old_regime_tax": round(old_tax, 2),
        "better_regime": "new" if new_tax <= old_tax else "old",
        "effective_rate_pct": round(new_tax / req.income * 100, 2),
        "engine_time_ms": round(elapsed_ms, 4),
    }


@app.post("/analyze-ledger", tags=["Audit Engine"])
async def analyze_ledger(file: UploadFile = File(...)):
    """
    Accepts a CSV file with a 'amount' column.
    Passes data to the C engine for statistical anomaly detection.
    Returns flagged transactions with Z-scores.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only CSV files are accepted.")

    content = await file.read()
    try:
        df = pd.read_csv(io.StringIO(content.decode("utf-8")))
    except Exception as e:
        raise HTTPException(400, f"CSV parse error: {e}")

    if "amount" not in df.columns:
        raise HTTPException(400, "CSV must contain an 'amount' column.")

    transactions = df["amount"].dropna().tolist()
    if len(transactions) < 3:
        raise HTTPException(400, "Need at least 3 transactions for analysis.")

    flags, count, mean, std = c_detect_outliers(transactions, threshold=3.0)

    flagged = []
    for i, (tx, flag) in enumerate(zip(transactions, flags)):
        z = abs(tx - mean) / (std + 1e-9)
        if flag:
            row = df.iloc[i].to_dict()
            row["z_score"] = round(z, 4)
            row["anomaly"] = True
            flagged.append(row)

    return {
        "total_transactions": len(transactions),
        "anomalies_found": count,
        "mean": round(mean, 2),
        "std_dev": round(std, 2),
        "flagged": flagged,
        "engine": "C-native" if ENGINE else "numpy-fallback",
    }


@app.post("/tax-optimizer", tags=["AI Advisor"])
async def tax_optimizer(req: TaxRequest):
    """
    LLM + RAG powered tax optimization.
    Queries the Income Tax Act vector DB, then calls Gemini 1.5 Pro
    to generate personalized deduction strategies.
    """
    # Step 1: RAG — retrieve relevant tax sections
    user_context = f"Income: {req.income}, Spending: {req.spending}"
    rag_results = rag.query(user_context, top_k=4)

    # Step 2: LLM analysis
    suggestions = gemini.analyze_tax(req.income, req.spending, rag_results)

    # Step 3: Calculate current vs projected tax
    current_tax = c_calculate_tax(req.income, req.deductions)
    projected_savings = suggestions.get("projected_savings", 0)
    optimized_tax = max(0, current_tax - projected_savings)

    return {
        "current_tax": round(current_tax, 2),
        "optimized_tax": round(optimized_tax, 2),
        "savings": round(current_tax - optimized_tax, 2),
        "rag_sections_used": [r["section"] for r in rag_results],
        "ai_suggestions": suggestions,
    }


@app.post("/detect-anomalies", tags=["Audit Engine"])
async def detect_anomalies(req: AnomalyRequest):
    """
    Raw JSON endpoint for transaction anomaly detection.
    Useful for real-time AuditStream in the frontend.
    """
    flags, count, mean, std = c_detect_outliers(req.transactions, req.threshold)
    results = []
    for i, (tx, flag) in enumerate(zip(req.transactions, flags)):
        z = abs(tx - mean) / (std + 1e-9)
        results.append({
            "index": i,
            "amount": tx,
            "z_score": round(z, 4),
            "flagged": bool(flag),
        })

    return {
        "summary": {"mean": round(mean, 2), "std_dev": round(std, 2), "anomalies": count},
        "transactions": results,
    }
