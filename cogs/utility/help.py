import discord
from discord.ext import commands
import os

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.command_descriptions = {
            # Música
            "play": "Reproduce una canción o añade a la cola. Soporta YouTube, Spotify y búsquedas por texto.",
            "skip": "Salta la canción actual y reproduce la siguiente en la cola.",
            "previous": "Vuelve a la canción anterior en la cola.",
            "queue": "Muestra la cola de reproducción actual.",
            "clear": "Limpia la cola de reproducción.",
            "join": "Hace que el bot se una a tu canal de voz.",
            "leave": "Hace que el bot abandone el canal de voz.",
            "pause": "Pausa la reproducción actual.",
            "resume": "Reanuda la reproducción pausada.",
            "volume": "Ajusta el volumen de reproducción (0-100).",
            "nowplaying": "Muestra información sobre la canción que se está reproduciendo.",
            "loop": "Activa/desactiva el modo de repetición (off/track/queue).",
            "shuffle": "Mezcla aleatoriamente las canciones en la cola.",
            "remove": "Elimina una canción específica de la cola por su número.",
            "seek": "Salta a un punto específico de la canción actual (en segundos).",
            "musichelp": "Muestra ayuda específica para los comandos de música.",
            
            # Moderación
            "warn": "Advierte a un usuario y registra la advertencia en la base de datos.",
            "warnings": "Muestra las advertencias de un usuario.",
            "clearwarnings": "Elimina todas las advertencias de un usuario.",
            "kick": "Expulsa a un usuario del servidor.",
            "ban": "Banea a un usuario del servidor.",
            "unban": "Desbanea a un usuario y opcionalmente le envía una invitación.",
            "mute": "Silencia temporalmente a un usuario.",
            "unmute": "Quita el silencio a un usuario.",
            
            # Economía
            "balance": "Muestra tu saldo de monedas o el de otro usuario.",
            "daily": "Reclama tu recompensa diaria de monedas.",
            "work": "Trabaja para ganar monedas (disponible cada hora).",
            "gamble": "Apuesta monedas con posibilidad de ganar más o perderlas.",
            "give": "Da monedas a otro usuario.",
            "shop": "Muestra los artículos disponibles en la tienda.",
            "buy": "Compra un artículo de la tienda.",
            "addcoins": "Añade monedas a un usuario (solo administradores).",
            "removecoins": "Quita monedas a un usuario (solo administradores).",
            "economy_leaderboard": "Muestra la clasificación de usuarios por monedas.",
            "customcommand": "Crea, edita o elimina un comando personalizado.",
            
            # Utilidades
            "help": "Muestra la lista de comandos o información detallada sobre un comando específico.",
            "reminders": "Establece un recordatorio para más tarde.",
            "dbtest": "Prueba la conexión a la base de datos.",
            "todos": "Gestiona tu lista de tareas pendientes.",
            
            # Comunicación
            "greetings": "Configura mensajes de bienvenida y despedida.",
            "poll": "Crea una encuesta simple con opciones.",
            "strawpoll": "Crea una encuesta avanzada con múltiples opciones.",
            "vote": "Inicia una votación simple de sí/no.",
            
            # Eventos
            "giveaway": "Crea y gestiona sorteos en el servidor.",
            
            # Niveles
            "rank": "Muestra tu nivel y experiencia actual.",
            "leaderboard": "Muestra la clasificación de usuarios por nivel.",
            "givexp": "Da experiencia a un usuario (solo administradores).",
            "levelrole": "Configura roles que se otorgan al alcanzar ciertos niveles.",
            
            # Tickets
            "tickets": "Gestiona el sistema de tickets de soporte.",
            
            # Logging
            "logging": "Configura el registro de eventos del servidor.",
            
            # AutoMod
            "automod": "Configura la moderación automática del servidor."
        }
        
        self.command_usage = {
            # Música
            "play": "!play <url o búsqueda>",
            "skip": "!skip",
            "previous": "!previous",
            "queue": "!queue [página]",
            "clear": "!clear",
            "join": "!join",
            "leave": "!leave",
            "pause": "!pause",
            "resume": "!resume",
            "volume": "!volume <0-100>",
            "nowplaying": "!nowplaying",
            "loop": "!loop <off/track/queue>",
            "shuffle": "!shuffle",
            "remove": "!remove <número>",
            "seek": "!seek <segundos>",
            "musichelp": "!musichelp",
            
            # Moderación
            "warn": "!warn <@usuario> [razón]",
            "warnings": "!warnings <@usuario>",
            "clearwarnings": "!clearwarnings <@usuario>",
            "kick": "!kick <@usuario> [razón]",
            "ban": "!ban <@usuario> [razón]",
            "unban": "!unban <ID o @usuario> [razón]",
            "mute": "!mute <@usuario> [duración en segundos] [razón]",
            "unmute": "!unmute <@usuario> [razón]",
            
            # Economía
            "balance": "!balance [@usuario]",
            "daily": "!daily",
            "work": "!work",
            "gamble": "!gamble <cantidad>",
            "give": "!give <@usuario> <cantidad>",
            "shop": "!shop",
            "buy": "!buy <ID>",
            "addcoins": "!addcoins <@usuario> <cantidad>",
            "removecoins": "!removecoins <@usuario> <cantidad>",
            "economy_leaderboard": "!economy_leaderboard [página]",
            "customcommand": "!customcommand <create/edit/delete> <nombre> [respuesta]",
            
            # Utilidades
            "help": "!help [comando/categoría]",
            "reminders": "!reminders <tiempo> <mensaje>",
            "dbtest": "!dbtest",
            "todos": "!todos [add/remove/list/clear] [tarea]",
            
            # Comunicación
            "greetings": "!greetings <welcome/goodbye> <on/off/set> [mensaje]",
            "poll": "!poll <pregunta> [opciones...]",
            "strawpoll": "!strawpoll <título> <opción1> <opción2> [más opciones...]",
            "vote": "!vote <opción>",
            
            # Eventos
            "giveaway": "!giveaway <tiempo> <premio>",
            
            # Niveles
            "rank": "!rank [@usuario]",
            "leaderboard": "!leaderboard [página]",
            "givexp": "!givexp <@usuario> <cantidad>",
            "levelrole": "!levelrole <add/remove/list> [nivel] [@rol]",
            
            # Tickets
            "tickets": "!tickets <setup/close/add/remove>",
            
            # Logging
            "logging": "!logging <setup/enable/disable> [canal]",
            
            # AutoMod
            "automod": "!automod <enable/disable/setup> [tipo]"
        }
        
        # Descripciones de categorías
        self.category_descriptions = {
            "Music": "Comandos para reproducir música en canales de voz. Soporta YouTube, Spotify y búsquedas por texto.",
            "Moderation": "Herramientas para moderar el servidor: advertencias, expulsiones, baneos y silencios.",
            "Economy": "Sistema económico con monedas, tienda, trabajos y recompensas diarias.",
            "Help": "Comandos de ayuda para entender cómo usar el bot.",
            "Leveling": "Sistema de niveles y experiencia para los usuarios del servidor.",
            "Logging": "Registro de eventos del servidor como entradas, salidas, mensajes eliminados, etc.",
            "AutoMod": "Moderación automática para filtrar contenido inapropiado, spam y más.",
            "Utility": "Utilidades varias como recordatorios y pruebas de base de datos.",
            "Communication": "Comandos para mejorar la comunicación en el servidor.",
            "Events": "Organización de eventos como sorteos.",
            "Tickets": "Sistema de tickets para soporte y ayuda.",
            "TodoList": "Gestión de listas de tareas pendientes.",
            "Voting": "Sistema de votaciones y encuestas.",
            "Giveaways": "Organización de sorteos y regalos.",
            "Greetings": "Mensajes de bienvenida y despedida para nuevos miembros.",
            "Polls": "Creación de encuestas y votaciones.",
            "Reminders": "Sistema de recordatorios programados.",
            "DatabaseTest": "Comandos para probar la conexión a la base de datos."
        }
    
    @commands.command()
    async def help(self, ctx, query=None):
        """Muestra ayuda para los comandos o categorías"""
        if not query:
            # Mostrar ayuda general con categorías
            await self.send_general_help(ctx)
        else:
            # Verificar si es una categoría
            cog_found = False
            for cog_name in self.bot.cogs:
                if query.lower() == cog_name.lower():
                    await self.send_cog_help(ctx, cog_name)
                    cog_found = True
                    break
            
            # Si no es una categoría, buscar como comando
            if not cog_found:
                command = self.bot.get_command(query)
                if command:
                    await self.send_command_help(ctx, command)
                else:
                    # Buscar coincidencias parciales en categorías
                    for cog_name in self.bot.cogs:
                        if query.lower() in cog_name.lower():
                            await self.send_cog_help(ctx, cog_name)
                            return
                    
                    await ctx.send(f"No se encontró ningún comando o categoría llamado `{query}`.")
    
    async def send_general_help(self, ctx):
        """Envía la ayuda general con todas las categorías"""
        embed = discord.Embed(
            title="Ayuda del Bot",
            description="Aquí están todos los comandos disponibles. Usa `!help <comando>` para más detalles sobre un comando específico o `!help <categoría>` para ver todos los comandos de una categoría.",
            color=discord.Color.blue()
        )
        
        # Agrupar comandos por cog
        cog_mapping = {}
        for command in self.bot.commands:
            if command.cog_name not in cog_mapping:
                cog_mapping[command.cog_name] = []
            cog_mapping[command.cog_name].append(command)
        
        # Añadir campos para cada categoría
        for cog_name, commands_list in sorted(cog_mapping.items()):
            if cog_name is None:
                cog_name = "Sin Categoría"
            
            commands_text = ", ".join([f"`!{cmd.name}`" for cmd in sorted(commands_list, key=lambda x: x.name)])
            if commands_text:
                embed.add_field(name=cog_name, value=commands_text, inline=False)
        
        # Añadir pie de página con información adicional
        embed.set_footer(text="Tip: Usa !help <comando> para ver información detallada sobre cómo usar cada comando.")
        
        await ctx.send(embed=embed)
    
    async def send_command_help(self, ctx, command):
        """Envía ayuda detallada para un comando específico"""
        embed = discord.Embed(
            title=f"Ayuda: {command.name}",
            description=self.command_descriptions.get(command.name, command.help or "No hay descripción disponible."),
            color=discord.Color.blue()
        )
        
        # Añadir uso
        usage = self.command_usage.get(command.name, f"!{command.name}")
        if not self.command_usage.get(command.name) and command.signature:
            usage += f" {command.signature}"
        embed.add_field(name="Uso", value=f"`{usage}`", inline=False)
        
        # Añadir aliases si hay
        if command.aliases:
            embed.add_field(name="Aliases", value=", ".join([f"`!{alias}`" for alias in command.aliases]), inline=False)
        
        # Añadir permisos necesarios si los hay
        if command.checks:
            perms = []
            for check in command.checks:
                if hasattr(check, "__qualname__") and "has_permissions" in check.__qualname__:
                    perms.append("Administrador")
                    break
            if perms:
                embed.add_field(name="Permisos requeridos", value=", ".join(perms), inline=False)
        
        # Añadir ejemplos
        examples = {
            "play": "!play https://www.youtube.com/watch?v=dQw4w9WgXcQ\n!play despacito",
            "warn": "!warn @Usuario Spam en el chat",
            "mute": "!mute @Usuario 3600 Comportamiento inapropiado",
            "daily": "!daily",
            "gamble": "!gamble 100",
            "customcommand": "!customcommand create saludo ¡Hola a todos!",
            "reminders": "!reminders 10m Revisar el correo",
            "poll": "!poll ¿Pizza o hamburguesa? Pizza Hamburguesa",
        }
        
        if command.name in examples:
            embed.add_field(name="Ejemplos", value=examples[command.name], inline=False)
        
        await ctx.send(embed=embed)
    
    async def send_cog_help(self, ctx, cog_name):
        """Envía ayuda detallada para una categoría específica"""
        cog = self.bot.get_cog(cog_name)
        if not cog:
            return await ctx.send(f"No se encontró la categoría `{cog_name}`.")
        
        # Obtener todos los comandos de la categoría
        commands_list = [cmd for cmd in cog.get_commands() if not cmd.hidden]
        if not commands_list:
            return await ctx.send(f"La categoría `{cog_name}` no tiene comandos disponibles.")
        
        # Crear embed con descripción de la categoría
        embed = discord.Embed(
            title=f"Categoría: {cog_name}",
            description=self.category_descriptions.get(cog_name, f"Comandos de {cog_name}"),
            color=discord.Color.blue()
        )
        
        # Añadir cada comando con su descripción
        for command in sorted(commands_list, key=lambda x: x.name):
            description = self.command_descriptions.get(command.name, command.help or "No hay descripción disponible.")
            usage = self.command_usage.get(command.name, f"!{command.name}")
            
            value = f"{description}\nUso: `{usage}`"
            embed.add_field(name=f"!{command.name}", value=value, inline=False)
        
        # Añadir pie de página
        embed.set_footer(text=f"Usa !help <comando> para más detalles sobre un comando específico.")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Help(bot))
