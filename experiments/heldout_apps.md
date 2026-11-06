# Held-out apps for the scaling tests (frozen 2026-11-06, before any web-app data is recorded)

No model is trained on any data from these apps before their test. They are used only as "new apps".

- **Desktop (unchanged from Stage 5):** disk-usage, files, logs.
- **Desktop (new, if it records cleanly):** LibreOffice Math.
- **Web (5 of the 21 apps in `dreamdesk/webapps`, drawn with `random.Random("dreamdesk-heldout-web").sample(WEB_APPS, 5)`):**
  chat, fitness, quiz, todo, weather.

The other 16 web apps and the 7 Stage 3 desktop apps are training apps for the priors. The web apps were all written
by us in one style, so results are reported separately for desktop and web held-out apps.
