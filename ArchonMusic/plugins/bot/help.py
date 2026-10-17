import random
from typing import Union

from pyrogram import filters, types
from pyrogram.errors import MessageNotModified
from pyrogram.types import InlineKeyboardMarkup, Message, InputMediaPhoto

from ArchonMusic import yuki
from ArchonMusic.utils import help_pannel
from ArchonMusic.utils.database import get_lang
from ArchonMusic.utils.decorators.language import LanguageStart, languageCB
from ArchonMusic.utils.inline.help import format_help_topic, help_topic_markup, private_help_panel
from ArchonMusic.utils.inline.start import private_panel
from config import BANNED_USERS, START_IMG_URL, SUPPORT_CHAT
from strings import get_string, helpers

MESSAGE_EFFECTS = [
    5107584321108051014,
    5159385139981059251,
    5104841245755180586,
    5046509860389126442,
]

HELP_TOPICS = {
    "hb1": helpers.HELP_1,
    "hb2": helpers.HELP_2,
    "hb6": helpers.HELP_6,
    "hb11": helpers.HELP_11,
    "hb14": helpers.HELP_14,
    "hb16": helpers.HELP_16,
}

HELP_PAGES = ["hb1", "hb2", "hb6", "hb11", "hb14", "hb16"]
PREMIUM_EMOJI = {
    "hb1": ("6269458311381258421", "👮‍♂️"),
    "hb2": ("5291873529464122510", "👤"),
    "hb6": ("4958861891549004661", "▶️"),
    "hb11": ("5271721134889395048", "🎵"),
    "hb14": ("5276352986535194063", "🎙️"),
    "hb16": ("6071242534128981419", "🔁"),
}

HELP_TITLES = {
    "hb1": "Aᴅᴍɪɴ Cᴏᴍᴍᴀɴᴅs",
    "hb2": "Aᴜᴛʜ Cᴏᴍᴍᴀɴᴅs",
    "hb6": "C-Pʟᴀʏ Cᴏᴍᴍᴀɴᴅs",
    "hb11": "Pʟᴀʏ Cᴏᴍᴍᴀɴᴅs",
    "hb14": "Sᴏɴɢ Cᴏᴍᴍᴀɴᴅs",
    "hb16": "Aᴜᴛᴏᴘʟᴀʏ Cᴏᴍᴍᴀɴᴅs",
}

HELP_CENTER_EMOJI = '<tg-emoji emoji-id="4956560313064358770">💡</tg-emoji>'


def _topic_page(topic):
    """Return the 1-based Help Center page number for a topic key."""
    try:
        return HELP_PAGES.index(topic) + 1
    except ValueError:
        return 1


def _topic_for_page(page):
    """Return the Help Center topic key for a 1-based page number."""
    page = max(1, min(int(page), len(HELP_PAGES)))
    return HELP_PAGES[page - 1]


def _page_text(topic, page):
    emoji_id, fallback = PREMIUM_EMOJI[topic]
    icon = f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    emoji_id, fallback = PREMIUM_EMOJI[topic]
    commands = format_help_topic(
        HELP_TOPICS[topic],
        emoji_id=emoji_id,
        fallback_emoji=fallback,
    )
    return (
        f"<b>{HELP_CENTER_EMOJI} Hᴇʟᴘ Cᴇɴᴛᴇʀ {page}/{len(HELP_PAGES)}</b>\n\n"
        f"<b>{icon} {HELP_TITLES[topic]}</b>\n\n{commands}"
    )


async def _show_help_categories(CallbackQuery, _, START=False):
    """Show the six-category menu. Used by /help and Start -> Help."""
    keyboard = help_pannel(_, START, 1)
    try:
        await CallbackQuery.edit_message_caption(
            caption=_["help_1"].format(SUPPORT_CHAT), reply_markup=keyboard
        )
    except MessageNotModified:
        pass
    except Exception:
        # Fallback for a text message (for example if the old Help menu is still open).
        try:
            await CallbackQuery.edit_message_text(
                _["help_1"].format(SUPPORT_CHAT), reply_markup=keyboard
            )
        except MessageNotModified:
            pass


async def _send_start_page(client, chat_id, _, message_to_replace=None):
    """Return to the real private /start page."""
    caption = _["start_2"].format(
        message_to_replace.from_user.mention if message_to_replace else "",
        yuki.mention,
    )
    keyboard = InlineKeyboardMarkup(private_panel(_))

    if message_to_replace is not None:
        try:
            await message_to_replace.delete()
        except Exception:
            pass

    await client.send_photo(
        chat_id=chat_id,
        photo=START_IMG_URL,
        caption=caption,
        reply_markup=keyboard,
        effect_id=random.choice(MESSAGE_EFFECTS),
    )


