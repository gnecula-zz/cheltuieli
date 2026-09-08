# Changelog

## 1.0.1

- Pozele de bonuri se comprimă înainte de upload (evită 413 pe Ingress/Cloudflare)
- Extragerea AI rulează în fundal, cu sondare — nu mai ține deschisă cererea până răspunde OpenRouter
- Headere OpenRouter + mesaje de eroare mai clare

## 1.0.0

- Add-on Home Assistant: container unic, Ingress, AUTH_MODE=homeassistant
- Mapare utilizatori HA după ID, fără login local
- Date pe /data (SQLite + upload-uri)
