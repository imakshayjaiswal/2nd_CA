use leptos::*;
use std::time::Duration;

#[component]
pub fn NewsCloud() -> impl IntoView {
    let all_news = vec![
        ("Bloomberg", "Verified", "Just Now", "RBI maintains status quo on repo rate at 6.5%, signals stable inflation trajectory."),
        ("Reuters", "Verified", "2 mins ago", "Tax authorities consider revising the 80C deduction limit to ₹2.5 Lakh ahead of upcoming budget."),
        ("Financial Express", "Verified", "10 mins ago", "GST Council proposes restructuring of tax slabs over next two fiscal quarters."),
        ("Mint", "Verified", "15 mins ago", "Startups gain massive traction as new Angel Tax abolishment takes full effect."),
        ("CNBC", "Verified", "22 mins ago", "Global tech rally pushes major indices to new highs, buoying local retail investment."),
        ("Economic Times", "Verified", "30 mins ago", "Corporate tax collections surpass estimates by 15% in Q1 2026."),
        ("Moneycontrol", "Verified", "45 mins ago", "Rupee stabilizes against the dollar following robust FII inflows this week."),
        ("NDTV Profit", "Verified", "1 hr ago", "Real estate sector sees 22% surge in housing sales due to favorable home loan rates."),
        ("Zee Business", "Verified", "2 hrs ago", "Mutual Fund SIP accounts cross a record 10 Crore milestone nationwide."),
        ("ET Now", "Verified", "3 hrs ago", "Electric vehicle subsidies heavily discussed for upcoming green-tax incentives.")
    ];

    let (news, set_news) = create_signal(all_news.clone());

    // Rotates the feed slightly every 10 minutes to simulate live updates
    set_interval_with_handle(move || {
        set_news.update(|n| {
            let first = n.remove(0);
            n.push(first);
        });
    }, Duration::from_secs(600)).unwrap();

    view! {
        <div class="news-cloud-container">
            <h2 class="cloud-title">"Live Market Intelligence"</h2>
            <div class="news-cloud-grid">
                {move || news.get().into_iter().take(6).map(|(source, status, time, headline)| {
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