@yuki.on_message(filters.command(["help"]) & filters.private & ~BANNED_USERS)
async def helper_private_message(client: yuki, message: Message):
    try:
        await message.delete()
    except Exception:
        pass

    language = await get_lang(message.chat.id)
    _ = get_string(language)
    # /help opens directly on the first paginated Help Center page.
    topic = HELP_PAGES[0]
    text = _page_text(topic, 1)
    keyboard = help_topic_markup(_, 1, False)
    await client.send_message(
        chat_id=message.chat.id,
        text=text,
        reply_markup=keyboard,
    )


@yuki.on_callback_query(filters.regex(r"^settings_back_helper$") & ~BANNED_USERS)
async def helper_private_back(client: yuki, CallbackQuery: types.CallbackQuery):
    try:
        await CallbackQuery.answer()
    except Exception:
        pass

    chat_id = CallbackQuery.message.chat.id
    language = await get_lang(chat_id)
    _ = get_string(language)

    # Help & Commands from the real Start page opens directly on page 1.
    # The Start page is a photo message, so Telegram cannot convert it into
    # a text message. Send the Help page first, then remove the old Start page.
    topic = HELP_PAGES[0]
    text = _page_text(topic, 1)
    keyboard = help_topic_markup(_, 1, True)
    try:
        await client.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=keyboard,
        )
    finally:
        try:
            await CallbackQuery.message.delete()
        except Exception:
            pass


@yuki.on_message(filters.command(["help"]) & filters.group & ~BANNED_USERS)
@LanguageStart
async def help_com_group(client, message: Message, _):
    keyboard = private_help_panel(_)
    await message.reply_text(_["help_2"], reply_markup=InlineKeyboardMarkup(keyboard))


@yuki.on_callback_query(filters.regex(r"^help_callback\s") & ~BANNED_USERS)
@languageCB
async def helper_cb(client, CallbackQuery, _):
    parts = CallbackQuery.data.strip().split()
    if len(parts) < 2:
        return await CallbackQuery.answer()

    cb = parts[1]
    sf = parts[2] if len(parts) > 2 else "0"
    START = sf == "1"

    if cb not in HELP_PAGES:
        return await CallbackQuery.answer("This help section is unavailable.", show_alert=True)

    page = _topic_page(cb)
    text = _page_text(cb, page)
    keyboard = help_topic_markup(_, page, START)

    # A photo message cannot be converted into a text message with Telegram's
    # edit API. Send the command page first, then delete the old Help Center
    # message. This prevents the visible blank/deleted-message gap.
    try:
        await client.send_message(
            chat_id=CallbackQuery.message.chat.id,
            text=text,
            reply_markup=keyboard,
        )
    finally:
        try:
            await CallbackQuery.message.delete()
        except Exception:
            pass
        try:
            await CallbackQuery.answer()
        except Exception:
            pass


@yuki.on_callback_query(filters.regex(r"^help_page\s") & ~BANNED_USERS)
@languageCB
async def help_page_cb(client, CallbackQuery, _):
    parts = CallbackQuery.data.split()
    try:
        page = int(parts[1])
    except (IndexError, ValueError):
        return await CallbackQuery.answer()

    sf = parts[2] if len(parts) > 2 else "0"
    START = sf == "1"

    if page < 1 or page > len(HELP_PAGES):
        return await CallbackQuery.answer()

    topic = _topic_for_page(page)
    keyboard = help_topic_markup(_, page, START)
    try:
        await CallbackQuery.edit_message_text(
            _page_text(topic, page), reply_markup=keyboard
        )
    except MessageNotModified:
        pass
    finally:
        try:
            await CallbackQuery.answer()
        except Exception:
            pass


@yuki.on_callback_query(filters.regex(r"^help_home\s") & ~BANNED_USERS)
@languageCB
async def help_home_cb(client, CallbackQuery, _):
    # Home must return to the real bot Start page, not the six-category menu.
    try:
        await CallbackQuery.answer()
    except Exception:
        pass

    chat_id = CallbackQuery.message.chat.id
    await _send_start_page(
        client,
        chat_id,
        _,
        message_to_replace=CallbackQuery.message,
    )


@yuki.on_callback_query(filters.regex(r"^help_noop$") & ~BANNED_USERS)
async def help_noop_cb(client, CallbackQuery):
    try:
        await CallbackQuery.answer()
    except Exception:
        pass
