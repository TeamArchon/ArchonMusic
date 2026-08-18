import os
import sys
import shutil
import asyncio

from pyrogram import filters, types

from ArchonMusic import app, db, lang, stop


@app.on_message(filters.command(["logs"]) & app.sudoers)
@lang.language()
async def _logs(_, m: types.Message):
    sent = await m.reply_text(m.lang["log_fetch"])
    if not os.path.exists("log.txt"):
        return await sent.edit_text(m.lang["log_not_found"])
    await sent.edit_media(
        media=types.InputMediaDocument(
            media="log.txt",
            caption=m.lang["log_sent"].format(app.name),
        )
    )


@app.on_message(filters.command(["logger"]) & app.sudoers)
@lang.language()
async def _logger(_, m: types.Message):
    if len(m.command) < 2:
        return await m.reply_text(m.lang["logger_usage"].format(m.command[0]))
    if m.command[1] not in ("on", "off"):
        return await m.reply_text(m.lang["logger_usage"].format(m.command[0]))

    if m.command[1] == "on":
        await db.set_logger(True)
        await m.reply_text(m.lang["logger_on"])
    else:
        await db.set_logger(False)
        await m.reply_text(m.lang["logger_off"])


@app.on_message(filters.command(["restart"]) & app.sudoers)
@lang.language()
async def _restart(_, m: types.Message):
    sent = await m.reply_text(m.lang["restarting"])

    for directory in ["cache", "downloads"]:
        shutil.rmtree(directory, ignore_errors=True)

    await sent.edit_text(m.lang["restarted"])
    asyncio.create_task(stop())
    await asyncio.sleep(2)

    try: os.remove("log.txt")
    except Exception: pass

    os.execl(sys.executable, sys.executable, "-m", "ArchonMusic")


# --- NAYA UPDATE COMMAND YAHAN HAI ---
@app.on_message(filters.command(["update"]) & app.sudoers)
async def _update(_, m: types.Message):
    sent = await m.reply_text("🔄 **Checking for updates from GitHub...**")

    try:
        # Git pull command run karne ke liye subprocess ka use
        process = await asyncio.create_subprocess_shell(
            "git pull",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        output = stdout.decode().strip()
        error = stderr.decode().strip()

        # Agar bot pehle se updated hai
        if "Already up to date." in output:
            return await sent.edit_text("✅ **Bot is already up to date with GitHub.**")

        # Agar git pull me koi error aati hai
        if process.returncode != 0:
            return await sent.edit_text(f"❌ **Update failed:**\n\n`{error}`")

        # Update successful hone par restart logic
        await sent.edit_text(f"✅ **Successfully pulled updates!**\n\n`{output}`\n\n🔄 **Restarting bot now baby...**")

        # Cache aur downloads folder clean karna (jaisa restart me hai)
        for directory in ["cache", "downloads"]:
            shutil.rmtree(directory, ignore_errors=True)

        asyncio.create_task(stop())
        await asyncio.sleep(2)

        try: 
            os.remove("log.txt")
        except Exception: 
            pass

        # Bot ko naye code ke sath run karna
        os.execl(sys.executable, sys.executable, "-m", "ArchonMusic")

    except Exception as e:
        await sent.edit_text(f"❌ **Error during update:**\n`{e}`")
