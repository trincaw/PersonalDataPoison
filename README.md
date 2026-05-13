# Personal Data Poison (PDP)

Framework modulare per il data poisoning mirato contro le principali aziende di data collecting (Google, Meta, ByteDance, Microsoft, Amazon, X). Genera identità digitali persistenti con traffico web realistico per piattaforma, rendendo la correlazione OSINT tra sessioni estremamente complessa.

## Obiettivo

Ogni sessione targettizza una specifica piattaforma con comportamenti realistici per quella piattaforma:
- **Google** — Ricerche, Maps, News, Shopping, Images
- **YouTube** — Watch, browse trending, categorie
- **Instagram** — Explore, hashtag, reels, profili
- **Facebook** — Feed, Marketplace, eventi, video
- **TikTok** — FYP scroll, discover, hashtag
- **LinkedIn** — Feed, job search, company browsing
- **Twitter/X** — Timeline, trending, liste
- **Amazon** — Ricerche prodotto, categorie, bestseller

Ogni identità mantiene interessi **diversi per piattaforma** — il profilo che Google vede è diverso da quello che Instagram traccia, complicando la correlazione cross-platform.

## Architettura

```
src/
├── app.py                    # Entrypoint CLI
├── accounts/                 # Gestione credenziali criptate + login flow
├── config/                   # Caricamento e validazione YAML
├── core/                     # Event bus, lifecycle, orchestratore
├── platforms/                # Strategy per piattaforma (Google, Meta, ecc.)
├── identity/                 # Generazione, persistenza e scoring identità
├── fingerprint/              # Consistenza e validazione fingerprint
├── browser/                  # Controller Playwright, behavior engine
├── network/                  # Proxy pool, DNS, transport layer
├── timing/                   # Profili circadiani, distribuzioni temporali
├── storage/                  # SQLAlchemy models, SQLite persistence
├── telemetry/                # Logging strutturato, metriche, tracing
└── plugins/                  # Plugin architecture (browser, identity, timing)
```

## Setup

```bash
# Bootstrap completo (dipendenze + database + Playwright)
python scripts/bootstrap.py

# Oppure manuale:
pip install -e ".[dev]"
python -m playwright install chromium
```

## Utilizzo

```bash
# Dry run — genera identità e mostra le piattaforme target
python src/app.py --profile desktop --dry-run

# Sessione singola (piattaforma selezionata automaticamente con pesi)
python src/app.py --profile desktop -n 1

# Targeting specifico su una piattaforma
python src/app.py --profile desktop --target google -n 1
python src/app.py --profile mobile --target tiktok -n 3

# Modalità multi-piattaforma (stessa identità visita più piattaforme)
python src/app.py --profile research --mode multi_platform -n 1

# Modalità continua (circadian-aware, ruota piattaforme)
python src/app.py --profile desktop

# Headless con verbose
python src/app.py --profile desktop --headless -v

# Seed identità nel datastore
python scripts/seed_identities.py -n 20 --locale it-IT
```

### Modalità sessione

| Modalità            | Comportamento                                              |
|---------------------|------------------------------------------------------------|
| `single_platform`   | Ogni sessione targettizza una sola piattaforma             |
| `multi_platform`    | Stessa identità visita 2-4 piattaforme in sequenza         |
| `mixed`             | Alterna casualmente tra single e multi (default desktop)   |

## Gestione Account

Per sessioni autenticate (login su piattaforme), PDP usa un sistema di credenziali criptate AES su disco.

### Setup passphrase

```bash
# Imposta la passphrase per criptare/decriptare gli account
export PDP_ACCOUNTS_PASSPHRASE="la_tua_passphrase"
```

### Aggiungere account

```bash
# Google (usato anche per YouTube)
python scripts/manage_accounts.py add --platform google --username user@gmail.com --email user@gmail.com

# Instagram
python scripts/manage_accounts.py add --platform instagram --username myuser --email user@mail.com

# Facebook, TikTok, LinkedIn, Twitter, Amazon...
python scripts/manage_accounts.py add --platform facebook --username user@mail.com
python scripts/manage_accounts.py add --platform tiktok --username user@mail.com
python scripts/manage_accounts.py add --platform linkedin --username user@mail.com
python scripts/manage_accounts.py add --platform twitter --username @handle
python scripts/manage_accounts.py add --platform amazon --username user@mail.com
```

La password viene chiesta interattivamente se non specificata con `--password`.

### Gestione

```bash
# Lista tutti gli account
python scripts/manage_accounts.py list

# Lista per piattaforma
python scripts/manage_accounts.py list --platform google

# Rimuovi un account
python scripts/manage_accounts.py remove --platform google --username user@gmail.com

# Assegna un account a un'identità specifica
python scripts/manage_accounts.py assign --platform google --username user@gmail.com --identity id-abc12345

# Testa il login (apre browser visibile)
python scripts/manage_accounts.py test --platform instagram
```

### Abilitare il login automatico

In `configs/base.yaml`:

```yaml
accounts:
  enabled: true           # Abilita il sistema di account
  accounts_dir: "data/accounts"
  sessions_dir: "data/sessions"
  save_sessions: true     # Salva cookie dopo login riuscito
```

**Funzionamento:**
1. Al primo avvio, PDP esegue il login con le credenziali salvate
2. I cookie vengono salvati in `data/sessions/`
3. Nelle sessioni successive, i cookie vengono ricaricati (no re-login)
4. Se non ci sono account per una piattaforma, la sessione è non-autenticata

## Profili

| Profilo    | Descrizione                                      | Piattaforme dominanti            |
|------------|--------------------------------------------------|----------------------------------|
| `desktop`  | Sessioni lunghe, mixed mode                      | Google, YouTube, Amazon          |
| `mobile`   | Sessioni brevi, scroll veloce, single platform   | TikTok, Instagram, YouTube       |
| `research` | Dwell time lungo, multi-platform, Firefox        | Google, YouTube, LinkedIn        |

## Configurazione

La configurazione è gerarchica:

```
configs/base.yaml → configs/profiles/<nome>.yaml → variabili d'ambiente (PDP_*)
```

### Pesi piattaforme

In `configs/base.yaml` o nei profili:

```yaml
platforms:
  enabled:
    - google
    - youtube
    - instagram
    - facebook
    - tiktok
    - linkedin
    - twitter
    - amazon
  weights:
    google: 5.0       # Più alto = selezionato più spesso
    youtube: 4.0
    instagram: 3.0
    tiktok: 3.0
    amazon: 2.5
```

### Variabili d'ambiente

| Variabile                   | Descrizione                          |
|-----------------------------|--------------------------------------|
| `PDP_ACCOUNTS_PASSPHRASE`  | Passphrase per criptare gli account  |
| `PDP_BROWSER__HEADLESS`    | Override headless mode               |
| `PDP_GENERAL__LOG_LEVEL`   | Override log level                   |

## Test

```bash
pytest tests/ -v
```

## Plugin

Estendi `plugins.base.Plugin` (o `BrowserPlugin`, `IdentityPlugin`, `TimingPlugin`) e registra in `configs/base.yaml`:

```yaml
plugins:
  - "plugins.browser.my_plugin:MyBrowserPlugin"
```

## Sicurezza

- Le credenziali sono criptate AES-256 (Fernet + PBKDF2 600k iterazioni)
- I file `.enc` non contengono dati leggibili senza la passphrase
- I cookie di sessione sono salvati in chiaro in `data/sessions/` (aggiungi a `.gitignore`)
- Non committare mai `data/` nel repository
