/*!
 * components/audit_stream.rs
 * ───────────────────────────
 * Real-time ledger feed. Transactions float in with CSS animations.
 * Anomalies are highlighted red by the AI engine.
 */

use leptos::*;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Transaction {
    index: usize,
    amount: f64,
    z_score: f64,
    flagged: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct AuditSummary {
    mean: f64,
    std_dev: f64,
    anomalies: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
struct AuditResponse {
    summary: Option<AuditSummary>,
    transactions: Vec<Transaction>,
}

#[component]
pub fn AuditStream() -> impl IntoView {
    let (transactions, set_transactions) = create_signal::<Vec<Transaction>>(vec![]);
    let (summary, set_summary) = create_signal::<Option<AuditSummary>>(None);
    let (loading, set_loading) = create_signal(false);
    let (raw_input, set_raw_input) = create_signal(String::new());

    // ── Demo data button ──
    let load_demo = move |_| {
        let demo = vec![
            100.0, 95.0, 110.0, 105.0, 98.0, 102.0, 99.0,
            850.0,  // ANOMALY
            103.0, 97.0, 5.0,  // ANOMALY
            101.0, 104.0, 99.0,
        ];
        set_raw_input.set(demo.iter().map(|x| x.to_string()).collect::<Vec<_>>().join(","));
    };

    // ── Run analysis ──
    let on_analyze = move |_| {
        let input = raw_input.get();
        let transactions_raw: Vec<f64> = input
            .split(',')
            .filter_map(|s| s.trim().parse().ok())
            .collect();

        if transactions_raw.is_empty() {
            return;
        }

        set_loading.set(true);
        spawn_local(async move {
            let body = serde_json::json!({
                "transactions": transactions_raw,
                "threshold": 3.0
            });

            // Simple fetch for demo
            let response = gloo_net::http::Request::post("http://localhost:8000/detect-anomalies")
                .header("Content-Type", "application/json")
                .body(serde_json::to_string(&body).unwrap())
                .unwrap()
                .send()
                .await;

            if let Ok(resp) = response {
                if let Ok(data) = resp.json::<serde_json::Value>().await {
                    // Parse transactions
                    if let Some(txns) = data["transactions"].as_array() {
                        let parsed: Vec<Transaction> = txns.iter().filter_map(|t| {
                            Some(Transaction {
                                index: t["index"].as_u64()? as usize,
                                amount: t["amount"].as_f64()?,
                                z_score: t["z_score"].as_f64()?,
                                flagged: t["flagged"].as_bool()?,
                            })
                        }).collect();
                        set_transactions.set(parsed);
                    }
                    if let Some(s) = data["summary"].as_object() {
                        set_summary.set(Some(AuditSummary {
                            mean: s["mean"].as_f64().unwrap_or(0.0),
                            std_dev: s["std_dev"].as_f64().unwrap_or(0.0),
                            anomalies: s["anomalies"].as_i64().unwrap_or(0) as i32,
                        }));
                    }
                }
            }
            set_loading.set(false);
        });
    };

    view! {
        <div class="audit-container">
            // ── Controls ──────────────────────────────────────────
            <div class="glass-card card-float audit-controls">
                <h3 class="card-title">"Transaction Input"</h3>
                <textarea
                    class="audit-textarea"
                    placeholder="Enter comma-separated amounts, e.g: 100, 105, 98, 850, 102"
                    id="transaction-input"
                    prop:value=raw_input
                    on:input=move |e| set_raw_input.set(event_target_value(&e))
                />
                <div class="btn-group">
                    <button class="btn-secondary" on:click=load_demo id="demo-btn">
                        "📂 Load Demo Data"
                    </button>
                    <button class="btn-primary btn-glow" on:click=on_analyze
                        disabled=loading id="analyze-btn">
                        {move || if loading.get() { "Analyzing..." } else { "🔍 Run AI Audit" }}
                    </button>
                </div>
            </div>

            // ── Summary Stats ─────────────────────────────────────
            {move || summary.get().map(|s| view! {
                <div class="audit-stats-row">
                    <div class="glass-card stat-card">
                        <div class="stat-label">"Mean"</div>
                        <div class="stat-value">{ format!("₹{:.2}", s.mean) }</div>
                    </div>
                    <div class="glass-card stat-card">
                        <div class="stat-label">"Std Deviation"</div>
                        <div class="stat-value">{ format!("₹{:.2}", s.std_dev) }</div>
                    </div>
                    <div class="glass-card stat-card stat-card--alert">
                        <div class="stat-label">"Anomalies"</div>
                        <div class="stat-value">{ s.anomalies }</div>
                    </div>
                </div>
            })}

            // ── Transaction Feed ──────────────────────────────────
            <div class="audit-feed glass-card">
                <h3 class="card-title">"Live Ledger Stream"</h3>
                {move || {
                    let txns = transactions.get();
                    if txns.is_empty() {
                        return view! {
                            <div class="audit-empty">
                                <span>"🔄 Awaiting transaction data..."</span>
                            </div>
                        }.into_view();
                    }
                    txns.into_iter().map(|tx| {
                        let flagged = tx.flagged;
                        view! {
                            <div class=move || format!("tx-row tx-float {}",
                                if flagged { "tx-row--anomaly" } else { "" })>
                                <div class="tx-index">{ format!("#{:03}", tx.index + 1) }</div>
                                <div class="tx-amount">{ format!("₹{:.2}", tx.amount) }</div>
                                <div class="tx-zscore">{ format!("z={:.2}", tx.z_score) }</div>
                                <div class="tx-flag">
                                    {if flagged {
                                        view! { <span class="flag-badge">"⚠ FLAGGED"</span> }.into_view()
                                    } else {
                                        view! { <span class="ok-badge">"✓"</span> }.into_view()
                                    }}
                                </div>
                            </div>
                        }
                    }).collect_view().into_view()
                }}
            </div>
        </div>
    }
}
