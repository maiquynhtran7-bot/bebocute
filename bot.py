import asyncio
import os
import re
import traceback
from collections import deque

import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp

# ================== LẤY TOKEN TỪ RAILWAY ==================
BOT_TOKEN = os.getenv("DISCORD_TOKEN")   # Railway sẽ tự động lấy biến này

if not BOT_TOKEN:
    print("[ERROR] Không tìm thấy DISCORD_TOKEN trong Variables!")
    exit(1)

COMMAND_PREFIX = "!"
EMBED_COLOR = 0x1DB954

BOT_NAME = "bobepong"
BOT_DESCRIPTION = "Nghe nhạc cùng bạn bè • https://discord.gg/bobepong"

# ================== PHẦN CODE CÒN LẠI ==================
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    },
    "retries": 5,
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
    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    def get_player(self, guild_id):
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(guild_id)
        return self.players[guild_id]

    def _after(self, guild, error=None):
        if error:
            print(f"[ERROR] {error}")
        player = self.get_player(guild.id)
        source = player.next()
        if source and guild.voice_client and guild.voice_client.is_connected():
            guild.voice_client.play(source, after=lambda e: self._after(guild, e))
            if guild.voice_client.source:
                guild.voice_client.source.volume = player.volume

    @app_commands.command(name="play", description="Phát nhạc từ link hoặc tên bài")
    @app_commands.describe(query="Link YouTube hoặc tên bài hát")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.send_message("Lệnh play đang được xây dựng...", ephemeral=True)


intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)


@bot.event
async def on_ready():
    print(f"[OK] Bot online: {bot.user}")
    try:
        await bot.add_cog(MusicCog(bot))
        await bot.tree.sync()
        print("[OK] Commands synced.")
    except Exception as e:
        print(f"[ERROR] {e}")

    activity = discord.Activity(type=discord.ActivityType.listening, name=f"/play • {BOT_NAME}")
    await bot.change_presence(activity=activity)
    print(f"[OK] Tiểu sử bot đã đặt: {BOT_DESCRIPTION}")


if __name__ == "__main__":
    bot.run(BOT_TOKEN)
