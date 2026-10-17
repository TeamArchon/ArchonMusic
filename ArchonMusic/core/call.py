import asyncio
import os
import wave
from datetime import datetime, timedelta
from typing import Union

from pyrogram import Client
from pytgcalls import PyTgCalls, StreamType
from pytgcalls.exceptions import (
    AlreadyJoinedError,
    NoActiveGroupCall,
    TelegramServerError,
)
from pytgcalls.types import Update
from pytgcalls.types.input_stream import AudioPiped, AudioVideoPiped
from pytgcalls.types.input_stream.quality import HighQualityAudio, MediumQualityVideo
from pytgcalls.types.stream import StreamAudioEnded

import config
from ArchonMusic import LOGGER, YouTube, yuki
from ArchonMusic.misc import db
from ArchonMusic.utils.database import (
    add_active_chat,
    add_active_video_chat,
    get_lang,
    get_loop,
    group_assistant,
    is_active_chat,
    is_autoend,
    music_on,
    remove_active_chat,
    remove_active_video_chat,
    set_loop,
)
from ArchonMusic.utils.exceptions import AssistantErr
from ArchonMusic.utils.formatters import check_duration, seconds_to_min, speed_converter
from ArchonMusic.utils.rich_stream import send_now_playing_rich
from ArchonMusic.utils.stream.autoclear import auto_clean
from ArchonMusic.utils.stream.autoplay import discard_prefetch, try_autoplay
from ArchonMusic.utils.stream.history import record_played
from ArchonMusic.utils.thumbnails import get_thumb
from strings import get_string

autoend = {}
counter = {}


async def _clear_(chat_id):
    db[chat_id] = []
    discard_prefetch(chat_id)
    await remove_active_video_chat(chat_id)
    await remove_active_chat(chat_id)


PLACEHOLDER_SECONDS = 120

_video_placeholder_lock = asyncio.Lock()


