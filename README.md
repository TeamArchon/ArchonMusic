# Archon Music

Telegram Music Player Bot, written in Python with Pyrogram and Py-Tgcalls.

## 🚀 Deploy to Heroku

> **Important:** The Heroku Deploy button works after this project is pushed to a **public GitHub repository**.

### Deploy button

Replace `YOUR_GITHUB_USERNAME/YOUR_REPO` below with the GitHub repository containing this project:

```markdown
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO)
```
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/TeamArchon/ArchonMusic)
```

### Required environment variables

Heroku will show these fields automatically from `app.json`:

- `API_ID`
- `API_HASH`
- `BOT_TOKEN`
- `MONGO_DB_URI`
- `OWNER_ID`
- `STRING_SESSION`
- `LOGGER_ID`
- `SHRUTI_API_URL`
- `SHRUTI_API_KEY`

Optional Heroku variables:

- `HEROKU_API_KEY`
- `HEROKU_APP_NAME`

The project already includes:
- `app.json`
- `Procfile`
- `heroku.yml`
- `Dockerfile`
- `runtime.txt`
- `start`

### Heroku deploy flow

1. Push this project to GitHub.
2. Make the GitHub repository public.
3. Put the GitHub URL in the Deploy button shown above.
4. Open the button.
5. Enter the required variables.
6. Click **Deploy app**.
