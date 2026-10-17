from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def stats_buttons(_, status=None):
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text=_["CLOSE_BUTTON"], callback_data="close")]]
    )


def back_stats_buttons(_):
    return stats_buttons(_)
