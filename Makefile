# AeroTax Makefile — Hackathon Speed Commands
# Usage:
#   make build-engine   → compile C library
#   make run-backend    → start FastAPI
#   make run-frontend   → start Leptos/Trunk dev server
#   make all            → build everything

# ── C Engine ────────────────────────────────────────────────────
build-engine:
	@echo "⚡ Compiling AeroTax C Engine..."
ifeq ($(OS),Windows_NT)
	gcc -O3 -march=native -shared -o engine/engine.dll engine/engine.c -lm
	@echo "✅ engine.dll compiled"
else
	gcc -O3 -march=native -ffast-math -shared -fPIC -o engine/engine.so engine/engine.c -lm -lpthread
	@echo "✅ engine.so compiled"
endif

# ── Backend ──────────────────────────────────────────────────────
install-backend:
	cd backend && pip install -r requirements.txt

run-backend:
	cd backend && uvicorn main:app --reload --port 8000 --host 0.0.0.0

# ── Frontend ─────────────────────────────────────────────────────
install-frontend:
	cargo install trunk
	rustup target add wasm32-unknown-unknown

run-frontend:
	cd frontend && trunk serve --open --port 8080

build-frontend:
	cd frontend && trunk build --release

# ── Combined ─────────────────────────────────────────────────────
all: build-engine install-backend install-frontend

.PHONY: build-engine install-backend run-backend install-frontend run-frontend build-frontend all
