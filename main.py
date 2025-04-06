import os
import discord
from discord.ext import commands, tasks
import asyncio
from dotenv import load_dotenv
from utils.database import supabase, create_tables, get_user, create_user, add_punishment, record_message, update_user_xp, add_achievement

# Load environment variables
load_dotenv()

class ZenShellBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix='!', intents=intents, help_command=None)  # Desactivar el comando de ayuda predeterminado
        self.message_counts = {}  # Diccionario para contar mensajes por usuario
        self.current_status_index = 0
        self.music_playing = False  # Indica si el bot está reproduciendo música
        self.current_song_status = None  # Guarda el estado de la canción actual
        self.status_list = [
            discord.Game(name="!help"),  # Primer estado (por defecto)
            discord.Activity(type=discord.ActivityType.playing, name="con {len(self.guilds)} servidores"),
            discord.Activity(type=discord.ActivityType.watching, name="a {self.get_total_users()} usuarios"),
            discord.Activity(type=discord.ActivityType.competing, name="la mejor experiencia de Discord"),
            discord.Activity(type=discord.ActivityType.watching, name="tus comandos"),
            discord.Activity(type=discord.ActivityType.playing, name="con roles y niveles"),
            discord.Activity(type=discord.ActivityType.competing, name="el top de servidores"),
            discord.Activity(type=discord.ActivityType.listening, name="!help"),  # Movido al final
            discord.Activity(type=discord.ActivityType.listening, name="música para ti"),
            discord.Game(name="Usa !status para cambiarme"),
        ]
        self.supabase = supabase  # Assign supabase client to the bot
        
    def get_total_users(self):
        """Obtiene el número total de usuarios únicos en todos los servidores"""
        unique_users = set()
        for guild in self.guilds:
            for member in guild.members:
                unique_users.add(member.id)
        return len(unique_users)
    
    async def setup_hook(self):
        # Iniciar la tarea de rotación de estado
        self.rotate_status.start()
    
    @tasks.loop(minutes=5.0)
    async def rotate_status(self):
        """Cambia el estado del bot cada 5 minutos"""
        # Si está reproduciendo música, no cambiar el estado
        if hasattr(self, 'music_playing') and self.music_playing:
            return
            
        # Actualizar el estado con información dinámica
        status = self.status_list[self.current_status_index]
        
        # Reemplazar variables en el nombre de la actividad
        if isinstance(status, discord.Activity) and "{" in status.name:
            name = status.name
            if "{len(self.guilds)}" in name:
                name = name.replace("{len(self.guilds)}", str(len(self.guilds)))
            if "{self.get_total_users()}" in name:
                name = name.replace("{self.get_total_users()}", str(self.get_total_users()))
            status = discord.Activity(type=status.type, name=name)
        
        await self.change_presence(activity=status)
        
        # Avanzar al siguiente estado
        self.current_status_index = (self.current_status_index + 1) % len(self.status_list)
    
    @rotate_status.before_loop
    async def before_rotate_status(self):
        """Espera a que el bot esté listo antes de iniciar la rotación de estado"""
        await self.wait_until_ready()

# Crear instancia del bot
bot = ZenShellBot()

# Import cogs (will be implemented later)
async def load_extensions():
    for folder in os.listdir("cogs"):
        if os.path.isdir(os.path.join("cogs", folder)):
            for filename in os.listdir(f"cogs/{folder}"):
                if filename.endswith(".py"):
                    await bot.load_extension(f"cogs.{folder}.{filename[:-3]}")
                    print(f"Loaded extension: cogs.{folder}.{filename[:-3]}")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    print("------")
    
    # Verificar la conexión a la base de datos
    try:
        response = bot.supabase.table('users').select('*').limit(1).execute()
        print("Database connection successful!")
    except Exception as e:
        print(f"Database connection error: {e}")
    
    # Sincronizar usuarios con la base de datos
    await sync_all_users()
    
    # Iniciar tarea de sincronización periódica (cada 6 horas)
    bot.sync_task = asyncio.create_task(periodic_sync(21600))  # 21600 segundos = 6 horas
    
    # Create database tables if they don't exist
    await create_tables()
    
    print("Bot is ready!")