def _silence_path():
    path = os.path.abspath(os.path.join("cache", "silence.wav"))
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with wave.open(path, "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(1)
            f.setframerate(8000)
            f.writeframes(b"\x80" * 8000 * PLACEHOLDER_SECONDS)
    return path


async def _silence_video_path():
    path = os.path.abspath(os.path.join("cache", "silence.mp4"))
    if os.path.isfile(path) and os.path.getsize(path) > 0:
        return path
    async with _video_placeholder_lock:
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            return path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=320x180:r=15",
            "-f", "lavfi", "-i", "anullsrc=r=8000:cl=mono",
            "-t", str(PLACEHOLDER_SECONDS),
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", "-f", "mp4", tmp,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate()
        if proc.returncode != 0 or not os.path.isfile(tmp) or os.path.getsize(tmp) == 0:
            if os.path.isfile(tmp):
                os.remove(tmp)
            raise RuntimeError("silent video placeholder generation failed")
        os.replace(tmp, path)
    return path


class Call(PyTgCalls):
    def __init__(self):
        self.userbot1 = Client(
            name="YukiAss1",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING1),
        )
        self.one = PyTgCalls(
            self.userbot1,
            cache_duration=100,
        )
        self.userbot2 = Client(
            name="YukiAss2",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING2),
        )
        self.two = PyTgCalls(
            self.userbot2,
            cache_duration=100,
        )
        self.userbot3 = Client(
            name="YukiAss3",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING3),
        )
        self.three = PyTgCalls(
            self.userbot3,
            cache_duration=100,
        )
        self.userbot4 = Client(
            name="YukiAss4",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING4),
        )
        self.four = PyTgCalls(
            self.userbot4,
            cache_duration=100,
        )
        self.userbot5 = Client(
            name="YukiAss5",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=str(config.STRING5),
        )
        self.five = PyTgCalls(
            self.userbot5,
            cache_duration=100,
        )
        self._prejoin_tasks = {}
        self._prejoin_video = {}
        self._chat_locks = {}

    def chat_lock(self, chat_id: int):
        lock = self._chat_locks.get(chat_id)
        if lock is None:
            lock = asyncio.Lock()
            self._chat_locks[chat_id] = lock
        return lock

    async def _assistant_join(self, assistant, chat_id: int, stream, _):
        try:
            await assistant.join_group_call(
                chat_id,
                stream,
                stream_type=StreamType().pulse_stream,
            )
        except NoActiveGroupCall:
            raise AssistantErr(_["call_8"])
        except AlreadyJoinedError:
            raise AssistantErr(_["call_9"])
        except TelegramServerError:
            raise AssistantErr(_["call_10"])

    async def _run_prejoin(self, chat_id: int, video: bool = False):
        assistant = await group_assistant(self, chat_id)
        _ = get_string(await get_lang(chat_id))
        used_video = False
        if video:
            try:
                video_path = await _silence_video_path()
                stream = AudioVideoPiped(
                    video_path,
                    audio_parameters=HighQualityAudio(),
                    video_parameters=MediumQualityVideo(),
                )
                used_video = True
            except Exception:
                stream = AudioPiped(_silence_path(), audio_parameters=HighQualityAudio())
        else:
            stream = AudioPiped(_silence_path(), audio_parameters=HighQualityAudio())
        self._prejoin_video[chat_id] = used_video
        await self._assistant_join(assistant, chat_id, stream, _)

    async def prejoin_start(self, chat_id: int, video: bool = False) -> bool:
        if chat_id in self._prejoin_tasks or await is_active_chat(chat_id):
            return False
        self._prejoin_tasks[chat_id] = asyncio.ensure_future(
            self._run_prejoin(chat_id, video)
        )
        return True

    async def await_prejoin(self, chat_id: int):
        task = self._prejoin_tasks.get(chat_id)
        if task is not None:
            await asyncio.shield(task)

    async def prejoin_settle(self, chat_id: int):
        async with self.chat_lock(chat_id):
            task = self._prejoin_tasks.pop(chat_id, None)
            self._prejoin_video.pop(chat_id, None)
            if task is None:
                return
            try:
                await task
            except Exception:
                return
            try:
                assistant = await group_assistant(self, chat_id)
                await assistant.leave_group_call(chat_id)
            except Exception:
                pass

    async def pause_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        await assistant.pause_stream(chat_id)

    async def resume_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        await assistant.resume_stream(chat_id)

    async def stop_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        try:
            await _clear_(chat_id)
            await assistant.leave_group_call(chat_id)
        except:
            pass

    async def stop_stream_force(self, chat_id: int):
        try:
            if config.STRING1:
                await self.one.leave_group_call(chat_id)
        except:
            pass
        try:
            if config.STRING2:
                await self.two.leave_group_call(chat_id)
        except:
            pass
        try:
            if config.STRING3:
                await self.three.leave_group_call(chat_id)
        except:
            pass
        try:
            if config.STRING4:
                await self.four.leave_group_call(chat_id)
        except:
            pass
        try:
            if config.STRING5:
                await self.five.leave_group_call(chat_id)
        except:
            pass
        try:
            await _clear_(chat_id)
        except:
            pass

    async def speedup_stream(self, chat_id: int, file_path, speed, playing):
        assistant = await group_assistant(self, chat_id)
        if str(speed) != str("1.0"):
            base = os.path.basename(file_path)
            chatdir = os.path.join(os.getcwd(), "playback", str(speed))
            if not os.path.isdir(chatdir):
                os.makedirs(chatdir)
            out = os.path.join(chatdir, base)
            if not os.path.isfile(out):
                if str(speed) == str("0.5"):
                    vs = 2.0
                if str(speed) == str("0.75"):
                    vs = 1.35
                if str(speed) == str("1.5"):
                    vs = 0.68
                if str(speed) == str("2.0"):
                    vs = 0.5
                proc = await asyncio.create_subprocess_shell(
                    cmd=(
                        "ffmpeg "
                        "-i "
                        f"{file_path} "
                        "-filter:v "
                        f"setpts={vs}*PTS "
                        "-filter:a "
                        f"atempo={speed} "
                        f"{out}"
                    ),
                    stdin=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
            else:
                pass
        else:
            out = file_path
        dur = await asyncio.get_event_loop().run_in_executor(None, check_duration, out)
        dur = int(dur)
        played, con_seconds = speed_converter(playing[0]["played"], speed)
        duration = seconds_to_min(dur)
        stream = (
            AudioVideoPiped(
                out,
                audio_parameters=HighQualityAudio(),
                video_parameters=MediumQualityVideo(),
                additional_ffmpeg_parameters=f"-ss {played} -to {duration}",
            )
            if playing[0]["streamtype"] == "video"
            else AudioPiped(
                out,
                audio_parameters=HighQualityAudio(),
                additional_ffmpeg_parameters=f"-ss {played} -to {duration}",
            )
        )
        if str(db[chat_id][0]["file"]) == str(file_path):
            await assistant.change_stream(chat_id, stream)
        else:
            raise AssistantErr("Umm")
        if str(db[chat_id][0]["file"]) == str(file_path):
            exis = (playing[0]).get("old_dur")
            if not exis:
                db[chat_id][0]["old_dur"] = db[chat_id][0]["dur"]
                db[chat_id][0]["old_second"] = db[chat_id][0]["seconds"]
            db[chat_id][0]["played"] = con_seconds
            db[chat_id][0]["dur"] = duration
            db[chat_id][0]["seconds"] = dur
            db[chat_id][0]["speed_path"] = out
            db[chat_id][0]["speed"] = speed

    async def force_stop_stream(self, chat_id: int):
        assistant = await group_assistant(self, chat_id)
        try:
            check = db.get(chat_id)
            check.pop(0)
        except:
            pass
        await remove_active_video_chat(chat_id)
        await remove_active_chat(chat_id)
        try:
            await assistant.leave_group_call(chat_id)
        except:
            pass

    async def skip_stream(
        self,
        chat_id: int,
        link: str,
        video: Union[bool, str] = None,
        image: Union[bool, str] = None,
    ):
        assistant = await group_assistant(self, chat_id)
        if video:
            stream = AudioVideoPiped(
                link,
                audio_parameters=HighQualityAudio(),
                video_parameters=MediumQualityVideo(),
            )
        else:
            stream = AudioPiped(link, audio_parameters=HighQualityAudio())
        await assistant.change_stream(
            chat_id,
            stream,
        )

    async def seek_stream(self, chat_id, file_path, to_seek, duration, mode):
        assistant = await group_assistant(self, chat_id)
        stream = (
            AudioVideoPiped(
                file_path,
                audio_parameters=HighQualityAudio(),
                video_parameters=MediumQualityVideo(),
                additional_ffmpeg_parameters=f"-ss {to_seek} -to {duration}",
            )
            if mode == "video"
            else AudioPiped(
                file_path,
                audio_parameters=HighQualityAudio(),
                additional_ffmpeg_parameters=f"-ss {to_seek} -to {duration}",
            )
        )
        await assistant.change_stream(chat_id, stream)

    async def stream_call(self, link):
        assistant = await group_assistant(self, config.LOGGER_ID)
        await assistant.join_group_call(
            config.LOGGER_ID,
            AudioVideoPiped(link),
            stream_type=StreamType().pulse_stream,
        )
        await asyncio.sleep(0.2)
        await assistant.leave_group_call(config.LOGGER_ID)

    async def join_call(
        self,
        chat_id: int,
        original_chat_id: int,
        link,
        video: Union[bool, str] = None,
        image: Union[bool, str] = None,
    ):
        assistant = await group_assistant(self, chat_id)
        language = await get_lang(chat_id)
        _ = get_string(language)
        if video:
            stream = AudioVideoPiped(
                link,
                audio_parameters=HighQualityAudio(),
                video_parameters=MediumQualityVideo(),
            )
        else:
            stream = AudioPiped(link, audio_parameters=HighQualityAudio())
        joined = False
        task = self._prejoin_tasks.pop(chat_id, None)
        if task is not None:
            await task
            prejoin_was_video = self._prejoin_video.pop(chat_id, False)
            if bool(video) == prejoin_was_video:
                try:
                    await assistant.change_stream(chat_id, stream)
                    joined = True
                except Exception:
                    try:
                        await assistant.leave_group_call(chat_id)
                    except Exception:
                        pass
            else:
                try:
                    await assistant.leave_group_call(chat_id)
                except Exception:
                    pass
        if not joined:
            await self._assistant_join(assistant, chat_id, stream, _)
        await add_active_chat(chat_id)
        await music_on(chat_id)
        if video:
            await add_active_video_chat(chat_id)
        if await is_autoend():
            counter[chat_id] = {}
            users = len(await assistant.get_participants(chat_id))
            if users == 1:
                autoend[chat_id] = datetime.now() + timedelta(minutes=1)

    async def change_stream(self, client, chat_id):
        check = db.get(chat_id)
        popped = None
        loop = await get_loop(chat_id)
        try:
            if loop == 0:
                popped = check.pop(0)
            else:
                loop = loop - 1
                await set_loop(chat_id, loop)
            await auto_clean(popped)
            if not check:
                if await try_autoplay(chat_id, popped):
                    return
                await _clear_(chat_id)
                return await client.leave_group_call(chat_id)
        except:
            try:
                await _clear_(chat_id)
                return await client.leave_group_call(chat_id)
            except:
                return
        else:
            queued = check[0]["file"]
            language = await get_lang(chat_id)
            _ = get_string(language)
            title = (check[0]["title"]).title()
            user = check[0]["by"]
            original_chat_id = check[0]["chat_id"]
            streamtype = check[0]["streamtype"]
            videoid = check[0]["vidid"]
            if videoid and videoid not in ("telegram", "soundcloud"):
                record_played(chat_id, videoid)
            db[chat_id][0]["played"] = 0
            exis = (check[0]).get("old_dur")
            if exis:
                db[chat_id][0]["dur"] = exis
                db[chat_id][0]["seconds"] = check[0]["old_second"]
                db[chat_id][0]["speed_path"] = None
                db[chat_id][0]["speed"] = 1.0
            video = True if str(streamtype) == "video" else False
            if "live_" in queued:
                n, link = await YouTube.video(videoid, True)
                if n == 0:
                    return await yuki.send_message(
                        original_chat_id,
                        text=_["call_6"],
                    )
                if video:
                    stream = AudioVideoPiped(
                        link,
                        audio_parameters=HighQualityAudio(),
                        video_parameters=MediumQualityVideo(),
                    )
                else:
                    stream = AudioPiped(
                        link,
                        audio_parameters=HighQualityAudio(),
                    )
                try:
                    await client.change_stream(chat_id, stream)
                except Exception:
                    return await yuki.send_message(
                        original_chat_id,
                        text=_["call_6"],
                    )
                img = await get_thumb(videoid)
                run = await send_now_playing_rich(
                    yuki,
                    chat_id,
                    original_chat_id,
                    img,
                    _["stream_1"].format(
                        f"https://t.me/{yuki.username}?start=info_{videoid}",
                        title[:23],
                        check[0]["dur"],
                        user,
                    ),
                )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"
            elif "vid_" in queued:
                mystic = await yuki.send_message(original_chat_id, _["call_7"])
                try:
                    file_path, direct = await YouTube.download(
                        videoid,
                        mystic,
                        videoid=True,
                        video=True if str(streamtype) == "video" else False,
                    )
                except:
                    return await mystic.edit_text(
                        _["call_6"], disable_web_page_preview=True
                    )
                if video:
                    stream = AudioVideoPiped(
                        file_path,
                        audio_parameters=HighQualityAudio(),
                        video_parameters=MediumQualityVideo(),
                    )
                else:
                    stream = AudioPiped(
                        file_path,
                        audio_parameters=HighQualityAudio(),
                    )
                try:
                    await client.change_stream(chat_id, stream)
                except:
                    return await yuki.send_message(
                        original_chat_id,
                        text=_["call_6"],
                    )
                img = await get_thumb(videoid)
                await mystic.delete()
                run = await send_now_playing_rich(
                    yuki,
                    chat_id,
                    original_chat_id,
                    img,
                    _["stream_1"].format(
                        f"https://t.me/{yuki.username}?start=info_{videoid}",
                        title[:23],
                        check[0]["dur"],
                        user,
                    ),
                )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "stream"
            elif "index_" in queued:
                stream = (
                    AudioVideoPiped(
                        videoid,
                        audio_parameters=HighQualityAudio(),
                        video_parameters=MediumQualityVideo(),
                    )
                    if str(streamtype) == "video"
                    else AudioPiped(videoid, audio_parameters=HighQualityAudio())
                )
                try:
                    await client.change_stream(chat_id, stream)
                except:
                    return await yuki.send_message(
                        original_chat_id,
                        text=_["call_6"],
                    )
                run = await send_now_playing_rich(
                    yuki,
                    chat_id,
                    original_chat_id,
                    config.STREAM_IMG_URL,
                    _["stream_2"].format(user),
                )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"
            else:
                if video:
                    stream = AudioVideoPiped(
                        queued,
                        audio_parameters=HighQualityAudio(),
                        video_parameters=MediumQualityVideo(),
                    )
                else:
                    stream = AudioPiped(
                        queued,
                        audio_parameters=HighQualityAudio(),
                    )
                try:
                    await client.change_stream(chat_id, stream)
                except:
                    return await yuki.send_message(
                        original_chat_id,
                        text=_["call_6"],
                    )
                if videoid == "telegram":
                    run = await send_now_playing_rich(
                        yuki,
                        chat_id,
                        original_chat_id,
                        config.TELEGRAM_AUDIO_URL
                        if str(streamtype) == "audio"
                        else config.TELEGRAM_VIDEO_URL,
                        _["stream_1"].format(
                            config.SUPPORT_CHAT, title[:23], check[0]["dur"], user
                        ),
                    )
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "tg"
                elif videoid == "soundcloud":
                    run = await send_now_playing_rich(
                        yuki,
                        chat_id,
                        original_chat_id,
                        config.SOUNCLOUD_IMG_URL,
                        _["stream_1"].format(
                            config.SUPPORT_CHAT, title[:23], check[0]["dur"], user
                        ),
                    )
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "tg"
                else:
                    img = await get_thumb(videoid)
                    run = await send_now_playing_rich(
                        yuki,
                        chat_id,
                        original_chat_id,
                        img,
                        _["stream_1"].format(
                            f"https://t.me/{yuki.username}?start=info_{videoid}",
                            title[:23],
                            check[0]["dur"],
                            user,
                        ),
                    )
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "stream"

    async def ping(self):
        pings = []
        if config.STRING1:
            pings.append(await self.one.ping)
        if config.STRING2:
            pings.append(await self.two.ping)
        if config.STRING3:
            pings.append(await self.three.ping)
        if config.STRING4:
            pings.append(await self.four.ping)
        if config.STRING5:
            pings.append(await self.five.ping)
        return str(round(sum(pings) / len(pings), 3))

    async def start(self):
        LOGGER(__name__).info("Starting PyTgCalls Client...\n")
        if config.STRING1:
            await self.one.start()
        if config.STRING2:
            await self.two.start()
        if config.STRING3:
            await self.three.start()
        if config.STRING4:
            await self.four.start()
        if config.STRING5:
            await self.five.start()

    async def decorators(self):
        @self.one.on_kicked()
        @self.two.on_kicked()
        @self.three.on_kicked()
        @self.four.on_kicked()
        @self.five.on_kicked()
        @self.one.on_closed_voice_chat()
        @self.two.on_closed_voice_chat()
        @self.three.on_closed_voice_chat()
        @self.four.on_closed_voice_chat()
        @self.five.on_closed_voice_chat()
        @self.one.on_left()
        @self.two.on_left()
        @self.three.on_left()
        @self.four.on_left()
        @self.five.on_left()
        async def stream_services_handler(_, chat_id: int):
            await self.stop_stream(chat_id)

        @self.one.on_stream_end()
        @self.two.on_stream_end()
        @self.three.on_stream_end()
        @self.four.on_stream_end()
        @self.five.on_stream_end()
        async def stream_end_handler1(client, update: Update):
            if not isinstance(update, StreamAudioEnded):
                return
            if update.chat_id in self._prejoin_tasks:
                return
            await self.change_stream(client, update.chat_id)


Archon = Call()
