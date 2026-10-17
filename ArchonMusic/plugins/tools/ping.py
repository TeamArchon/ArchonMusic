import time
from datetime import timedelta

from pyrogram import enums, filters, types
from pyrogram.types import Message

from ArchonMusic import yuki
from ArchonMusic.core.call import Archon
from ArchonMusic.utils import bot_sys_stats
from ArchonMusic.utils.decorators.language import language
from config import BANNED_USERS


def _paragraph(text):
    return types.InputRichBlockParagraph(text=text)


def _heading(text):
    return types.InputRichBlockPullQuotation(
        text=types.RichTextBold(text=text)
    )


def _bold_paragraph(label, value):
    return types.InputRichBlockParagraph(
        text=[
            types.RichTextBold(text=label),
            str(value),
        ]
    )


def _format_uptime(value):
    if isinstance(value, (int, float)):
        return str(timedelta(seconds=max(0, int(value))))
    return str(value)


def _format_ping(value):
    if isinstance(value, (int, float)):
        return f"{value:.2f} ms"
    return str(value)


def build_ping_blocks(ping, telegram_ping, uptime, cpu, ram, disk):
    return [
        _paragraph(
            [types.RichTextBold(text="ArchonMusic — Pɪɴɢ Sᴛᴀᴛᴜs")]
        ),
        _heading("Pɪɴɢ"),
        _bold_paragraph("• Rᴇsᴘᴏɴsᴇ: ", _format_ping(ping)),
        _bold_paragraph("• Tᴇʟᴇɢʀᴀᴍ: ", _format_ping(telegram_ping)),
        _heading("Sʏsᴛᴇᴍ"),
        _bold_paragraph("• CPU: ", f"{cpu}%"),
        _bold_paragraph("• RAM: ", f"{ram}%"),
        _bold_paragraph("• Dɪsᴋ: ", f"{disk}%"),
        _heading("Rᴜɴᴛɪᴍᴇ"),
        _bold_paragraph("• Uᴘᴛɪᴍᴇ: ", _format_uptime(uptime)),
        _heading("Sᴛᴀᴛᴜs"),
        _bold_paragraph("• Sᴛᴀᴛᴜs: ", "🟢 Oɴʟɪɴᴇ"),
        _paragraph("────────────────────────"),
        types.InputRichBlockButtons(
            buttons=[
                types.RichMessageButton(
                    text="💬 Cʜᴀᴛ",
                    style=enums.ButtonStyle.SUCCESS,
                    callback_data="ping_chat",
                )
            ],
            align="center",
        ),
    ]


@yuki.on_message(filters.command(["ping", "alive"]) & ~BANNED_USERS)
@language
async def ping_com(client, message: Message, _):
    start = time.perf_counter()
    telegram_ping = await Archon.ping()
    UP, CPU, RAM, DISK = await bot_sys_stats()
    ping = (time.perf_counter() - start) * 1000

    blocks = build_ping_blocks(
        ping,
        telegram_ping,
        UP,
        CPU,
        RAM,
        DISK,
    )

    rich_message = types.InputRichMessage(blocks=blocks)

    await client.send_rich_message(
        message.chat.id,
        rich_message=rich_message,
    )
