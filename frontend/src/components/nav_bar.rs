/*!
 * components/nav_bar.rs
 * ─────────────────────
 * Sticky glassmorphism navigation bar with AeroTax branding and animated links.
 */

use leptos::*;
use leptos_router::*;

#[component]
pub fn NavBar() -> impl IntoView {
    let intel_news = vec![
        "🚨 80C limit update pending",
        "📊 Markets at record high",
        "💡 Tax deadline approaching",
        "📰 GST council meet today",
        "📈 Tech stocks rally continues",
        "🔔 New tax slab proposed",
        "💼 RBI holds repo rate",
        "🏦 Digital rupee surge"
    ];
    let (idx, set_idx) = create_signal(0);
    
    let intel_len = intel_news.len();

    set_interval_with_handle(move || {
        set_idx.update(|i| *i = (*i + 1) % intel_len);
    }, std::time::Duration::from_secs(60)).unwrap();

    let display_items = move || {
        let current = idx.get();
        vec![
            intel_news[current],
            intel_news[(current + 1) % intel_len],
            intel_news[(current + 2) % intel_len],
        ]
    };

    view! {
        <nav class="navbar glass-card">
            // ── Brand ──────────────────────────────────────────
            <div class="nav-brand">
                <div class="nav-logo">
                    <span class="logo-text">"Aero"<span class="logo-accent">"Tax"</span></span>
                </div>
                <div class="nav-tagline">"Tax Intelligence"</div>
            </div>

            // ── Navigation Links ────────────────────────────────
            <ul class="nav-links">
                <li>
                    <A href="/" class="nav-link" active_class="nav-link--active">
                        <span>"Dashboard"</span>
                    </A>
                </li>
                <li>
                    <A href="/audit" class="nav-link" active_class="nav-link--active">
                        <span>"Audit"</span>
                    </A>
                </li>
                <li>
                    <A href="/news" class="nav-link" active_class="nav-link--active">
                        <span>"Market Intel"</span>
                    </A>
                </li>
                <li>
                    <A href="/upload" class="nav-link" active_class="nav-link--active">
                        <span>"Upload"</span>
                    </A>
                </li>
            </ul>

            // ── Status Indicator ────────────────────────────────
            <div class="nav-status-group">
                <div class="nav-status">
                    <div class="status-dot status-dot--live"></div>
                    <span class="status-text">"Engine Online"</span>
                </div>
                <div class="nav-intel-cloud">
                    {move || display_items().into_iter().map(|item| {
                        view! { <span class="nav-intel-item">{ item }</span> }
                    }).collect_view()}
                </div>
            </div>
        </nav>
    }
}
