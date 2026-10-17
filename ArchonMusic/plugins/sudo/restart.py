import asyncio
import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path
from datetime import datetime

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError
from pyrogram import filters

import config
from ArchonMusic import yuki
from ArchonMusic.misc import HAPP, SUDOERS, XCB
from ArchonMusic.utils.database import (
    get_active_chats,
    remove_active_chat,
    remove_active_video_chat,
)
from ArchonMusic.utils.decorators.language import language
from ArchonMusic.utils.pastebin import ArchonBin

log = logging.getLogger("ArchonMusic.Updater")

# /root/ArchonMusicBot
ROOT = Path(__file__).resolve().parents[3]
BACKUPS = ROOT / "backups" / "updater"
STATE = ROOT / ".ArchonMusic_update.json"
LOCK = asyncio.Lock()

PROTECTED = {
    ".env",
    ".git",
    "venv",
    ".venv",
    "__pycache__",
    "backups",
    ".ArchonMusic_update.json",
}

AUTO_CHECK = os.getenv("ArchonMusic_AUTO_UPDATE_CHECK", "true").lower() in {
    "1", "true", "yes", "on"
}
CHECK_INTERVAL = max(300, int(os.getenv("ArchonMusic_UPDATE_INTERVAL", "3600")))
NOTIFY_COOLDOWN = max(
    300, int(os.getenv("ArchonMusic_UPDATE_NOTIFY_COOLDOWN", "21600"))
)


async def is_heroku():
    return "heroku" in socket.getfqdn()


@yuki.on_message(filters.command(["getlog", "logs", "getlogs"]) & SUDOERS)
@language
async def log_(client, message, _):
    try:
        await message.reply_document(document="log.txt")
    except Exception:
        await message.reply_text(_["server_1"])



def repo_name():
    repo = str(getattr(config, "UPSTREAM_REPO", "")).rstrip("/")
    return repo.split("github.com/")[-1].removesuffix(".git")


def branch():
    return getattr(config, "UPSTREAM_BRANCH", "main")


def github_headers():
    headers = {
        "User-Agent": "ArchonMusic-Updater",
        "Accept": "application/vnd.github+json",
    }
    token = getattr(config, "GIT_TOKEN", None)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def github_json(url):
    req = urllib.request.Request(url, headers=github_headers())
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def download(url, path):
    req = urllib.request.Request(url, headers=github_headers())
    with urllib.request.urlopen(req, timeout=180) as r:
        with open(path, "wb") as f:
            shutil.copyfileobj(r, f)


def latest_commit():
    owner_repo = repo_name()
    if not owner_repo or "/" not in owner_repo:
        raise RuntimeError("Invalid UPSTREAM_REPO in config.py")
    data = github_json(
        f"https://api.github.com/repos/{owner_repo}/commits/{branch()}"
    )
    return data["sha"], data["commit"]["message"].splitlines()[0]


def latest_release():
    try:
        owner_repo = repo_name()
        data = github_json(
            f"https://api.github.com/repos/{owner_repo}/releases/latest"
        )
        return {
            "tag": data.get("tag_name") or "",
            "name": data.get("name") or "",
            "url": data.get("html_url") or "",
        }
    except Exception:
        return {}


