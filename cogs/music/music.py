import discord
from discord.ext import commands
import asyncio
import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
from dotenv import load_dotenv
import re
import urllib.request
import urllib.parse
import random
from aiohttp import ClientSession

# Load environment variables
load_dotenv()

# YouTube and yt-dlp configuration
youtube_base_url = 'https://www.youtube.com/'
youtube_results_url = youtube_base_url + 'results?'
youtube_watch_url = youtube_base_url + 'watch?v='

yt_dl_options = {
    "format": "bestaudio/best",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",
    "extract_flat": True,
    "skip_download": True,
    "no_check_certificate": True,
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -loglevel error',
    'options': '-vn -filter:a "volume=1"'
}

ytdl = yt_dlp.YoutubeDL(yt_dl_options)

# Spotify API setup
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET")
))

class MusicQueue:
    def __init__(self):
        self.queue = []
        self.position = 0
        self.loop_mode = "off"  # off, single, queue
        self.volume = 100
        self.skip_votes = set()
    
    def add(self, track):
        self.queue.append(track)
    
    def next(self):
        if not self.queue:
            return None
        
        if self.loop_mode == "single":
            return self.queue[self.position]
        
        if self.loop_mode == "queue":
            self.position = (self.position + 1) % len(self.queue)
        else:
            self.position += 1
            if self.position >= len(self.queue):
                return None
        
        return self.queue[self.position] if self.position < len(self.queue) else None
    
    def previous(self):
        if not self.queue:
            return None
        
        if self.loop_mode == "single":
            return self.queue[self.position]
        
        self.position -= 1
        if self.position < 0:
            if self.loop_mode == "queue":
                self.position = len(self.queue) - 1
            else:
                self.position = 0
        
        return self.queue[self.position]
    
    def current(self):
        if not self.queue or self.position >= len(self.queue):
            return None
        return self.queue[self.position]
    
    def clear(self):
        self.queue = []
        self.position = 0
        self.skip_votes.clear()
    
    def remove(self, index):
        if 0 <= index < len(self.queue):
            track = self.queue.pop(index)
            if index < self.position:
                self.position -= 1
            return track
        return None
    
    def shuffle(self):
        if not self.queue:
            return
        
        current = self.queue[self.position]
        remaining = self.queue[self.position + 1:]
        import random
        random.shuffle(remaining)
        
        self.queue = self.queue[:self.position + 1] + remaining

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}
        self.voice_clients = {}
        self.current_songs = {}
        self.loading_playlists = set()
    
    async def get_random_image(self):
        """Get a random anime image for embeds"""
        safe_categories = ['smile', 'wave', 'thumbsup', 'dance']
        category = random.choice(safe_categories)
        try:
            async with ClientSession() as session:
                async with session.get(f'https://nekos.best/api/v2/{category}') as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if 'results' in data and len(data['results']) > 0:
                            return data['results'][0].get('url')
        except Exception as e:
            print(f"Error getting image: {e}")
        return None
    
    async def create_embed(self, title, description, color=discord.Color.blue()):
        """Create a fancy embed with optional image"""
        embed = discord.Embed(
            title=title, description=description, color=color)
        try:
            image_url = await self.get_random_image()
            if image_url:
                embed.set_image(url=image_url)
        except Exception as e:
            print(f"Error setting image: {e}")
        return embed
    
    async def send_embed(self, ctx, title, description, color=discord.Color.blue()):
        """Send an embed message"""
        embed = await self.create_embed(title, description, color)
        await ctx.send(embed=embed)
    
    def get_queue(self, guild_id):
        """Get or create a queue for a guild"""
        if guild_id not in self.queues:
            self.queues[guild_id] = MusicQueue()
        return self.queues[guild_id]
    
    async def play_next(self, ctx):
        """Play the next song in the queue"""
        guild_id = ctx.guild.id
        queue = self.get_queue(guild_id)
        
        # Get the next track without advancing the queue yet
        next_track = None
        if queue.position + 1 < len(queue.queue):
            next_track = queue.queue[queue.position + 1]
            queue.position += 1
        elif queue.loop_mode == "queue" and queue.queue:
            queue.position = 0
            next_track = queue.queue[0]
        
        if next_track:
            try:
                await self.play_song(ctx, next_track)
            except Exception as e:
                print(f"Error playing next song: {e}")
                # Try to play the next song if this one fails
                await self.play_next(ctx)
        else:
            await self.send_embed(ctx, "Queue Empty", "Playback finished.")
            if guild_id in self.voice_clients and self.voice_clients[guild_id].is_playing():
                self.voice_clients[guild_id].stop()
    
    async def play_song(self, ctx, song=None):
        """Reproduce una canción o continúa la cola actual"""
        if not song:
            # Si no se especifica una canción, verifica si hay una cola pausada
            if ctx.voice_client and ctx.voice_client.is_paused():
                ctx.voice_client.resume()
                await ctx.send("▶️ Reproducción reanudada.")
                
                # Actualizar estado del bot para mostrar la canción actual
                current = self.get_current_song(ctx.guild.id)
                if current:
                    await self.update_bot_status(f"🎵 {current['title']}")
                return
            else:
                await ctx.send("❌ No hay ninguna canción para reproducir. Usa `!play <canción>` para añadir una canción.")
                return
        
        try:
            guild_id = ctx.guild.id
            
            # Extract audio URL using yt-dlp
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(song['url'], download=False))
            
            if data is None:
                await self.send_embed(ctx, "Error", f"Could not retrieve data for the song: {song['title']}", discord.Color.red())
                return
            
            song_url = data.get('url')
            if song_url is None:
                await self.send_embed(ctx, "Error", f"Could not get playable URL for the song: {song['title']}", discord.Color.red())
                return
            
            # Create FFmpeg audio source
            player = discord.FFmpegOpusAudio(song_url, **ffmpeg_options)
            
            # Play the song
            if guild_id in self.voice_clients:
                self.voice_clients[guild_id].play(
                    player,
                    after=lambda e: asyncio.run_coroutine_threadsafe(
                        self.play_next(ctx),
                        self.bot.loop
                    ).result() if e is None else print(f"Player error: {e}")
                )
                
                # Store current song info
                self.current_songs[guild_id] = song
                
                # Send now playing message
                embed = discord.Embed(
                    title="Now Playing",
                    description=f"[{song['title']}]({song['url']})",
                    color=discord.Color.blue()
                )
                
                if 'thumbnail' in song:
                    embed.set_thumbnail(url=song['thumbnail'])
                
                if 'duration' in song:
                    duration = song['duration']
                    minutes, seconds = divmod(duration, 60)
                    hours, minutes = divmod(minutes, 60)
                    
                    if hours > 0:
                        duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
                    else:
                        duration_str = f"{minutes}:{seconds:02d}"
                    
                    embed.add_field(name="Duration", value=duration_str)
                
                if 'uploader' in song:
                    embed.add_field(name="Channel", value=song['uploader'])
                
                await ctx.send(embed=embed)
                
                # Actualizar estado del bot para mostrar la canción actual
                await self.update_bot_status(f"🎵 {song['title']}")
            else:
                await self.send_embed(ctx, "Error", "Not connected to a voice channel")
        except Exception as e:
            await self.send_embed(ctx, "Error", f"An error occurred: {str(e)}", discord.Color.red())
    
    async def update_bot_status(self, status_text):
        """Actualiza el estado del bot para mostrar la canción actual"""
        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=status_text
            )
        )
        # Guardar el estado actual para restaurarlo después
        self.bot.music_playing = True
        self.bot.current_song_status = status_text
    
    async def get_youtube_results(self, query):
        """Search for videos on YouTube"""
        try:
            search_query = urllib.parse.urlencode({'search_query': query})
            content = urllib.request.urlopen(youtube_results_url + search_query)
            search_results = re.findall(r'/watch\?v=(.{11})', content.read().decode())
            return search_results[:5]  # Return top 5 results
        except Exception as e:
            print(f"Error searching YouTube: {e}")
            return []
    
    async def get_video_info(self, video_id):
        """Get video info from YouTube"""
        url = youtube_watch_url + video_id
        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
            
            return {
                'url': url,
                'title': data['title'],
                'duration': data['duration'],
                'uploader': data['uploader'],
                'thumbnail': data['thumbnail']
            }
        except Exception as e:
            print(f"Error getting video info: {e}")
            return None

    @commands.Cog.listener()
    async def on_ready(self):
        """Event fired when the bot is ready"""
        print("Music module initialized")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Evento que se activa cuando cambia el estado de voz de un miembro"""
        # Si el miembro es el bot
        if member.id == self.bot.user.id:
            # Si el bot salió de un canal de voz
            if before.channel is not None and after.channel is None:
                # Restaurar el estado del bot
                self.bot.music_playing = False
                # Reiniciar la rotación de estado
                if hasattr(self.bot, 'rotate_status'):
                    self.bot.current_status_index = 0
                    await self.bot.rotate_status()

    @commands.command()
    async def musichelp(self, ctx):
        """Show help for music commands"""
        embed = discord.Embed(
            title="Music Commands",
            description="Here are all the available music commands:",
            color=discord.Color.blue()
        )
        
        commands_list = [
            ("join", "Join your voice channel"),
            ("leave", "Leave the voice channel"),
            ("play", "Play a song or add it to the queue"),
            ("pause", "Pause the current track"),
            ("resume", "Resume the current track"),
            ("skip", "Skip the current track"),
            ("previous", "Play the previous track"),
            ("nowplaying", "Show information about the current track"),
            ("queue", "Show the current queue"),
            ("clear", "Clear the music queue"),
            ("remove", "Remove a track from the queue"),
            ("shuffle", "Shuffle the queue"),
            ("loop", "Set loop mode (off, single, queue)"),
            ("volume", "Set the volume (0-100)"),
            ("seek", "Seek to a specific position in the current track (MM:SS)")
        ]
        
        for cmd, desc in commands_list:
            embed.add_field(name=f"!{cmd}", value=desc, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="join")
    async def join_command(self, ctx):
        """Join the user's voice channel"""
        if not ctx.author.voice:
            return await ctx.send("You need to be in a voice channel to use this command.")
        
        channel = ctx.message.author.voice.channel
        await channel.connect()
        self.voice_clients[ctx.guild.id] = ctx.voice_client
        await ctx.send(f"Joined {channel.mention}")
    
    @commands.command(name="leave", aliases=["disconnect", "dc"])
    async def leave_command(self, ctx):
        """Desconecta el bot del canal de voz"""
        if not ctx.voice_client:
            await ctx.send("❌ No estoy conectado a un canal de voz.")
            return
        
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Me he desconectado del canal de voz.")
        
        # Restaurar el estado del bot
        self.bot.music_playing = False
        # Reiniciar la rotación de estado
        if hasattr(self.bot, 'rotate_status'):
            self.bot.current_status_index = 0
            await self.bot.rotate_status()
    
    @commands.command(aliases=["p"])
    async def play(self, ctx, *, query=None):
        """Play a song or add it to the queue"""
        if not query:
            return await ctx.send("Please provide a song to play.")
        
        # Check if user is in a voice channel
        if not ctx.author.voice:
            return await ctx.send("You need to be in a voice channel to use this command.")
        
        # Join the voice channel if not already connected
        if not ctx.voice_client:
            channel = ctx.message.author.voice.channel
            voice_client = await channel.connect()
            self.voice_clients[ctx.guild.id] = voice_client
            await ctx.send(f"Joined {channel.mention}")
        else:
            self.voice_clients[ctx.guild.id] = ctx.voice_client
        
        # Check if query is a Spotify URL
        spotify_pattern = re.compile(r'https?://open\.spotify\.com/(track|playlist|album)/([a-zA-Z0-9]+)')
        spotify_match = spotify_pattern.match(query)
        
        if spotify_match:
            content_type = spotify_match.group(1)
            spotify_id = spotify_match.group(2)
            
            if content_type == "track":
                # Get track info from Spotify
                try:
                    track_info = sp.track(spotify_id)
                    search_query = f"{track_info['name']} {' '.join([artist['name'] for artist in track_info['artists']])}"
                    
                    # Search for the track on YouTube
                    results = await self.get_youtube_results(search_query)
                    if not results:
                        return await ctx.send("Could not find the track on YouTube.")
                    
                    # Get video info
                    video_id = results[0]
                    video_info = await self.get_video_info(video_id)
                    if not video_info:
                        return await ctx.send("Could not get video info.")
                    
                    # Add to queue
                    queue = self.get_queue(ctx.guild.id)
                    queue.add(video_info)
                    
                    # Play if not already playing
                    if not ctx.voice_client.is_playing():
                        await self.play_song(ctx, video_info)
                    else:
                        await ctx.send(f"Added **{video_info['title']}** to the queue")
                    
                except Exception as e:
                    await ctx.send(f"Error processing Spotify track: {str(e)}")
            
            elif content_type == "playlist" or content_type == "album":
                await ctx.send(f"Loading Spotify {content_type}... This may take a moment.")
                
                try:
                    # Get tracks from Spotify playlist or album
                    if content_type == "playlist":
                        results = sp.playlist_items(spotify_id)
                        tracks = [item['track'] for item in results['items'] if item['track']]
                    else:  # album
                        results = sp.album_tracks(spotify_id)
                        tracks = results['items']
                    
                    if not tracks:
                        return await ctx.send(f"No tracks found in the {content_type}.")
                    
                    # Process the first track immediately
                    first_track = tracks[0]
                    search_query = f"{first_track['name']} {' '.join([artist['name'] for artist in first_track['artists']])}"
                    
                    results = await self.get_youtube_results(search_query)
                    if not results:
                        return await ctx.send("Could not find the first track on YouTube.")
                    
                    video_id = results[0]
                    video_info = await self.get_video_info(video_id)
                    if not video_info:
                        return await ctx.send("Could not get video info for the first track.")
                    
                    # Add to queue
                    queue = self.get_queue(ctx.guild.id)
                    queue.add(video_info)
                    
                    # Play if not already playing
                    if not ctx.voice_client.is_playing():
                        await self.play_song(ctx, video_info)
                    else:
                        await ctx.send(f"Added **{video_info['title']}** to the queue")
                    
                    # Process remaining tracks in the background
                    remaining_tracks = tracks[1:25]  # Limit to 25 tracks total
                    if remaining_tracks:
                        await ctx.send(f"Loading the remaining {len(remaining_tracks)} tracks in the background...")
                        asyncio.create_task(self.load_playlist_tracks(ctx, remaining_tracks))
                
                except Exception as e:
                    await ctx.send(f"Error processing Spotify {content_type}: {str(e)}")
            
            return
        
        # Check if query is a YouTube playlist
        youtube_playlist_pattern = re.compile(r'https?://(?:www\.)?youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)')
        youtube_playlist_match = youtube_playlist_pattern.match(query)
        
        if youtube_playlist_match:
            playlist_id = youtube_playlist_match.group(1)
            await ctx.send("Loading YouTube playlist... This may take a moment.")
            
            try:
                # Extract playlist info using yt-dlp
                loop = asyncio.get_event_loop()
                playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(playlist_url, download=False))
                
                if not data or 'entries' not in data:
                    return await ctx.send("Could not retrieve playlist data.")
                
                entries = list(data['entries'])
                if not entries:
                    return await ctx.send("No videos found in the playlist.")
                
                # Process the first track immediately
                first_entry = entries[0]
                if not first_entry:
                    return await ctx.send("Could not retrieve the first video in the playlist.")
                
                video_info = {
                    'url': f"https://www.youtube.com/watch?v={first_entry['id']}",
                    'title': first_entry['title'],
                    'duration': first_entry.get('duration', 0),
                    'uploader': first_entry.get('uploader', 'Unknown'),
                    'thumbnail': first_entry.get('thumbnail', '')
                }
                
                # Add to queue
                queue = self.get_queue(ctx.guild.id)
                queue.add(video_info)
                
                # Play if not already playing
                if not ctx.voice_client.is_playing():
                    await self.play_song(ctx, video_info)
                else:
                    await ctx.send(f"Added **{video_info['title']}** to the queue")
                
                # Process remaining tracks in the background
                remaining_entries = entries[1:25]  # Limit to 25 tracks total
                if remaining_entries:
                    await ctx.send(f"Loading the remaining {len(remaining_entries)} videos in the background...")
                    asyncio.create_task(self.load_youtube_playlist_tracks(ctx, remaining_entries))
            
            except Exception as e:
                await ctx.send(f"Error processing YouTube playlist: {str(e)}")
            
            return
        
        # Regular search or single YouTube URL
        try:
            # Search for the song on YouTube
            results = await self.get_youtube_results(query)
            if not results:
                return await ctx.send("No results found for your query.")
            
            # Get video info for the first result
            video_id = results[0]
            video_info = await self.get_video_info(video_id)
            if not video_info:
                return await ctx.send("Could not get video info.")
            
            # Add the song to the queue
            queue = self.get_queue(ctx.guild.id)
            queue.add(video_info)
            
            # Play the song if not already playing
            if not ctx.voice_client.is_playing():
                await self.play_song(ctx, video_info)
            else:
                await ctx.send(f"Added **{video_info['title']}** to the queue")
        
        except Exception as e:
            await ctx.send(f"Error: {str(e)}")
    
    async def load_playlist_tracks(self, ctx, tracks):
        """Load tracks from a Spotify playlist in the background"""
        guild_id = ctx.guild.id
        queue = self.get_queue(guild_id)
        
        tracks_added = 0
        for track in tracks:
            try:
                search_query = f"{track['name']} {' '.join([artist['name'] for artist in track['artists']])}"
                results = await self.get_youtube_results(search_query)
                
                if results:
                    video_id = results[0]
                    video_info = await self.get_video_info(video_id)
                    
                    if video_info:
                        queue.add(video_info)
                        tracks_added += 1
                
                # Add a small delay to avoid rate limiting
                await asyncio.sleep(0.5)
            
            except Exception as e:
                print(f"Error processing track: {e}")
        
        print(f"Added {tracks_added} tracks from playlist to queue")
    
    async def load_youtube_playlist_tracks(self, ctx, entries):
        """Load tracks from a YouTube playlist in the background"""
        guild_id = ctx.guild.id
        queue = self.get_queue(guild_id)
        
        tracks_added = 0
        for entry in entries:
            try:
                if entry:
                    video_info = {
                        'url': f"https://www.youtube.com/watch?v={entry['id']}",
                        'title': entry['title'],
                        'duration': entry.get('duration', 0),
                        'uploader': entry.get('uploader', 'Unknown'),
                        'thumbnail': entry.get('thumbnail', '')
                    }
                    
                    queue.add(video_info)
                    tracks_added += 1
                
                # Add a small delay to avoid rate limiting
                await asyncio.sleep(0.5)
            
            except Exception as e:
                print(f"Error processing YouTube playlist entry: {e}")
        
        print(f"Added {tracks_added} tracks from YouTube playlist to queue")
    
    @commands.command()
    async def pause(self, ctx):
        """Pause the current track"""
        if ctx.voice_client:
            ctx.voice_client.pause()
            await ctx.send("Paused the current track")
        else:
            await ctx.send("Not connected to a voice channel")
    
    @commands.command()
    async def resume(self, ctx):
        """Resume the current track"""
        if ctx.voice_client:
            ctx.voice_client.resume()
            await ctx.send("Resumed the current track")
        else:
            await ctx.send("Not connected to a voice channel")
    
    @commands.command()
    async def skip(self, ctx):
        """Skip the current track"""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            # El evento after=lambda e: ... en play_song se encargará de reproducir la siguiente canción
            await ctx.send("⏭️ Skipped to next track")
        else:
            await ctx.send("Not playing any music")
    
    @commands.command()
    async def previous(self, ctx):
        """Play the previous track in the queue"""
        guild_id = ctx.guild.id
        queue = self.get_queue(guild_id)
        
        if not queue.queue:
            await self.send_embed(ctx, "Error", "Queue is empty")
            return
            
        if queue.position <= 0:
            if queue.loop_mode == "queue" and len(queue.queue) > 0:
                queue.position = len(queue.queue) - 1
            else:
                queue.position = 0
        else:
            queue.position -= 1
            
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            # La canción anterior se reproducirá automáticamente después de detener la actual
            await ctx.send("⏮️ Playing previous track")
        else:
            # Si no está reproduciendo, iniciamos la reproducción directamente
            await self.play_song(ctx, queue.queue[queue.position])
    
    @commands.command(aliases=["np"])
    async def nowplaying(self, ctx):
        """Show information about the current track"""
        if ctx.guild.id in self.current_songs:
            song = self.current_songs[ctx.guild.id]
            embed = discord.Embed(
                title="Now Playing",
                description=f"[{song['title']}]({song['url']})",
                color=discord.Color.blue()
            )
            
            if 'thumbnail' in song:
                embed.set_thumbnail(url=song['thumbnail'])
            
            if 'duration' in song:
                duration = song['duration']
                minutes, seconds = divmod(duration, 60)
                hours, minutes = divmod(minutes, 60)
                
                if hours > 0:
                    duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
                else:
                    duration_str = f"{minutes}:{seconds:02d}"
                
                embed.add_field(name="Duration", value=duration_str)
            
            if 'uploader' in song:
                embed.add_field(name="Channel", value=song['uploader'])
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("No song is currently playing")
    
    @commands.command(aliases=["q"])
    async def queue(self, ctx, page: int = 1):
        """Show the current queue"""
        queue = self.get_queue(ctx.guild.id)
        if not queue.queue:
            return await ctx.send("The queue is empty")
        
        # Create an embed for the queue
        embed = discord.Embed(
            title="Music Queue",
            description=f"Total tracks: {len(queue.queue)}",
            color=discord.Color.blue()
        )
        
        # Calculate pagination
        items_per_page = 10
        pages = (len(queue.queue) - 1) // items_per_page + 1
        
        if page < 1 or page > pages:
            return await ctx.send(f"Invalid page number. Please specify a page between 1 and {pages}.")
        
        start_idx = (page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, len(queue.queue))
        
        # Add queue items to the embed
        for i in range(start_idx, end_idx):
            song = queue.queue[i]
            status = "🔊 Now Playing" if i == queue.position else f"#{i + 1}"
            
            # Format duration
            if 'duration' in song:
                duration = song['duration']
                minutes, seconds = divmod(duration, 60)
                hours, minutes = divmod(minutes, 60)
                
                if hours > 0:
                    duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
                else:
                    duration_str = f"{minutes}:{seconds:02d}"
            else:
                duration_str = "Unknown"
            
            embed.add_field(
                name=f"{status}",
                value=f"[{song['title']}]({song['url']}) | {duration_str}",
                inline=False
            )
        
        # Add pagination info
        embed.set_footer(text=f"Page {page}/{pages} | Use !queue {page-1} or !queue {page+1} to navigate")
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def clear(self, ctx):
        """Clear the music queue"""
        queue = self.get_queue(ctx.guild.id)
        queue.clear()
        await ctx.send("Cleared the queue")
    
    @commands.command()
    async def remove(self, ctx, index: int = None):
        """Remove a track from the queue"""
        if index is None:
            return await ctx.send("Please provide a track number to remove")
        
        queue = self.get_queue(ctx.guild.id)
        if index < 1 or index > len(queue.queue):
            return await ctx.send("Invalid track number")
        
        queue.remove(index-1)
        await ctx.send(f"Removed track #{index}")
    
    @commands.command()
    async def shuffle(self, ctx):
        """Shuffle the queue"""
        queue = self.get_queue(ctx.guild.id)
        queue.shuffle()
        await ctx.send("Shuffled the queue")
    
    @commands.command()
    async def loop(self, ctx, mode: str = None):
        """Set loop mode (off, single, queue)"""
        if not mode:
            queue = self.get_queue(ctx.guild.id)
            await ctx.send(f"Current loop mode: {queue.loop_mode}")
            return
        
        mode = mode.lower()
        
        if mode not in ["off", "single", "queue"]:
            return await ctx.send("Invalid loop mode. Please specify 'off', 'single', or 'queue'.")
        
        queue = self.get_queue(ctx.guild.id)
        queue.loop_mode = mode
        await ctx.send(f"Set loop mode to '{mode}'")
    
    @commands.command()
    async def volume(self, ctx, volume: int = None):
        """Set the volume (0-100)"""
        if volume is None:
            queue = self.get_queue(ctx.guild.id)
            await ctx.send(f"Current volume: {queue.volume}%")
            return
        
        if volume < 0 or volume > 100:
            return await ctx.send("Volume must be between 0 and 100")
        
        queue = self.get_queue(ctx.guild.id)
        queue.volume = volume
        await ctx.send(f"Set volume to {volume}%")
    
    @commands.command()
    async def seek(self, ctx, position: str = None):
        """Seek to a specific position in the current track (MM:SS)"""
        if not position:
            return await ctx.send("Please provide a position in MM:SS format")
        
        # Parse the position string (MM:SS)
        time_pattern = re.compile(r'^(\d+):(\d{2})$')
        match = time_pattern.match(position)
        
        if not match:
            return await ctx.send("Invalid time format. Please use MM:SS format (e.g., 1:30)")
        
        if ctx.guild.id in self.current_songs:
            song = self.current_songs[ctx.guild.id]
            if 'duration' in song:
                duration = song['duration']
                minutes, seconds = divmod(duration, 60)
                hours, minutes = divmod(minutes, 60)
                
                if hours > 0:
                    duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
                else:
                    duration_str = f"{minutes}:{seconds:02d}"
                
                await ctx.send(f"Seeked to {position} in {duration_str}")
            else:
                await ctx.send("Could not seek to the specified position")
        else:
            await ctx.send("No song is currently playing")
    
    @commands.command(name="stop")
    async def stop_command(self, ctx):
        """Detiene la reproducción y limpia la cola"""
        if not ctx.voice_client:
            await ctx.send("❌ No estoy conectado a un canal de voz.")
            return
        
        # Limpiar la cola y detener la reproducción
        if ctx.guild.id in self.queues:
            self.queues[ctx.guild.id] = []
        
        ctx.voice_client.stop()
        await ctx.send("⏹️ Reproducción detenida y cola limpiada.")
        
        # Restaurar el estado del bot
        self.bot.music_playing = False
        # Reiniciar la rotación de estado
        if hasattr(self.bot, 'rotate_status'):
            self.bot.current_status_index = 0
            await self.bot.rotate_status()

async def setup(bot):
    await bot.add_cog(Music(bot))
