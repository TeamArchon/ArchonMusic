from pyrogram import types

from ArchonMusic import app, config, lang
from ArchonMusic.core.lang import lang_codes
from pyrogram.enums import ButtonStyle
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class Inline:
    def __init__(self):
        self.ikm = types.InlineKeyboardMarkup
        self.ikb = types.InlineKeyboardButton

    def cancel_dl(self, text) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(
                        text=text,
                        callback_data="cancel_dl",
                        icon_custom_emoji_id="6271611232457855630",  # ❌
                    )
                ]
            ]
        )

    def controls(
        self,
        chat_id: int,
        status: str = None,
        timer: str = None,
        remove: bool = False,
        more: bool = False,
        thumb: bool = None,
        lang: dict = None,
    ) -> types.InlineKeyboardMarkup:
        keyboard = []
        if status:
            keyboard.append(
                [
                    self.ikb(
                        text=status,
                        callback_data=f"controls status {chat_id}",
                        style=ButtonStyle.PRIMARY,
                        icon_custom_emoji_id="5767288287001580715",  # 💡
                    )
                ]
            )
        elif timer:
            keyboard.append(
                [
                    self.ikb(
                        text=timer,
                        callback_data=f"controls status {chat_id}",
                        style=ButtonStyle.PRIMARY,
                        icon_custom_emoji_id="5267421370114914946",  # ⏱
                    )
                ]
            )

        if not remove:
            if more:
                _on = "ᴏɴ ☜"
                _off = "ᴏғғ ☜"
                
                # Check ON/OFF state for thumb
                thumb_emoji = "6280269890821558384" if thumb else "6271611232457855630" # ✅ or ❌

                keyboard.append(
                    [
                        self.ikb(
                            text="Thumbnail",
                            callback_data="help thumb",
                            style=ButtonStyle.SUCCESS,
                            icon_custom_emoji_id="5409143496902716934",  # 🖼
                        ),
                        self.ikb(
                            text=_on if thumb else _off,
                            callback_data=f"controls cthumb {chat_id}",
                            style=ButtonStyle.SUCCESS,
                            icon_custom_emoji_id=thumb_emoji,
                        ),
                    ]
                )
                keyboard.append(
                    [
                        self.ikb(
                            text="ʙᴀᴄᴋ ⎋",
                            callback_data=f"controls back {chat_id}",
                            style=ButtonStyle.DANGER,
                            icon_custom_emoji_id="5352759161945867747",  # 🔙
                        )
                    ]
                )
            else:
                keyboard.append(
                    [
                        self.ikb(
                            text="▷", 
                            callback_data=f"controls resume {chat_id}",
                            icon_custom_emoji_id="5850346984501680054"  # ▶️
                        ),
                        self.ikb(
                            text="II", 
                            callback_data=f"controls pause {chat_id}",
                            icon_custom_emoji_id="6100514338274020922"  # ⏸️
                        ),
                        self.ikb(
                            text="⥁", 
                            callback_data=f"controls replay {chat_id}",
                            icon_custom_emoji_id="6030657343744644592"  # 🔁
                        ),
                        self.ikb(
                            text="‣‣I", 
                            callback_data=f"controls skip {chat_id}",
                            icon_custom_emoji_id="6172332822892647766"  # 🚀
                        ),
                        self.ikb(
                            text="▢", 
                            callback_data=f"controls stop {chat_id}",
                            icon_custom_emoji_id="6271674836628541366"  # 🛑
                        ),
                    ]
                )
                
        return self.ikm(keyboard)

    def help_markup(
        self, _lang: dict, back: bool = False
    ) -> types.InlineKeyboardMarkup:
        
        emoji_map = {
            "admins": "6271824284310573725", # 👮‍♂️
            "auth": "5884366771913233289",   # 👤
            "blist": "6100397162976252509",  # 🚫
            "lang": "6269490656779965144",   # 🌐
            "ping": "6246741653827095091",   # 🏓
            "play": "5850346984501680054",   # ▶️
            "queue": "5222281328258465590",  # 📜
            "stats": "5936143551854285132",  # 📊
            "sudo": "6237864166879663987",   # 👑
            "thumb": "5409143496902716934",  # 🖼
            "vclog": "5258077307985207053",  # 📹
            "autoplay": "6030657343744644592" # 🔁
        }

        if back:
            rows = [
                [
                    self.ikb(
                        text=_lang["back"],
                        callback_data="help back",
                        style=ButtonStyle.DANGER,
                        icon_custom_emoji_id="5352759161945867747",  # 🔙
                    ),
                ]
            ]
        else:
            rows = []
                
            cbs = [
                "admins", "auth", "blist", "lang", "ping", "play", 
                "queue", "stats", "sudo", "thumb", "vclog", "autoplay",
            ]
            
            buttons = [
                self.ikb(
                    text=_lang[f"help_{cb}"],
                    callback_data=f"help {cb}",
                    style=ButtonStyle.SUCCESS,
                    icon_custom_emoji_id=emoji_map.get(cb, "6100424015111787987"), # Default 📌
                )
                for cb in cbs
            ]
            rows += [buttons[i : i + 3] for i in range(0, len(buttons), 3)]
            rows.append(
                [
                    self.ikb(
                        text=_lang["back"],
                        callback_data="help home",
                        style=ButtonStyle.DANGER,
                        icon_custom_emoji_id="5352759161945867747",  # 🔙
                    ),
                ]
            )

        return self.ikm(rows)

    def song_markup(self, vid_id: str) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(
                        text="Audio", 
                        callback_data=f"song_download audio {vid_id}",
                        icon_custom_emoji_id="5409025823388741707"  # 🎵
                    ),
                    self.ikb(
                        text="Video", 
                        callback_data=f"song_download video {vid_id}",
                        icon_custom_emoji_id="5937999673510858217"  # 🎞
                    ),
                ],
                [
                    self.ikb(
                        text="Close", 
                        callback_data="help close",
                        icon_custom_emoji_id="6271611232457855630"  # ❌
                    ),
                ],
            ]
        )

    def lang_markup(self, _lang: str) -> types.InlineKeyboardMarkup:
        langs = lang.get_languages()

        buttons = [
            self.ikb(
                text=f"{name} ({code}) {'✔️' if code == _lang else ''}",
                callback_data=f"lang_change {code}",
                style=ButtonStyle.PRIMARY,
                icon_custom_emoji_id="6269490656779965144",  # 🌐
            )
            for code, name in langs.items()
        ]
        rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
        return self.ikm(rows)

    def ping_markup(self, text: str) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(
                        text=text,
                        url=config.SUPPORT_CHAT,
                        style=ButtonStyle.PRIMARY,
                        icon_custom_emoji_id="6246741653827095091",  # 🏓
                    )
                ]
            ]
        )

    def play_queued(
        self, chat_id: int, item_id: str, _text: str
    ) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(
                        text=_text,
                        callback_data=f"controls force {chat_id} {item_id}",
                        style=ButtonStyle.SUCCESS,
                        icon_custom_emoji_id="6280269890821558384",  # ✅
                    )
                ]
            ]
        )

    def queue_markup(
        self, chat_id: int, _text: str, playing: bool
    ) -> types.InlineKeyboardMarkup:
        _action = "pause" if playing else "resume"
        _emoji = "6100514338274020922" if playing else "5850346984501680054"  # ⏸️ or ▶️
        return self.ikm(
            [
                [
                    self.ikb(
                        text=_text, 
                        callback_data=f"controls {_action} {chat_id} q",
                        icon_custom_emoji_id=_emoji
                    )
                ]
            ]
        )

    def settings_markup(
        self,
        lang: dict,
        admin_only: bool,
        cmd_delete: bool,
        vclogger: bool,
        thumbnail: bool,
        autoplay: bool,
        language: str,
        chat_id: int,
    ) -> types.InlineKeyboardMarkup:
        _on = "ᴏɴ ☜"
        _off = "ᴏғғ ☜"
        
        def get_btn_emoji(state):
            return "6280269890821558384" if state else "6271611232457855630" # ✅ or ❌
            
        return self.ikm(
            [
                [
                    self.ikb(
                        text=lang["play_mode"] + " ➜",
                        callback_data="settings",
                        style=ButtonStyle.SUCCESS,
                        icon_custom_emoji_id="6271824284310573725",  # 👮‍♂️
                    ),
                    self.ikb(
                        text=_on if admin_only else _off,
                        callback_data="settings play",
                        style=ButtonStyle.SUCCESS,
                        icon_custom_emoji_id=get_btn_emoji(admin_only),
                    ),
                ],
                [
                    self.ikb(
                        text=lang["cmd_delete"] + " ➜",
                        callback_data="settings",
                        style=ButtonStyle.SUCCESS,
                        icon_custom_emoji_id="5408832111773757273",  # 🗑
                    ),
                    self.ikb(
                        text=_on if cmd_delete else _off,
                        callback_data="settings delete",
                        style=ButtonStyle.SUCCESS,
                        icon_custom_emoji_id=get_btn_emoji(cmd_delete),
                    ),
                ],
                [
                    self.ikb(
                        text=lang["vclogger"] + " ➜",
                        callback_data="settings",
                        style=ButtonStyle.SUCCESS,
                        icon_custom_emoji_id="5258077307985207053",  # 📹
                    ),
                    self.ikb(
                        text=_on if vclogger else _off,
                        callback_data="settings vclog",
                        style=ButtonStyle.SUCCESS,
                        icon_custom_emoji_id=get_btn_emoji(vclogger),
                    ),
                ],
                [
                    self.ikb(
                        text=lang["thumbnail"] + " ➜",
                        callback_data="settings",
                        style=ButtonStyle.SUCCESS,
                        icon_custom_emoji_id="5409143496902716934",  # 🖼
                    ),
                    self.ikb(
                        text=_on if thumbnail else _off,
                        callback_data="settings thumb",
                        style=ButtonStyle.SUCCESS,
                        icon_custom_emoji_id=get_btn_emoji(thumbnail),
                    ),
                ],
                [
                    self.ikb(
                        text=lang["autoplay"] + " ➜",
                        callback_data="settings",
                        style=ButtonStyle.SUCCESS,
                        icon_custom_emoji_id="6030657343744644592",  # 🔁
                    ),
                    self.ikb(
                        text=_on if autoplay else _off,
                        callback_data="settings autoplay",
                        style=ButtonStyle.SUCCESS,
                        icon_custom_emoji_id=get_btn_emoji(autoplay),
                    ),
                ],
                [
                    self.ikb(
                        text=lang["language"] + " ➜",
                        callback_data="settings",
                        style=ButtonStyle.SUCCESS,
                        icon_custom_emoji_id="6269490656779965144",  # 🌐
                    ),
                    self.ikb(
                        text=lang_codes[language],
                        callback_data="language",
                        style=ButtonStyle.SUCCESS,
                        icon_custom_emoji_id="6269490656779965144",  # 🌐
                    ),
                ],
                [
                    self.ikb(
                        text="close",
                        callback_data="settings close",
                        style=ButtonStyle.PRIMARY,
                        icon_custom_emoji_id="6271611232457855630",  # ❌
                    ),
                ],
            ]
        )

    def start_key(
        self, lang: dict, private: bool = False
    ) -> types.InlineKeyboardMarkup:
        rows = [
            [
                self.ikb(
                    text=lang["add_me"],
                    url=f"https://t.me/{app.username}?startgroup=true",
                    style=ButtonStyle.SUCCESS,
                    icon_custom_emoji_id="6100125944381444896",  # ➕
                )
            ],
            [
                self.ikb(
                    text=lang["support"],
                    url=config.SUPPORT_CHAT,
                    style=ButtonStyle.PRIMARY,
                    icon_custom_emoji_id="5258337316715373336",  # 🤙
                ),
                self.ikb(
                    text=lang["channel"],
                    url=config.SUPPORT_CHANNEL,
                    style=ButtonStyle.DANGER,
                    icon_custom_emoji_id="6039381989985882045",  # 📢
                ),
            ],
            [
                self.ikb(
                    text=lang["help"],
                    callback_data="help",
                    style=ButtonStyle.PRIMARY,
                    icon_custom_emoji_id="5260512129240276089",  # 📚
                ),
                self.ikb(
                    text="Tʜᴇ Sʜɪᴠ",
                    user_id=config.OWNER_ID,
                    style=ButtonStyle.DANGER,
                    icon_custom_emoji_id="6237864166879663987",  # 👑
                ),
            ],
        ]
        if not private:
            rows += [
                [
                    self.ikb(
                        text=lang["language"],
                        callback_data="language",
                        style=ButtonStyle.PRIMARY,
                        icon_custom_emoji_id="6269490656779965144",  # 🌐
                    )
                ]
            ]
        return self.ikm(rows)

    def yt_key(self, link: str) -> types.InlineKeyboardMarkup:
        return self.ikm(
            [
                [
                    self.ikb(
                        text="Copy", 
                        copy_text=link,
                        icon_custom_emoji_id="5778455936410588193"  # 🔗
                    ),
                    self.ikb(
                        text="Youtube", 
                        url=link,
                        icon_custom_emoji_id="5409143496902716934"  # 🖼 -> (Or any video equivalent)
                    ),
                ],
            ]
        )
