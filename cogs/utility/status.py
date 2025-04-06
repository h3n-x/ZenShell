import discord
from discord.ext import commands
from discord import app_commands
import asyncio

class Status(commands.Cog):
    """Comandos para gestionar el estado del bot"""
    
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command(name="status")
    @commands.has_permissions(administrator=True)
    async def set_status(self, ctx, status_type=None, *, status_text=None):
        """
        Cambia el estado del bot
        
        Tipos disponibles: playing, listening, watching, streaming, competing
        
        Ejemplos:
        !status playing Minecraft
        !status listening música
        !status watching tus mensajes
        !status competing torneos
        !status reset (vuelve a la rotación automática)
        """
        if not status_type:
            # Mostrar ayuda si no se proporciona un tipo
            embed = discord.Embed(
                title="Cambiar Estado del Bot",
                description="Usa este comando para cambiar el estado del bot",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Uso",
                value="!status [tipo] [texto]",
                inline=False
            )
            embed.add_field(
                name="Tipos disponibles",
                value="• playing\n• listening\n• watching\n• streaming\n• competing\n• reset",
                inline=False
            )
            embed.add_field(
                name="Ejemplos",
                value="!status playing Minecraft\n!status listening música\n!status reset",
                inline=False
            )
            await ctx.send(embed=embed)
            return
            
        # Restaurar la rotación automática
        if status_type.lower() == "reset":
            self.bot.music_playing = False
            self.bot.current_status_index = 0
            await self.bot.rotate_status()
            await ctx.send("✅ Estado del bot restaurado a la rotación automática.")
            return
            
        if not status_text:
            await ctx.send("❌ Debes proporcionar un texto para el estado.")
            return
            
        # Mapear los tipos de estado a los tipos de actividad de Discord
        activity_types = {
            "playing": discord.ActivityType.playing,
            "listening": discord.ActivityType.listening,
            "watching": discord.ActivityType.watching,
            "streaming": discord.ActivityType.streaming,
            "competing": discord.ActivityType.competing
        }
        
        # Verificar si el tipo de estado es válido
        if status_type.lower() not in activity_types:
            await ctx.send(f"❌ Tipo de estado no válido. Usa uno de: {', '.join(activity_types.keys())}")
            return
            
        # Crear la actividad
        activity_type = activity_types[status_type.lower()]
        activity = discord.Activity(type=activity_type, name=status_text)
        
        # Cambiar el estado
        await self.bot.change_presence(activity=activity)
        
        # Desactivar la rotación automática
        self.bot.music_playing = True  # Usamos el mismo flag que para la música
        
        await ctx.send(f"✅ Estado del bot cambiado a: **{status_type}** {status_text}")
        
    @commands.command(name="statuslist")
    @commands.has_permissions(administrator=True)
    async def status_list(self, ctx):
        """Muestra la lista de estados automáticos configurados"""
        embed = discord.Embed(
            title="Estados Automáticos del Bot",
            description="Lista de estados que el bot rotará automáticamente cada 5 minutos",
            color=discord.Color.blue()
        )
        
        for i, status in enumerate(self.bot.status_list):
            status_type = status.type.name if hasattr(status, 'type') else "playing"
            status_name = status.name if hasattr(status, 'name') else str(status)
            embed.add_field(
                name=f"Estado #{i+1}",
                value=f"**Tipo:** {status_type}\n**Texto:** {status_name}",
                inline=False
            )
            
        await ctx.send(embed=embed)
        
    @commands.command(name="addstatus")
    @commands.has_permissions(administrator=True)
    async def add_status(self, ctx, status_type, *, status_text):
        """
        Añade un nuevo estado a la rotación automática
        
        Tipos disponibles: playing, listening, watching, streaming, competing
        
        Ejemplos:
        !addstatus playing Minecraft
        !addstatus listening música
        """
        # Mapear los tipos de estado a los tipos de actividad de Discord
        activity_types = {
            "playing": discord.ActivityType.playing,
            "listening": discord.ActivityType.listening,
            "watching": discord.ActivityType.watching,
            "streaming": discord.ActivityType.streaming,
            "competing": discord.ActivityType.competing
        }
        
        # Verificar si el tipo de estado es válido
        if status_type.lower() not in activity_types:
            await ctx.send(f"❌ Tipo de estado no válido. Usa uno de: {', '.join(activity_types.keys())}")
            return
            
        # Crear la actividad
        activity_type = activity_types[status_type.lower()]
        
        if status_type.lower() == "playing":
            new_status = discord.Game(name=status_text)
        else:
            new_status = discord.Activity(type=activity_type, name=status_text)
        
        # Añadir a la lista de estados
        self.bot.status_list.append(new_status)
        
        await ctx.send(f"✅ Nuevo estado añadido a la rotación: **{status_type}** {status_text}")
        
    @commands.command(name="removestatus")
    @commands.has_permissions(administrator=True)
    async def remove_status(self, ctx, index: int):
        """
        Elimina un estado de la rotación automática
        
        Ejemplo:
        !removestatus 3
        """
        if index < 1 or index > len(self.bot.status_list):
            await ctx.send(f"❌ Índice no válido. Debe estar entre 1 y {len(self.bot.status_list)}")
            return
            
        # Obtener el estado que se va a eliminar
        status = self.bot.status_list[index-1]
        status_type = status.type.name if hasattr(status, 'type') else "playing"
        status_name = status.name if hasattr(status, 'name') else str(status)
        
        # Eliminar el estado
        self.bot.status_list.pop(index-1)
        
        # Ajustar el índice actual si es necesario
        if self.bot.current_status_index >= len(self.bot.status_list):
            self.bot.current_status_index = 0
            
        await ctx.send(f"✅ Estado eliminado de la rotación: **{status_type}** {status_name}")

async def setup(bot):
    await bot.add_cog(Status(bot))
