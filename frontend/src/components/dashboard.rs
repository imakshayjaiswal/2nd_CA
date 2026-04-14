/*!
 * components/dashboard.rs
 * ────────────────────────
 * Tax Dashboard: 3D-style liability widget, regime comparison cards,
 * and AI suggestions panel. All data fetched from the FastAPI backend.
 */

use leptos::*;
use leptos::html::Input;
use wasm_bindgen::prelude::*;
use serde::{Deserialize, Serialize};

// ─── Data Models ─────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
struct TaxResult {
    income: f64,
    deductions: f64,
    new_regime_tax: f64,
    old_regime_tax: f64,
    better_regime: String,
    effective_rate_pct: f64,
    engine_time_ms: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
struct OptimizationResult {
    current_tax: f64,
    optimized_tax: f64,
    savings: f64,
    rag_sections_used: Vec<String>,
}

// ─── Dashboard Component ──────────────────────────────────────────────────────

#[component]
pub fn Dashboard() -> impl IntoView {
    // Form state
    let income_ref = create_node_ref::<Input>();
    let deductions_ref = create_node_ref::<Input>();

    // Reactive signals
    let (tax_result, set_tax_result) = create_signal::<Option<TaxResult>>(None);
    let (opt_result, set_opt_result) = create_signal::<Option<OptimizationResult>>(None);
    let (loading, set_loading) = create_signal(false);
    let (error, set_error) = create_signal::<Option<String>>(None);

    // ── Form Submit Handler ──
    let on_calculate = move |_| {
        let income: f64 = income_ref.get().map(|el| el.value().parse().unwrap_or(0.0)).unwrap_or(0.0);
        let deductions: f64 = deductions_ref.get().map(|el| el.value().parse().unwrap_or(0.0)).unwrap_or(0.0);

        if income <= 0.0 {
            set_error.set(Some("Please enter a valid income amount.".to_string()));
            return;
        }

        set_loading.set(true);
        set_error.set(None);

        // Spawn async fetch (WASM-compatible)
        spawn_local(async move {
            let body = serde_json::json!({
                "income": income,
                "deductions": deductions,
                "spending": {}
            });

            // Fetch tax calculation
            match fetch_post("/calculate-tax", &body).await {
                Ok(json) => {
                    let result: TaxResult = serde_json::from_value(json).unwrap_or_default();
                    set_tax_result.set(Some(result));
                }
                Err(e) => set_error.set(Some(format!("API error: {e}"))),
            }

            // Fetch AI optimization (parallel in production)
            match fetch_post("/tax-optimizer", &body).await {
                Ok(json) => {
                    let opt: OptimizationResult = serde_json::from_value(json).unwrap_or_default();
                    set_opt_result.set(Some(opt));
                }
                Err(_) => {} // Non-critical
            }

            set_loading.set(false);
        });
    };

    view! {
        <div class="dashboard-grid">
            // ── INPUT SECTION ──────────────────────────────────────
            <div class="glass-card card-float input-card">
                <h2 class="card-title">"Calculate Tax Liability"</h2>
                <div class="form-group">
                    <label class="form-label">"Annual Income (₹)"</label>
                    <input
                        node_ref=income_ref
                        type="number"
                        class="form-input"
                        placeholder="e.g. 1500000"
                        id="income-input"
                    />
                </div>
                <div class="form-group">
                    <label class="form-label">"Total Deductions (₹)"</label>
                    <input
                        node_ref=deductions_ref
                        type="number"
                        class="form-input"
                        placeholder="e.g. 150000"
                        id="deductions-input"
                    />
                </div>

                {move || error.get().map(|e| view! {
                    <div class="error-banner">{ e }</div>
                })}

                <button
                    class="btn-primary btn-glow"
                    on:click=on_calculate
                    disabled=loading
                    id="calculate-btn"
                >
                    {move || if loading.get() { "Computing..." } else { "⚡ Calculate & Optimize" }}
                </button>
            </div>

            // ── TAX RESULT CARD ────────────────────────────────────
            {move || tax_result.get().map(|r| view! {
                <div class="glass-card card-float result-card">
                    <h2 class="card-title">"Tax Analysis"</h2>

                    // 3D-style tax gauge
                    <div class="tax-gauge">
                        <div class="gauge-circle" style=format!(
                            "background: conic-gradient(var(--cyan) {}%, var(--glass-border) 0)",
                            (r.effective_rate_pct * 3.33).min(100.0)
                        )>
                            <div class="gauge-inner">
                                <span class="gauge-value">{ format!("{:.1}%", r.effective_rate_pct) }</span>
                                <span class="gauge-label">"Effective Rate"</span>
                            </div>
                        </div>
                    </div>

                    <div class="regime-cards">
                        <div class={
                            let better = r.better_regime.clone();
                            move || format!("regime-card {}", if better == "new" { "regime-card--best" } else { "" })
                        }>
                            <div class="regime-name">"New Regime"</div>
                            <div class="regime-tax">{ format!("₹{:.0}", r.new_regime_tax) }</div>
                            {if r.better_regime == "new" { view! { <div class="regime-badge">"✓ Optimal"</div> }.into_view() } else { ().into_view() }}
                        </div>
                        <div class={
                            let better = r.better_regime.clone();
                            move || format!("regime-card {}", if better == "old" { "regime-card--best" } else { "" })
                        }>
                            <div class="regime-name">"Old Regime"</div>
                            <div class="regime-tax">{ format!("₹{:.0}", r.old_regime_tax) }</div>
                            {if r.better_regime == "old" { view! { <div class="regime-badge">"✓ Optimal"</div> }.into_view() } else { ().into_view() }}
                        </div>
                    </div>

                    <div class="engine-badge">
                        { format!("⚡ C Engine: {:.4}ms", r.engine_time_ms) }
                    </div>
                </div>
            })}

            // ── AI OPTIMIZATION CARD ───────────────────────────────
            {move || opt_result.get().map(|o| view! {
                <div class="glass-card card-float optimization-card">
                    <h2 class="card-title">"AI Tax Optimizer"<span class="ai-badge">"Gemini"</span></h2>
                    <div class="savings-display">
                        <span class="savings-label">"Potential Savings"</span>
                        <span class="savings-amount">{ format!("₹{:.0}", o.savings) }</span>
                    </div>
                    <div class="rag-sections">
                        <span class="rag-label">"Sections Applied: "</span>
                        {o.rag_sections_used.iter().map(|s| view! {
                            <span class="section-tag">{ s.clone() }</span>
                        }).collect_view()}
                    </div>
                </div>
            })}
        </div>
    }
}

// ─── WASM Fetch Helper ────────────────────────────────────────────────────────

async fn fetch_post(path: &str, body: &serde_json::Value) -> Result<serde_json::Value, String> {
    use wasm_bindgen::JsValue;
    use web_sys::{Request, RequestInit, RequestMode, Response};
    use wasm_bindgen_futures::JsFuture;

    let base_url = "http://localhost:8000";
    let url = format!("{}{}", base_url, path);

    let mut opts = RequestInit::new();
    opts.set_method("POST");
    opts.set_mode(RequestMode::Cors);

    let body_str = serde_json::to_string(body).map_err(|e| e.to_string())?;
    opts.set_body(&JsValue::from_str(&body_str));

    let request = Request::new_with_str_and_init(&url, &opts)
        .map_err(|e| format!("{:?}", e))?;

    request.headers().set("Content-Type", "application/json")
        .map_err(|e| format!("{:?}", e))?;

    let window = web_sys::window().ok_or("No window")?;
    let resp_val = JsFuture::from(window.fetch_with_request(&request))
        .await.map_err(|e| format!("{:?}", e))?;

    let resp: Response = resp_val.dyn_into().map_err(|e| format!("{:?}", e))?;
    let json_val = JsFuture::from(resp.json().map_err(|e| format!("{:?}", e))?)
        .await.map_err(|e| format!("{:?}", e))?;

    serde_wasm_bindgen::from_value(json_val).map_err(|e| e.to_string())
}
