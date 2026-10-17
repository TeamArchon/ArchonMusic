from typing import Union
import re

from pyrogram.enums import ButtonStyle
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from ArchonMusic import yuki

# Only these six sections are shown in the Help Center.
HELP_PAGES = ["hb1", "hb2", "hb6", "hb11", "hb14", "hb16"]

# Telegram Premium Custom Emoji IDs for button icons.
HELP_BUTTON_EMOJI = {
    "hb1": "6269458311381258421",   # Admin
    "hb2": "5291873529464122510",   # Auth
    "hb6": "4958861891549004661",   # C-Play
    "hb11": "5271721134889395048",  # Play
    "hb14": "5276352986535194063",  # Song
    "hb16": "6071242534128981419",  # Autoplay
}

NAV_EMOJI = {
    "prev": "5357165441909279397",
    "page": "4956260073375532310",
    "next": "5354815888639942120",
    "home": "4956525562483967357",
    "back": "5447506720316225765",
    "close": "6269316311172518259",
}


def _button(text, *, callback_data=None, url=None, style=None, emoji_id=None):
    kwargs = {"text": text}
    if callback_data is not None:
        kwargs["callback_data"] = callback_data
    if url is not None:
        kwargs["url"] = url
    if style is not None:
        kwargs["style"] = style
    if emoji_id is not None:
        kwargs["icon_custom_emoji_id"] = emoji_id
    return InlineKeyboardButton(**kwargs)


def _mark_button(_, START):
    if START:
        return _button(
            _["BACK_BUTTON"],
            callback_data="settings_back_helper",
            style=ButtonStyle.SUCCESS,
            emoji_id=NAV_EMOJI["back"],
        )
    return _button(
        _["CLOSE_BUTTON"],
        callback_data="close",
        style=ButtonStyle.DANGER,
        emoji_id=NAV_EMOJI["close"],
    )


def help_pannel(_, START: Union[bool, int] = None, page: int = 1):
    """Six-category Help Center menu with Premium Custom Emoji button icons."""
    sf = "1" if START else "0"
    rows = []

    for i in range(0, len(HELP_PAGES), 2):
        row = []
        for key in HELP_PAGES[i : i + 2]:
            row.append(
                _button(
                    text=_[f"H_B_{key[2:]}"],
                    callback_data=f"help_callback {key} {sf}",
                    style=ButtonStyle.PRIMARY,
                    emoji_id=HELP_BUTTON_EMOJI[key],
                )
            )
        rows.append(row)

    rows.append([_mark_button(_, START)])
    return InlineKeyboardMarkup(rows)


def help_topic_markup(_, page: int = 1, START: Union[bool, int] = None):
    """Video-style navigation with Premium Custom Emoji icons.

    Page 1: Prev hidden.
    Pages 2-5: Prev + page + Next.
    Page 6: Prev + page; Next hidden.
    Home is always present.
    """
    sf = "1" if START else "0"
    total = len(HELP_PAGES)
    page = max(1, min(page, total))

    navigation_row = []

    if page > 1:
        navigation_row.append(
            _button(
                text="\u2009",
                callback_data=f"help_page {page - 1} {sf}",
                style=ButtonStyle.PRIMARY,
                emoji_id=NAV_EMOJI["prev"],
            )
        )

    navigation_row.append(
        _button(
            text=f"{page}/{total}",
            callback_data="help_noop",
            style=ButtonStyle.DANGER,
            emoji_id=NAV_EMOJI["page"],
        )
    )

    if page < total:
        navigation_row.append(
            _button(
                text="\u2009",
                callback_data=f"help_page {page + 1} {sf}",
                style=ButtonStyle.PRIMARY,
                emoji_id=NAV_EMOJI["next"],
            )
        )

    return InlineKeyboardMarkup(
        [
            navigation_row,
            [
                _button(
                    text="Hᴏᴍᴇ",
                    callback_data=f"help_home {sf}",
                    style=ButtonStyle.SUCCESS,
                    emoji_id=NAV_EMOJI["home"],
                )
            ],
        ]
    )


def help_back_markup(_, page: int = 1, START: Union[bool, int] = None):
    return help_topic_markup(_, page, START)


def private_help_panel(_):
    buttons = [
        [
            _button(
                text=_["S_B_4"],
                url=f"https://t.me/{yuki.username}?start=help",
                emoji_id=NAV_EMOJI["home"],
            ),
        ],
    ]
    return buttons


def format_help_topic(
    text: str,
    emoji_id: str = "",
    fallback_emoji: str = "✨",
) -> str:
    """Format a Help page like the reference video.

    - The duplicated section heading from the source text is removed.
    - Every command line becomes a Telegram blockquote.
    - Every quoted command starts with the page's Premium Custom Emoji.
    - Explanatory/non-command text is moved below all commands and italicized.
    """
    command_lines = []
    normal_lines = []

    for raw in text.strip().splitlines():
        line = raw.strip()
        if not line:
            continue

        # Remove the original section heading; the page already has its own
        # title above this body.
        plain = re.sub(r"<[^>]+>", "", line).strip()
        if plain.endswith(":") and "/" not in plain:
            continue

        # Commands start with "/" after optional HTML markup.
        command_candidate = re.sub(r"^<[^>]+>", "", line).lstrip()
        if command_candidate.startswith("/"):
            command_lines.append(line)
        else:
            normal_lines.append(line)

    command_emoji = (
        f'<tg-emoji emoji-id="{emoji_id}">{fallback_emoji}</tg-emoji>'
        if emoji_id
        else fallback_emoji
    )

    rendered = [
        f"<blockquote>{command_emoji} {line}</blockquote>"
        for line in command_lines
    ]

    if normal_lines:
        if rendered:
            rendered.append("")
        rendered.extend(f"<i>{line}</i>" for line in normal_lines)

    return "\n\n".join(rendered)