async def sync_all_users():
    """Sincroniza todos los usuarios de todos los servidores con la base de datos"""
    print("Starting user synchronization...")
    total_users = 0
    
    for guild in bot.guilds:
        print(f"Synchronizing users from {guild.name}...")
        
        # Obtener todos los miembros del servidor
        members = guild.members
        
        # Sincronizar cada miembro con la base de datos
        for member in members:
            if not member.bot:  # Ignorar bots
                # Verificar si el usuario ya existe en la base de datos
                user = await get_user(member.id)
                
                if not user:
                    # Crear el usuario si no existe
                    discriminator = member.discriminator if hasattr(member, 'discriminator') else '0000'
                    await create_user(member.id, member.name, discriminator)
                    total_users += 1
    
    # Sincronizar bans
    for guild in bot.guilds:
        try:
            # Usar list() para convertir el generador asíncrono a una lista
            bans = [ban async for ban in guild.bans()]
            for ban_entry in bans:
                # Registrar el ban en la base de datos si el usuario existe
                try:
                    await add_punishment(ban_entry.user.id, "ban", ban_entry.reason or "No reason provided")
                except Exception as e:
                    print(f"Error registering ban for {ban_entry.user.name}: {e}")
        except Exception as e:
            print(f"Error fetching bans from {guild.name}: {e}")
    
    print(f"User synchronization complete! Added {total_users} new users to the database.")

async def periodic_sync(interval):
    """Ejecuta la sincronización de usuarios periódicamente"""
    while True:
        await asyncio.sleep(interval)
        await sync_all_users()

@bot.event
async def on_message(message):
    # Ignore messages from bots
    if message.author.bot:
        return
        
    # Process commands
    await bot.process_commands(message)
    
    try:
        # Record the message in the database
        await record_message(message.author.id, message.content)
        
        # Add XP for the message
        await update_user_xp(message.author.id, 1)  # 1 XP per message
        
        # Check for message count achievements
        user_id = message.author.id
        if user_id in bot.message_counts:
            bot.message_counts[user_id] += 1
        else:
            bot.message_counts[user_id] = 1
        
        # Message count achievements
        if bot.message_counts[user_id] == 10:
            await add_achievement(message.author.id, "Chatty")
            try:
                await message.channel.send(f"🏆 {message.author.mention} ha conseguido el logro **Chatty**!")
            except:
                pass
        elif bot.message_counts[user_id] == 100:
            await add_achievement(message.author.id, "Conversador")
            try:
                await message.channel.send(f"🏆 {message.author.mention} ha conseguido el logro **Conversador**!")
            except:
                pass
        elif bot.message_counts[user_id] == 1000:
            await add_achievement(message.author.id, "Comunicador Experto")
            try:
                await message.channel.send(f"🏆 {message.author.mention} ha conseguido el logro **Comunicador Experto**!")
            except:
                pass
    except Exception as e:
        print(f"Error in on_message event: {e}")

# Run the bot
async def main():
    # Load extensions
    initial_extensions = [
        # Módulos esenciales (siempre activos)
        'cogs.utility.help',         # Sistema de ayuda (fundamental para que los usuarios conozcan los comandos)
        'cogs.music.music',          # Sistema de música
        'cogs.moderation.moderation', # Comandos básicos de moderación (ban, kick, mute, etc.)
        'cogs.moderation.logging',    # Registro de actividad del servidor
        'cogs.moderation.automod',    # Moderación automática
        'cogs.moderation.roles',      # Gestión de roles
        
        # Módulos de utilidad
        'cogs.utility.reminders',     # Sistema de recordatorios
        'cogs.utility.achievements',  # Sistema de logros y perfiles
        'cogs.utility.status',        # Sistema de gestión de estado del bot
        
        # Módulos de economía y niveles
        'cogs.economy.economy',       # Sistema de economía
        'cogs.leveling.leveling',     # Sistema de niveles
        
        # Módulos de comunicación y eventos
        'cogs.communication.greetings', # Saludos automáticos
        'cogs.communication.polls',     # Sistema de encuestas
        'cogs.events.giveaways',        # Sistema de sorteos
        
        # Módulos de tickets y soporte
        'cogs.moderation.tickets',      # Sistema de ticket
    ]
    for extension in initial_extensions:
        await bot.load_extension(extension)
        print(f"Loaded extension: {extension}")
    
    # Start the bot
    await bot.start(os.getenv('DISCORD_TOKEN'))

if __name__ == "__main__":
    asyncio.run(main())
