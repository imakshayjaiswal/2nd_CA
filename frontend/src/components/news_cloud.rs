use leptos::*;

#[component]
pub fn NewsCloud() -> impl IntoView {
    // Generate mock "real-time" timestamps relative to now
    let news_items = vec![
        ("Bloomberg", "Verified", "10 mins ago", "RBI maintains status quo on repo rate at 6.5%, signals stable inflation trajectory."),
        ("Reuters", "Verified", "25 mins ago", "Tax authorities consider revising the 80C deduction limit to ₹2.5 Lakh ahead of upcoming budget."),
        ("Financial Express", "Verified", "1 hr ago", "GST Council proposes restructuring of tax slabs over next two fiscal quarters."),
        ("Mint", "Verified", "2 hrs ago", "Startups gain massive traction as new Angel Tax abolishment takes full effect."),
        ("CNBC", "Verified", "3 hrs ago", "Global tech rally pushes major indices to new highs, buoying local retail investment."),
        ("Economic Times", "Verified", "4 hrs ago", "Corporate tax collections surpass estimates by 15% in Q1 2026."),
    ];

    view! {
        <div class="news-cloud-container">
            <h2 class="cloud-title">"Live Market Intelligence"</h2>
            <div class="news-cloud-grid">
                {news_items.into_iter().map(|(source, status, time, headline)| {
                    view! {
                        <div class="news-card">
                            <div class="news-meta">
                                <span class="news-source">{ source }</span>
                                <span class="news-verified">"✓ " { status }</span>
                                <span class="news-time">{ time }</span>
                            </div>
                            <h3 class="news-headline">{ headline }</h3>
                            <button class="btn-source-link">"Read Full Report \u{2197}"</button>
                        </div>
                    }
                }).collect_view()}
            </div>
        </div>
    }
}
