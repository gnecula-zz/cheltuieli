# Changelog

## 1.0.5

- Furnizorul AI din Setări nu se mai resetează la OpenAI după update-ul add-on-ului

## 1.0.4

- Poți șterge extrasele nesalvate din Import

## 1.0.3

- Salvarea a două bonuri de la același comerciant; extrasele abandonate pot fi reluate din Import
- Fără curse între poze consecutive; SQLite WAL; validare mai tolerantă la sumă/dată
- Editare categorii (nume, emoji, culoare), inclusiv cele implicite

## 1.0.2

- Modele gratuite OpenRouter în Setări (inclusiv cu vedere, pentru poze de bonuri)

## 1.0.1

- Pozele de bonuri se comprimă înainte de upload (evită 413 pe Ingress/Cloudflare)
- Extragerea AI rulează în fundal, cu sondare — nu mai ține deschisă cererea până răspunde OpenRouter
- Headere OpenRouter + mesaje de eroare mai clare

## 1.0.0

- Add-on Home Assistant: container unic, Ingress, AUTH_MODE=homeassistant
- Mapare utilizatori HA după ID, fără login local
- Date pe /data (SQLite + upload-uri)
