import asyncio
import os
import re
import traceback
from collections import deque

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
import yt_dlp

load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = "!"
EMBED_COLOR = 0x1DB954

# ================== CÀI ĐẶT TIỂU SỬ BOT ==================
BOT_NAME = "bobepong"
BOT_DESCRIPTION = "Nghe nhạc cùng bạn bè • https://discord.gg/bobepong"  # Thay link nếu cần

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": False,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    "http_headers": {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.youtube.com/",
    },
    "extractor_args": {
        "youtube": {
            "skip": ["dash", "hls"],
            "player_client": ["android", "web"],
        }
    },
    "retries": 5,
    "fragment_retries": 5,
    "skip_unavailable_fragments": True,
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -hide_banner -loglevel error",
    "options": "-vn -bufsize 512k",
}


class YTDLSource(discord.PCMVolumeTransformer):
    ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get("title", "Unknown")
        self.url = data.get("webpage_url", "")
        self.duration = data.get("duration", 0)
        self.thumbnail = data.get("thumbnail", "")
        self.uploader = data.get("uploader", "Unknown")

    @classmethod
    async def from_url(cls, url, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: cls.ytdl.extract_info(url, download=False))
        if data is None:
            raise ValueError("Không thể lấy thông tin bài hát.")
        if "entries" in data:
            entries = [e for e in data["entries"] if e]
            if not entries:
                raise ValueError("Playlist trống.")
            return [cls._make(e) for e in entries]
        return [cls._make(data)]

    @classmethod
    def _make(cls, data):
        return cls(discord.FFmpegPCMAudio(data["url"], **FFMPEG_OPTIONS), data=data)

    @staticmethod
    def fmt_dur(sec):
        if not sec:
            return "Live"
        m, s = divmod(int(sec), 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# ... (phần MusicPlayer và MusicCog giữ nguyên như cũ) ...

class MusicPlayer:
    def __init__(self, guild_id):
        self.guild_id = guild_id
        self.queue = deque()
        self.current = None
        self.loop = False
        self.loop_queue = False
        self.volume = 0.5

    def add(self, sources):
        self.queue.extend(sources)

    def next(self):
        if self.loop and self.current:
            return self.current
        if self.loop_queue and self.current:
            self.queue.append(self.current)
        if self.queue:
            self.current = self.queue.popleft()
            return self.current
        self.current = None
        return None

    def clear(self):
        self.queue.clear()
        self.current = None


class MusicCog(commands.Cog):
    # ... (giữ nguyên toàn bộ class MusicCog như file cũ của bạn) ...
    # (Tôi không copy hết để ngắn gọn, bạn chỉ cần thay phần on_ready bên dưới)

# ====================== PHẦN CHÍNH ======================
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)


@bot.event
async def on_ready():
    print(f"[OK] Bot online: {bot.user}")
    try:
        await bot.add_cog(MusicCog(bot))
        synced = await bot.tree.sync()
        print(f"[OK] Synced {len(synced)} commands.")
    except Exception as e:
        print(f"[ERROR] Sync failed: {e}")
        traceback.print_exc()

    # ================== SET TIỂU SỬ BOT ==================
    activity = discord.Activity(
        type=discord.ActivityType.listening,
        name=f"/play | {BOT_NAME}"
    )
    await bot.change_presence(activity=activity, status=discord.Status.online)
    
    print(f"[OK] Tiểu sử bot đã đặt thành: {BOT_DESCRIPTION}")


# Giữ nguyên phần on_voice_state_update và if __name__ == "__main__"
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("[ERROR] Điền DISCORD_TOKEN vào file .env trước!")
        exit(1)
    bot.run(BOT_TOKEN)
