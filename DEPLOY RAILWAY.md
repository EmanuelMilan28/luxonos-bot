# Vendos Luxonos Bot online me Railway.app (FALAS)

Kjo e mban botin **24/7 online** pa pasur nevojë laptopi i ndezur.

## 1. Krijo llogari
1. Shko te **railway.app**
2. Kliko "Login" → zgjidh "Login with GitHub" (nëse s'ke llogari GitHub, krijo një falas te github.com fillimisht — merr 2 minuta)

## 2. Ngarko kodin te GitHub (nëse s'e ke bërë ende)
Mënyra më e lehtë pa linjë komande:
1. Shko te **github.com** → New repository → emërtoje `luxonos-bot` → Create
2. Në faqen e repository-t, kliko "uploading an existing file"
3. Tërhiq/ngarko këto skedarë: `bot.py`, `requirements.txt`, `Procfile`, `runtime.txt`
   ⚠️ **MOS ngarko `.env`** — ai duhet të mbetet vetëm te kompjuteri yt, kurrë publik
4. Kliko "Commit changes"

## 3. Lidhe me Railway
1. Në Railway, kliko **"New Project"**
2. Zgjidh **"Deploy from GitHub repo"**
3. Zgjidh repository-n `luxonos-bot` që sapo krijove
4. Railway do të fillojë ta instalojë automatikisht

## 4. Shto token-in si "Environment Variable" (në vend të .env)
1. Në projektin e Railway, shko te tab-i **"Variables"**
2. Kliko **"New Variable"**
3. Emri: `BOT_TOKEN`
4. Vlera: [ngjit token-in tënd nga BotFather]
5. Save

## 5. Kontrollo që punon
1. Shko te tab-i **"Deployments"** → shiko "Logs"
2. Duhet të shohësh: `Luxonos bot is starting...`
3. Shko te grupi yt Telegram dhe shkruaj `/start` — duhet të përgjigjet

## Gati!
Boti tani punon 24/7 në serverat e Railway, pa lidhje me laptopin tënd.
Plani falas i Railway jep ~500 orë/muaj — më shumë se sa mjafton për një bot të vetëm gjatë gjithë muajit.

---

### Nëse diçka nuk punon
Kopjo mesazhin e gabimit nga "Logs" te Railway dhe ma dërgo — e zgjidhim bashkë.