def read_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def local_commit():
    state = read_state()
    if (
        state.get("repository") == repo_name()
        and state.get("branch") == branch()
        and state.get("commit")
    ):
        return state["commit"]

    git = shutil.which("git")
    if git and (ROOT / ".git").exists():
        try:
            result = subprocess.run(
                [git, "rev-parse", "HEAD"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            return result.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
    return None


def save_state(commit, **extra):
    data = read_state()
    data.update(
        {
            "repository": repo_name(),
            "branch": branch(),
            "commit": commit,
            "updated_at": int(time.time()),
        }
    )
    data.update(extra)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    tmp.replace(STATE)


def history():
    return read_state().get("history", [])


def add_history(entry):
    state = read_state()
    items = state.get("history", [])
    items.insert(0, entry)
    state["history"] = items[:20]
    save_state(state.get("commit") or local_commit() or "", history=state["history"])


def protected(path):
    return any(part in PROTECTED for part in Path(path).parts)


def safe_rel(path):
    p = Path(path)
    return not p.is_absolute() and ".." not in p.parts and not protected(p)


def extract_zip(zip_path, destination):
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            if not safe_rel(info.filename):
                raise RuntimeError(f"Unsafe archive path: {info.filename}")
        z.extractall(destination)

    folders = [p for p in destination.iterdir() if p.is_dir()]
    if len(folders) != 1:
        raise RuntimeError("Invalid GitHub archive.")
    return folders[0]


def repo_files(source):
    return [
        p.relative_to(source)
        for p in source.rglob("*")
        if p.is_file() and safe_rel(p.relative_to(source))
    ]


def backup_files(files, backup):
    old = []
    new = []
    for rel in files:
        if protected(rel):
            continue
        src = ROOT / rel
        dst = backup / rel
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            old.append(rel)
        elif not src.exists():
            new.append(rel)
    return old, new


def apply_files(source, files):
    for rel in files:
        if protected(rel):
            continue
        src = source / rel
        dst = ROOT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def rollback(backup, old, new):
    for rel in old:
        src = backup / rel
        dst = ROOT / rel
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    for rel in new:
        dst = ROOT / rel
        if dst.is_file():
            try:
                dst.unlink()
            except OSError:
                log.exception("Could not remove new file during rollback: %s", dst)


def validate(files):
    for rel in files:
        if rel.suffix != ".py" or protected(rel):
            continue
        path = ROOT / rel
        compile(path.read_text(encoding="utf-8"), str(path), "exec")


def requirements_changed(backup):
    current = ROOT / "requirements.txt"
    old = backup / "requirements.txt"
    if not current.exists():
        return False
    if not old.exists():
        return True
    return current.read_bytes() != old.read_bytes()


def install_requirements(requirements=None):
    req = requirements or (ROOT / "requirements.txt")
    if not req.exists():
        return
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        timeout=900,
        check=True,
    )


def changed_summary(files):
    names = [str(x).replace("\\", "/") for x in files if not protected(x)]
    names.sort()
    if len(names) <= 15:
        return names
    return names[:15] + [f"... +{len(names) - 15} more"]


async def update_bot():
    async with LOCK:
        with tempfile.TemporaryDirectory(prefix="ArchonMusic-") as tmp:
            tmp = Path(tmp)
            archive = tmp / "update.zip"
            source_dir = tmp / "source"

            latest, message = await asyncio.to_thread(latest_commit)
            current = local_commit()
            if current == latest:
                return False, latest, "already_latest", [], None

            owner_repo = repo_name()
            url = f"https://github.com/{owner_repo}/archive/refs/heads/{branch()}.zip"
            await asyncio.to_thread(download, url, archive)
            source_dir.mkdir()
            source = await asyncio.to_thread(extract_zip, archive, source_dir)
            files = repo_files(source)
            if not files:
                raise RuntimeError("GitHub update is empty.")

            stamp = time.strftime("%Y%m%d-%H%M%S")
            backup = BACKUPS / stamp
            backup.mkdir(parents=True, exist_ok=True)
            old, new = await asyncio.to_thread(backup_files, files, backup)

            try:
                await asyncio.to_thread(apply_files, source, files)
                await asyncio.to_thread(validate, files)

                if requirements_changed(backup):
                    await asyncio.to_thread(install_requirements)

                save_state(latest, last_backup=str(backup.relative_to(ROOT)))
                add_history(
                    {
                        "time": int(time.time()),
                        "from": current,
                        "to": latest,
                        "message": message[:500],
                        "backup": str(backup.relative_to(ROOT)),
                        "files": changed_summary(files),
                        "status": "success",
                    }
                )
                return True, latest, message, changed_summary(files), backup

            except Exception:
                log.exception("Update failed. Rolling back.")
                await asyncio.to_thread(rollback, backup, old, new)
                old_req = backup / "requirements.txt"
                if old_req.exists():
                    try:
                        await asyncio.to_thread(install_requirements, old_req)
                    except Exception:
                        log.exception("Dependency rollback failed.")

                add_history(
                    {
                        "time": int(time.time()),
                        "from": current,
                        "to": latest,
                        "message": message[:500],
                        "backup": str(backup.relative_to(ROOT)),
                        "files": changed_summary(files),
                        "status": "failed_rolled_back",
                    }
                )
                raise


def restore_backup(backup):
    if not backup.exists() or not backup.is_dir():
        raise RuntimeError("Backup not found.")
    files = [p.relative_to(backup) for p in backup.rglob("*") if p.is_file()]
    if not files:
        raise RuntimeError("Backup is empty.")

    for rel in files:
        if protected(rel):
            continue
        src = backup / rel
        dst = ROOT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    req = backup / "requirements.txt"
    if req.exists():
        install_requirements(req)
    return len(files)


def latest_backup():
    if not BACKUPS.exists():
        return None
    dirs = sorted((p for p in BACKUPS.iterdir() if p.is_dir()), reverse=True)
    return dirs[0] if dirs else None


def restart_bot():
    os.execv(sys.executable, [sys.executable, "-m", "ArchonMusic"])


def authorized(user_id):
    owner = getattr(config, "OWNER_ID", None)
    sudo = getattr(config, "SUDO_USERS", [])
    return user_id == owner or user_id in sudo


def update_buttons():
    # Standard Pyrogram buttons; no BioGuard/premium dependency required.
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔄 Update", callback_data="ymupd:update"),
                InlineKeyboardButton("❌ Cancel", callback_data="ymupd:cancel"),
            ]
        ]
    )


