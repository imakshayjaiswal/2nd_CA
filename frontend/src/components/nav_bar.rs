/*!
 * components/nav_bar.rs
 * ─────────────────────
 * Sticky glassmorphism navigation bar with AeroTax branding and animated links.
 */

use leptos::*;
use leptos_router::*;

#[component]
pub fn NavBar() -> impl IntoView {
    // Track which page is active for highlight effect
    let location = use_location();

    view! {
        <nav class="navbar glass-card">
            // ── Brand ──────────────────────────────────────────
            <div class="nav-brand">
                <div class="nav-logo">
                    <span class="logo-icon">"⚡"</span>
                    <span class="logo-text">"Aero"<span class="logo-accent">"Tax"</span></span>
                </div>
                <div class="nav-tagline">"AI-Powered CA"</div>
            </div>

            // ── Navigation Links ────────────────────────────────
            <ul class="nav-links">
                <li>
                    <A href="/" class="nav-link" active_class="nav-link--active">
                        <span class="nav-icon">"📊"</span>
                        <span>"Dashboard"</span>
                    </A>
                </li>
                <li>
                    <A href="/audit" class="nav-link" active_class="nav-link--active">
                        <span class="nav-icon">"🔍"</span>
                        <span>"AuditStream"</span>
                    </A>
                </li>
                <li>
                    <A href="/upload" class="nav-link" active_class="nav-link--active">
                        <span class="nav-icon">"📁"</span>
                        <span>"Upload"</span>
                    </A>
                </li>
            </ul>

            // ── Status Indicator ────────────────────────────────
            <div class="nav-status">
                <div class="status-dot status-dot--live"></div>
                <span class="status-text">"Engine Online"</span>
            </div>
        </nav>
    }
}
