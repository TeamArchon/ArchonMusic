from pyrogram import filters
from pyrogram.types import Message

from ArchonMusic import yuki
from ArchonMusic.core.call import Archon
from ArchonMusic.utils.database import is_music_playing, music_on
from ArchonMusic.utils.decorators import AdminRightsCheck
from ArchonMusic.utils.inline import close_markup
from ArchonMusic.utils.rich_stream import set_now_playing_state
from config import BANNED_USERS


@yuki.on_message(filters.command(["resume", "cresume"]) & filters.group & ~BANNED_USERS)
@AdminRightsCheck
async def resume_com(cli, message: Message, _, chat_id):
    if await is_music_playing(chat_id):
        return await message.reply_text(_["admin_3"])
    await music_on(chat_id)
    await Archon.resume_stream(chat_id)
    await set_now_playing_state(chat_id, playing=True)
    await message.reply_text(
        _["admin_4"].format(message.from_user.mention), reply_markup=close_markup(_)
    )
