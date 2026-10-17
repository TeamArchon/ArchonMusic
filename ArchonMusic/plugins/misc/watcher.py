from pyrogram import filters
from pyrogram.types import Message

from ArchonMusic import yuki
from ArchonMusic.core.call import Archon

welcome = 20
close = 30


@yuki.on_message(filters.video_chat_started, group=welcome)
@yuki.on_message(filters.video_chat_ended, group=close)
async def welcome(_, message: Message):
    await Archon.stop_stream_force(message.chat.id)
