# Cheltuieli — add-on Home Assistant

Aplicația rulează **doar prin Ingress** (bara laterală). Nu publică un port. Accesul de pe internet trece prin Home Assistant, inclusiv dacă HA e expus cu **Cloudflared** pe domeniul tău.

## Instalare din GitHub

1. **Setări → Add-on-uri → Magazin → ⋮ → Repositories**
2. Adaugă `https://github.com/gnecula-zz/cheltuieli`
3. Instalează **Cheltuieli** și pornește-l. Apare în bara laterală.

Sau deschide: [Adaugă repository-ul](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https://github.com/gnecula-zz/cheltuieli)

Prima instalare construiește containerul pe HA (poate dura). Nu expune portul add-on-ului.

## Cloudflared / domeniu propriu

Tunelul trebuie să trimită traficul **doar la Home Assistant (8123)**. Nu crea un hostname Cloudflare separat pentru Cheltuieli.

Fluxul corect:

`https://domeniul-tau` → Cloudflared → HA 8123 → Ingress (`/api/hassio_ingress/...`) → add-on

Identitatea utilizatorului vine din headerele puse de Supervisor (`X-Remote-User-Id`), **nu** din Cloudflare și **nu** din `X-Forwarded-For`.

Dacă folosești Cloudflare Access în fața HA, e în regulă: te autentifici întâi în HA, apoi Ingress merge.

Nu bifa „Show in sidebar” și apoi să încerci URL-ul intern al containerului din afara HA — nu e expus.

## Utilizatori

- Fiecare utilizator HA care deschide aplicația din bara laterală primește un cont mapat după **ID-ul HA** (nu după username, ca să nu se piardă cheltuielile dacă schimbi numele).
- Login-ul cu email/parolă este dezactivat.
- **admin_users**: username-uri HA (sau ID-uri), separate prin virgulă. Dacă e gol, primul care deschide aplicația e administrator.

## Date

SQLite și fișierele încărcate stau în `/data` (persistă la update-ul add-on-ului). Cheia AI din opțiuni se aplică la pornire dacă o completezi; o poți schimba și din Setări în aplicație.

## Limită upload

`ingress_stream` e activat pentru poze și PDF-uri. Cloudflare are de obicei o limită de body suficientă pentru fișierele din aplicație (~20 MB).