def info_buttons():
    from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔄 Check Again", callback_data="ymupd:check"),
                InlineKeyboardButton("📜 History", callback_data="ymupd:history"),
            ],
            [InlineKeyboardButton("↩️ Rollback", callback_data="ymupd:rollback")],
        ]
    )


async def check_update_message(message):
    latest, commit_message = await asyncio.to_thread(latest_commit)
    release = await asyncio.to_thread(latest_release)
    current = local_commit()

    if current == latest:
        await message.edit_text(
            "✅ <b>ArchonMusic is already up to date.</b>\n\n"
            f"<b>Version:</b> <code>{latest[:7]}</code>",
            reply_markup=info_buttons(),
        )
        return False

    await message.edit_text(
        "🔄 <b>New ArchonMusic update available.</b>\n\n"
        f"<b>Current:</b> <code>{(current or 'Unknown')[:7]}</code>\n"
        f"<b>Latest:</b> <code>{latest[:7]}</code>\n\n"
        f"📝 <b>{commit_message[:500]}</b>\n"
        f"<b>Release:</b> <code>{(release.get('tag') or 'None')[:80]}</code>\n\n"
        "<b>Install this update?</b>",
        reply_markup=update_buttons(),
    )
    return True


@yuki.on_message(filters.command("update") & SUDOERS)
@language
async def update_command(client, message, _):
    if await is_heroku():
        if HAPP is None:
            return await message.reply_text(_["server_2"])
    if LOCK.locked():
        return await message.reply_text("🔄 <b>An update is already running.</b>")

    msg = await message.reply_text("🔄 <b>Checking for updates...</b>")
    try:
        await check_update_message(msg)
    except Exception as e:
        log.exception("Update check failed.")
        await msg.edit_text(
            "❌ <b>Could not check for updates.</b>\n\n"
            f"<code>{str(e)[:700]}</code>",
            reply_markup=info_buttons(),
        )


@yuki.on_message(filters.command("gitpull") & SUDOERS)
@language
async def gitpull_command(client, message, _):
    # Keep the old command as an alias of the new safe updater.
    return await update_command(client, message, _)


