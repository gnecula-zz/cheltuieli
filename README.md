# Cheltuieli

Add-on Home Assistant pentru cheltuielile gospodăriei: înregistrare manuală, import din poze de bonuri și din PDF-uri (facturi, extrase), categorii, bugete și rapoarte lunare.

Aplicația rulează **doar prin Ingress** (bara laterală). Nu publică un port. Accesul de pe internet trece prin Home Assistant, inclusiv dacă HA e expus cu **Cloudflared** pe domeniul tău.

## Instalare (Home Assistant)

[![Adaugă repository-ul în Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https://github.com/gnecula-zz/cheltuieli)

1. În Home Assistant: **Setări → Add-on-uri → Magazin → ⋮ → Repositories**.
2. Adaugă: `https://github.com/gnecula-zz/cheltuieli`
3. Instalează **Cheltuieli** și pornește-l. Apare în bara laterală.

Prima instalare **construiește** imaginea pe dispozitiv (Node + Python) și poate dura câteva minute. Nu publica un port pentru add-on.

Tunelul **Cloudflared** rămâne doar pe Home Assistant (portul 8123). Nu crea un hostname Cloudflare separat pentru Cheltuieli:

`https://domeniul-tau` → Cloudflared → HA 8123 → Ingress → add-on

Identitatea vine din utilizatorul Home Assistant, nu din Cloudflare. Detalii suplimentare: [cheltuieli/DOCS.md](cheltuieli/DOCS.md).

### Opțiuni add-on

- **admin_users** — username-uri sau ID-uri HA, separate prin virgulă. Dacă e goală, primul care deschide aplicația e administrator.
- **ai_api_key** — opțională. Poți lăsa goală și o completezi din **Setări** în aplicație. Furnizorul și modelul (OpenAI, Claude, Gemini, OpenRouter) se aleg tot din aplicație și rămân după update.

Fiecare utilizator HA care deschide Cheltuieli din bara laterală primește un cont mapat după **ID-ul HA** (nu după username), ca să nu se piardă cheltuielile dacă schimbi numele. Login-ul cu email/parolă este dezactivat.

Datele (SQLite și fișierele încărcate) stau pe `/data` și persistă la update-ul add-on-ului.

## Funcții

- **Cheltuieli** — adaugi rapid sumă, dată, comerciant, categorie, TVA, card sau numerar. Poți marca o cheltuială ca personală sau comună (gospodărie).
- **Categorii** — listă implicită (cumpărături, transport, utilități etc.), cu iconiță emoji și culoare. Administratorul poate redenumi orice categorie, inclusiv cele implicite, și poate adăuga altele.
- **Import bonuri și PDF-uri** — poze din cameră sau fișiere (JPG, PNG, PDF). PDF-urile cu text se citesc local. Pozele și scanurile folosesc agentul AI din Setări. Înainte de salvare verifici și corectezi extrasul. Extrasele nesalvate pot fi reluate sau șterse.
- **Agent AI** — OpenAI, Anthropic (Claude), Google (Gemini) sau OpenRouter (inclusiv modele gratuite cu vedere, pentru bonuri). Cheia se salvează în aplicație.
- **Conturi familie** — pe HA, membrii sunt utilizatorii care deschid add-on-ul. Administratorii se definesc din `admin_users`.
- **Bugete** — plafon lunar pe categorie, ca să vezi ce s-a cheltuit față de ce ți-ai propus.
- **Panou și rapoarte** — totaluri lunare, pe categorii și pe membri, cu export CSV.
- **Mobil** — interfață gândită pentru telefon, inclusiv buton de poză pentru bonuri.

Rulare locală (dezvoltare) și instalare pe VPS: vezi [instalare.txt](instalare.txt).
