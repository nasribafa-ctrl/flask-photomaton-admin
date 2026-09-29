# Photomaton Admin

A Raspberry Pi photobooth system: kiosk software that drives the camera, printer, coin
acceptor and lighting, plus a Flask web admin panel backed by SQLite for managing the
booth remotely.

## Context

This project was built during a school internship at **Minute Papillons**, a company
that operates photobooths for events. It's a **team project** — several people
contributed to it over time (camera/printer/hardware integration, the design/template
editor, the booth kiosk logic, etc.).

**My contributions** during the internship:
- **User management** — admin panel for creating/listing/deleting operator accounts
  with role-based access (`flask/app.py`: `liste_utilisateurs`, `delete_user`; see
  `templates/user.html`).
- **Password security** — account passwords are hashed with Werkzeug's
  `generate_password_hash` / `check_password_hash` (PBKDF2), never stored or compared
  in plain text.
- **Prompt management** — CRUD interface for the AI style prompts used by the booth
  (create, edit, delete, associate a prompt with a camera pose — see the
  `/prompt` routes and `templates/prompt.html`, `modifier_prompt.html`,
  `crée_prompt.html`).
- **AI prompt generation** — the pipeline in `base/ia.py` that takes a prompt
  (positive/negative text + optional LoRAs), sends the current photo to a Stable
  Diffusion (AUTOMATIC1111 WebUI) instance with ControlNet (pose guidance) and
  ReActor (face swap), and saves the stylised result for preview/print
  (`utiliser_prompt`, `creer_prompt` routes and `prompt_test.html`).

This repository is a copy of the original internship codebase, stripped of the
production secrets and real customer photos (see **Notes on this copy** below) so it
can be shared publicly as a portfolio piece.

## What it does

- **Booth kiosk** (`base/`): captures photos (gphoto2), applies print layouts, drives
  a coin acceptor (MDB), an LED matrix/strip, an LCD/keypad, and sends jobs to a
  printer (CUPS). Optionally re-styles the shot through an AI image generator before
  printing.
- **Admin panel** (`flask/`): a Flask app to log in, manage operator accounts, manage
  AI prompts, review/print past sessions, and edit booth configuration, print
  templates and designs.
- **Storage**: a single SQLite database (`base/booth.db`) shared by both parts —
  users, prompts, booth configuration, designs/layers and photo sessions.

## Tech stack

- **Backend**: Python, Flask, SQLite (`sqlite3`)
- **Auth/security**: Flask sessions, Werkzeug password hashing (PBKDF2)
- **Frontend**: Jinja2 templates, Bootstrap 5, vanilla JS
- **Hardware integration**: gphoto2 (camera), CUPS (printer), RPi.GPIO / Adafruit
  libraries (LED matrix/strip, ADC), pyserial (Arduino/coin acceptor)
- **AI generation**: `webuiapi` client for a Stable Diffusion AUTOMATIC1111 server,
  with ControlNet (pose) and ReActor (face swap) extensions
- **Remote access** (production setup, not required to run this copy): the real
  deployment reaches the booths and the GPU/Stable Diffusion server over a private
  Tailscale network

## Running it locally

This is Raspberry Pi kiosk software, but the **admin panel** (`flask/`) runs fine on a
regular machine without any hardware attached.

```bash
cd flask
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt

cp ../.env.example ../.env      # then edit ../.env, at least SECRET_KEY
flask run
```

Open `http://127.0.0.1:5000/Authentification` and log in with one of the demo
accounts below (see **Demo accounts**), or create an additional one with
`flask/creation_useradmin.py` after setting `DEMO_ADMIN_LOGIN` /
`DEMO_ADMIN_PASSWORD` in `.env`.

### Demo accounts

`base/booth.db` ships with four demo accounts, one per role, so anyone can log in
and try every permission level without touching the database:

| Login          | Password     | Role(s)                              |
|----------------|--------------|---------------------------------------|
| `demo_admin`   | `Demo1234!`  | admin                                 |
| `demo_lecture` | `Demo1234!`  | lecture                               |
| `demo_editeur` | `Demo1234!`  | lecture, modification, suppression    |
| `demo_modif`   | `Demo1234!`  | modification                          |

These replace the original team's real accounts — same roles, fresh scrypt
password hashes, fictitious logins/password.

### AI prompt generation without a Stable Diffusion server

`base/ia.py` checks whether the configured `SD_API_HOST`/`SD_API_PORT` is reachable
before generating anything. If it isn't (the default `.env.example` value), prompt
testing/generation fails gracefully and logs a warning instead of crashing — you can
still use every other feature (login, user management, prompt CRUD) without running a
real Stable Diffusion instance.

### Hardware-dependent parts (`base/`)

The booth kiosk (`base/main.py` and friends) expects Raspberry Pi hardware (GPIO,
camera, printer, etc.) and Linux-only packages (`rpi-lgpio`, `RPi.GPIO`, ...) — it
isn't meant to run on a regular desktop.

## Notes on this copy

Compared to the original internship repository, this copy:
- Has its own fresh git history (not connected to the internship's private remote).
- Moves all secrets (Flask `SECRET_KEY`, the Stable Diffusion host, an SSH password
  used by an internal monitoring script, demo account credentials) out of the source
  code and into a local `.env` file (see `.env.example`).
- Drops the internal monitoring config (`monitor.json`) entirely, since it listed the
  real hostnames of production booths.
- Drops all real customer photos and photo-derived AI outputs (booth session
  captures, camera test shots, and template mockups that happened to use a real
  customer's photo).
- Drops `base/photomatons_status.db` and `base/booth.db.bkp`, two stray snapshot
  files (not used by the app) that embedded a real booth hostname and real session
  paths.
- Replaces the four real team accounts that were in `base/booth.db`'s `USER` table
  with the four fictitious demo accounts listed above — same roles, freshly
  generated password hashes, so the original (weak) test passwords can't be
  recovered from the hashes anymore.
- Replaces hardcoded `/home/minutepapillons/...` deployment paths across the booth
  scripts (`activatevenv.sh`, `boothlauncher.sh`, `boothsStatus.py`, `checkPod.py`,
  `photo_scroll.py`, `monitor.py`, `config.json`) with paths relative to the project,
  optionally overridable via `.env`.
