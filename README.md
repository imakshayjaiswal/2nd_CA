# ⚡ AeroTax — AI-Powered Indian Tax optimization

AeroTax is a high-performance, AI-driven tax optimization and audit detection platform designed for the Indian tax ecosystem. It combines a fast C-based calculation engine with a modern Rust/WASM frontend to provide instant, real-time insights into tax savings and compliance.

![AeroTax Banner](https://raw.githubusercontent.com/imakshayjaiswal/2nd_CA/main/frontend/assets/banner.png) *(Note: Placeholder image link)*

## 🚀 Key Features

- **Instant Tax Optimization**: Real-time calculation of tax liabilities across different regimes.
- **AI Audit Detection**: Detect potential anomalies and audit flags in your invoices and filings.
- **Rust/WASM Frontend**: Blazing fast, client-side calculations for a seamless UX.
- **C-Native Engine**: Core tax logic implemented in C for maximum precision and speed.
- **Invoice Processing**: Automated extraction and analysis of tax relevant data from invoices.

## 🛠️ Architecture

- **Backend**: FastAPI (Python) for API orchestration and AI integration.
- **Engine**: A custom C library for high-speed tax computations.
- **Frontend**: Built with Rust and the Leptos framework, compiled to WASM.
- **Deployment**: Configured for GitHub Pages (Frontend) and Render (Backend).

## 📦 Installation & Setup

### Prerequisites
- Python 3.9+
- Rust & Trunk (for frontend)
- C Compiler (GCC/Clang/MSVC)

### Local Development

1. **Clone the repository**:
   ```bash
   git clone https://github.com/imakshayjaiswal/2nd_CA.git
   cd 2nd_CA
   ```

2. **Setup Backend**:
   ```bash
   pip install -r requirements.txt
   # Compile the C engine (varies by OS, see Makefile)
   make engine
   python app.py
   ```

3. **Setup Frontend**:
   ```bash
   cd frontend
   trunk serve
   ```

## 🚢 Deployment Guide

AeroTax is designed for split deployment: **Frontend (GitHub Pages)** and **Backend (Render)**.

### 1. Backend (Render)
1.  Sign in to [Render](https://render.com).
2.  Create a **New Web Service** and connect this repository.
3.  Render will automatically pick up the `render.yaml` configuration.
4.  In the **Environment** tab, add your secrets:
    - `GEMINI_API_KEY`: Your Google AI key.
    - `PINECONE_API_KEY`: Your Pinecone key.
5.  Wait for the build to finish. Copy your new Render URL (e.g., `https://aerotax-backend.onrender.com`).

### 2. Frontend (GitHub Pages)
1.  Go to your GitHub Repository **Settings > Actions > General**.
2.  Under **Workflow permissions**, select **Read and write permissions** (required for the deploy tool).
3.  Go to `frontend/index.html` and update the `window.AEROTAX_API_URL` block with your Render URL if you aren't using the automatic detection.
4.  Push any change to the `main` branch. GitHub Actions will build and deploy the WASM frontend to the `gh-pages` branch.
5.  In **Settings > Pages**, set the source to the `gh-pages` branch.

### 3. Verification
Access your live app at `https://<your-username>.github.io/2nd_CA/`.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
