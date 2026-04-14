/*!
 * AeroTax Frontend — main.rs (Leptos + WebAssembly)
 * ===================================================
 * Entry point for the Leptos SPA. Mounts the root App component into the DOM.
 *
 * Build & Run:
 *   cargo install trunk
 *   trunk serve --open
 *
 * The `index.html` in frontend/ must include:
 *   <link data-trunk rel="rust" />
 *   <link data-trunk rel="css" href="styles/aerotax.css" />
 */

use leptos::*;
use leptos_meta::*;
use leptos_router::*;

mod components;
use components::{
    dashboard::Dashboard,
    audit_stream::AuditStream,
    upload_zone::UploadZone,
    nav_bar::NavBar,
};

// ─── Main Entry Point ────────────────────────────────────────────────────────

fn main() {
    // Initialize WASM panic hook for better error messages in browser console
    console_error_panic_hook::set_once();

    // Mount the Leptos app into the <body> element
    leptos::mount_to_body(|| view! { <App /> });
}

// ─── Root Application Component ──────────────────────────────────────────────

#[component]
pub fn App() -> impl IntoView {
    // Provide metadata context (for <title>, <meta> tags)
    provide_meta_context();

    view! {
        // SEO metadata
        <Title text="AeroTax — AI-Powered CA Alternative"/>
        <Meta name="description" content="AeroTax: Instant AI tax optimization, audit detection, and invoice processing for India — powered by Gemini AI and real-time C computation."/>

        // Leptos Router for SPA navigation
        <Router>
            <div class="aerotax-shell">
                // ── Navigation ──
                <NavBar />

                // ── Route Views ──
                <main class="main-content">
                    <Routes>
                        <Route path="/"         view=DashboardPage />
                        <Route path="/audit"    view=AuditPage />
                        <Route path="/upload"   view=UploadPage />
                        <Route path="/*any"     view=NotFound />
                    </Routes>
                </main>
            </div>
        </Router>
    }
}

// ─── Page Wrapper Components ──────────────────────────────────────────────────

#[component]
fn DashboardPage() -> impl IntoView {
    view! {
        <div class="page-container fade-in">
            <header class="hero-section">
                <div class="hero-badge">
                    <span class="status-dot"></span>
                    <span>"Next-Gen Tax Intelligence Live"</span>
                </div>
                <h1 class="glow-text">"Future of Tax" <br/> "Optimization"</h1>
                <p class="subtitle">"Harness the power of AI and real-time C-computation to minimize your liability and maximize your savings."</p>
            </header>
            <Dashboard />
        </div>
    }
}

#[component]
fn AuditPage() -> impl IntoView {
    view! {
        <div class="page-container fade-in">
            <div class="page-header">
                <h1 class="glow-text">"AuditStream"</h1>
                <p class="subtitle">"Live ledger monitoring — AI flags anomalies in real-time"</p>
            </div>
            <AuditStream />
        </div>
    }
}

#[component]
fn UploadPage() -> impl IntoView {
    view! {
        <div class="page-container fade-in">
            <div class="page-header">
                <h1 class="glow-text">"Invoice Upload"</h1>
                <p class="subtitle">"WASM-compressed uploads — process invoices at the edge"</p>
            </div>
            <UploadZone />
        </div>
    }
}

#[component]
fn NotFound() -> impl IntoView {
    view! {
        <div class="page-container fade-in" style="text-align:center; padding-top:10rem;">
            <h1 class="glow-text">"404"</h1>
            <p class="subtitle">"This tax break doesn't exist."</p>
            <a href="/" class="btn-primary">"Return to Dashboard"</a>
        </div>
    }
}