@yuki.on_callback_query(filters.regex(r"^ymupd:(update|cancel|check|history|rollback)$"))
async def update_callback(client, query):
    if not query.from_user or not authorized(query.from_user.id):
        await query.answer("You are not authorized.", show_alert=True)
        return

    action = query.data.split(":", 1)[1]

    if action == "cancel":
        await query.answer("Update cancelled.")
        await query.edit_message_text("❌ <b>Update cancelled.</b>")
        return

    if action == "check":
        await query.answer()
        try:
            await query.edit_message_text("🔄 <b>Checking for updates...</b>")
            await check_update_message(query.message)
        except Exception as e:
            log.exception("Manual update check failed.")
            await query.edit_message_text(
                "❌ <b>Check failed.</b>\n\n"
                f"<code>{str(e)[:700]}</code>",
                reply_markup=info_buttons(),
            )
        return

    if action == "history":
        await query.answer()
        items = history()[:10]
        if not items:
            text = "📜 <b>No update history found.</b>"
        else:
            lines = ["📜 <b>ArchonMusic Update History</b>\n"]
            for item in items:
                when = time.strftime(
                    "%Y-%m-%d %H:%M", time.localtime(item.get("time", 0))
                )
                lines.append(
                    f"<b>{when}</b> • <code>{str(item.get('to', ''))[:7]}</code> • "
                    f"<b>{item.get('status', 'unknown')}</b>"
                )
            text = "\n".join(lines)
        await query.edit_message_text(text, reply_markup=info_buttons())
        return

    if action == "rollback":
        await query.answer()
        if LOCK.locked():
            await query.answer("An update is already running.", show_alert=True)
            return

        backup = latest_backup()
        if not backup:
            await query.edit_message_text(
                "❌ <b>No backup is available for rollback.</b>",
                reply_markup=info_buttons(),
            )
            return

        try:
            async with LOCK:
                count = await asyncio.to_thread(restore_backup, backup)

            add_history(
                {
                    "time": int(time.time()),
                    "from": local_commit(),
                    "to": "rollback",
                    "message": "Manual rollback",
                    "backup": str(backup.relative_to(ROOT)),
                    "files": [f"Restored {count} files"],
                    "status": "rollback_success",
                }
            )

            await query.edit_message_text(
                "✅ <b>Rollback completed.</b>\n\n"
                f"<b>Backup:</b> <code>{backup.name}</code>\n"
                "<b>Restarting ArchonMusic...</b>"
            )
            await asyncio.sleep(2)
            await asyncio.to_thread(restart_bot)
        except Exception as e:
            log.exception("Rollback failed.")
            await query.edit_message_text(
                "❌ <b>Rollback failed.</b>\n\n"
                f"<code>{str(e)[:900]}</code>",
                reply_markup=info_buttons(),
            )
        return

    if LOCK.locked():
        await query.answer("An update is already running.", show_alert=True)
        return

    await query.answer("Updating ArchonMusic...")
    try:
        await query.edit_message_text(
            "🔄 <b>Updating ArchonMusic...</b>\n\n"
            "Creating backup and validating files."
        )

        updated, commit, commit_message, files, backup = await update_bot()

        if not updated:
            await query.edit_message_text(
                "✅ <b>ArchonMusic is already up to date.</b>",
                reply_markup=info_buttons(),
            )
            return

        file_text = "\n".join(f"• <code>{x}</code>" for x in files[:15])
        if len(files) > 15:
            file_text += f"\n• <i>+{len(files) - 15} more</i>"

        await query.edit_message_text(
            "✅ <b>Update installed successfully.</b>\n\n"
            f"<b>Version:</b> <code>{commit[:7]}</code>\n"
            f"📝 <b>{commit_message[:400]}</b>\n\n"
            f"<b>Changed files:</b>\n{file_text or '• None'}\n\n"
            f"<b>Backup:</b> <code>{backup.name}</code>\n"
            "<b>Restarting ArchonMusic...</b>"
        )
        await asyncio.sleep(2)
        await asyncio.to_thread(restart_bot)

    except Exception as e:
        log.exception("Update failed.")
        try:
            await query.edit_message_text(
                "❌ <b>Update failed.</b>\n\n"
                "<b>Previous version was restored.</b>\n\n"
                f"<code>{str(e)[:900]}</code>",
                reply_markup=info_buttons(),
            )
        except Exception:
            pass


