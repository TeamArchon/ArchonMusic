import asyncio

from ArchonMusic.misc import db
from ArchonMusic.utils.database import get_active_chats, is_music_playing
from ArchonMusic.utils.stream.autoplay import schedule_prefetch


async def timer():
    while not await asyncio.sleep(1):
        active_chats = await get_active_chats()
        for chat_id in active_chats:
            if not await is_music_playing(chat_id):
                continue
            playing = db.get(chat_id)
            if not playing:
                continue
            duration = int(playing[0]["seconds"])
            if duration == 0:
                continue
            if db[chat_id][0]["played"] >= duration:
                continue
            db[chat_id][0]["played"] += 1
            try:
                await schedule_prefetch(chat_id, playing)
            except Exception:
                pass


asyncio.create_task(timer())
