# Cheltuieli

Aplicație web pentru gospodărie: cheltuieli manuale, import din poze de bonuri fiscale și din PDF-uri (facturi, extrase de cont), categorii, bugete și rapoarte lunare.

## Add-on Home Assistant (GitHub)

[![Adaugă repository-ul în Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https://github.com/gnecula-zz/cheltuieli)

1. În Home Assistant: **Setări → Add-on-uri → Magazin → ⋮ → Repositories**.
2. Adaugă: `https://github.com/gnecula-zz/cheltuieli`
3. Instalează **Cheltuieli**, pornește-l. Apare în bara laterală.

Prima instalare **construiește** imaginea pe dispozitiv (Node + Python); poate dura câteva minute. Nu publica un port. Tunelul **Cloudflared** rămâne doar pe Home Assistant (8123). Detalii: [cheltuieli/DOCS.md](cheltuieli/DOCS.md).

Opțiunea `admin_users`: username-uri HA, separate prin virgulă. Dacă e goală, primul care deschide aplicația e administrator.

## Rulare locală (dezvoltare)

Cerințe: Python 3.11+, Node 20+. Sursa aplicației e în folderul `cheltuieli/`.

1. Copiază `.env.example` în `.env` și completează `SECRET_KEY`. Opțional: `OPENAI_API_KEY`.
2. Backend:

```bash
cd cheltuieli/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

3. Frontend (alt terminal):

```bash
cd cheltuieli/frontend
npm install
npm run dev
```

Deschide [http://localhost:5173](http://localhost:5173). Primul cont înregistrat devine administrator.

Fără cheie AI în Setări, PDF-urile **cu text** se parsează local. Pozele de bonuri se încarcă, dar datele se completează manual.

## Producție (VPS + Docker)

Același cod, alte variabile. Pe server:

1. Copiază proiectul, creează `.env` cu `SECRET_KEY`, `POSTGRES_PASSWORD`, `COOKIE_SECURE=true`, `CORS_ORIGINS=https://domeniul-tau.ro`, `PUBLIC_URL=https://domeniul-tau.ro` și, opțional, `OPENAI_API_KEY`.
2. `docker compose up -d --build`
3. Pune HTTPS în fața portului 80 (Caddy, nginx + Let's Encrypt sau un reverse proxy).

Datele Postgres și fișierele încărcate stau pe volume Docker. Migrările Alembic rulează la pornirea API-ului.

Mutare de pe local: export CSV din Rapoarte, sau dump Postgres dacă deja folosești Compose local. Folderul de upload-uri se copiază pe volume-ul `uploads`.

## Funcții

- Conturi familie: admin creează membri
- Cheltuieli personale sau comune, TVA, card/numerar
- Import PDF (text) și poze (agent AI din Setări: OpenAI, Claude, Gemini sau OpenRouter)
- Review înainte de salvare
- Panou lunar, rapoarte, bugete, export CSV
- Interfață mobile-first (cameră pentru bonuri)