@yuki.on_message(filters.command("updatehistory") & SUDOERS)
async def update_history_command(client, message):
    items = history()[:10]
    if not items:
        await message.reply_text("📜 <b>No update history found.</b>")
        return

    lines = ["📜 <b>ArchonMusic Update History</b>\n"]
    for item in items:
        when = time.strftime(
            "%Y-%m-%d %H:%M", time.localtime(item.get("time", 0))
        )
        lines.append(
            f"<b>{when}</b> • <code>{str(item.get('to', ''))[:7]}</code> • "
            f"<b>{item.get('status', 'unknown')}</b>"
        )
    await message.reply_text("\n".join(lines))


async def auto_update_checker(client):
    if not AUTO_CHECK:
        return

    await asyncio.sleep(60)
    while True:
        try:
            if not LOCK.locked():
                latest, message = await asyncio.to_thread(latest_commit)
                current = local_commit()
                if current and current != latest:
                    owner = getattr(config, "OWNER_ID", None)
                    state = read_state()
                    last_notice = state.get("last_notice_commit")
                    last_notice_time = int(state.get("last_notice_at", 0) or 0)

                    if owner and (
                        last_notice != latest
                        or time.time() - last_notice_time >= NOTIFY_COOLDOWN
                    ):
                        try:
                            await client.send_message(
                                owner,
                                "🔄 <b>New ArchonMusic update available.</b>\n\n"
                                f"<b>Current:</b> <code>{current[:7]}</code>\n"
                                f"<b>Latest:</b> <code>{latest[:7]}</code>\n\n"
                                f"📝 <b>{message[:500]}</b>",
                                reply_markup=update_buttons(),
                            )
                            save_state(
                                current,
                                last_notice_commit=latest,
                                last_notice_at=int(time.time()),
                            )
                        except Exception:
                            log.exception("Could not notify owner about update.")
        except Exception:
            log.exception("Automatic update check failed.")

        await asyncio.sleep(CHECK_INTERVAL)


@yuki.on_message(filters.command("restart") & SUDOERS)
async def restart_(client, message):
    response = await message.reply_text("ʀᴇsᴛᴀʀᴛɪɴɢ...")
    try:
        ac_chats = await get_active_chats()
        for x in ac_chats:
            try:
                await yuki.send_message(
                    chat_id=int(x),
                    text=(
                        f"{yuki.mention} ɪs ʀᴇsᴛᴀʀᴛɪɴɢ...\n\n"
                        "ʏᴏᴜ ᴄᴀɴ sᴛᴀʀᴛ ᴩʟᴀʏɪɴɢ ᴀɢᴀɪɴ ᴀғᴛᴇʀ 15-20 sᴇᴄᴏɴᴅs."
                    ),
                )
                await remove_active_chat(x)
                await remove_active_video_chat(x)
            except Exception:
                pass

        for folder in ("downloads", "raw_files", "cache"):
            path = ROOT / folder
            if path.exists():
                try:
                    shutil.rmtree(path)
                except Exception:
                    pass

        await response.edit_text(
            "» ʀᴇsᴛᴀʀᴛ ᴘʀᴏᴄᴇss sᴛᴀʀᴛᴇᴅ, ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ ғᴏʀ ғᴇᴡ sᴇᴄᴏɴᴅs ᴜɴᴛɪʟ ᴛʜᴇ ʙᴏᴛ sᴛᴀʀᴛs..."
        )
        await asyncio.sleep(1)
        await asyncio.to_thread(restart_bot)
    except Exception as e:
        log.exception("Restart failed.")
        await response.edit_text(f"❌ <b>Restart failed:</b> <code>{e}</code>")


# Plugins are imported from ArchonMusic.__main__ after the event loop is running.
# Starting the checker here is therefore safe and keeps the feature self-contained.
if AUTO_CHECK:
    try:
        asyncio.create_task(auto_update_checker(yuki))
    except RuntimeError:
        log.exception("Could not start automatic update checker.")
