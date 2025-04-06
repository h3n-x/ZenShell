import discord
from discord.ext import commands
import asyncio
from utils.database import get_user, get_user_achievements, get_user_balance

class Achievements(commands.Cog):
    """Comandos relacionados con logros y estadísticas de usuario"""
    
    def __init__(self, bot):
        self.bot = bot
        self.achievement_descriptions = {
            # Logros de mensajes
            "Chatty": "Enviar 10 mensajes en el servidor",
            "Conversador": "Enviar 100 mensajes en el servidor",
            "Comunicador Experto": "Enviar 1000 mensajes en el servidor",
            
            # Logros de nivel
            "Principiante": "Alcanzar el nivel 5",
            "Intermedio": "Alcanzar el nivel 10",
            "Experto": "Alcanzar el nivel 20",
            "Maestro": "Alcanzar el nivel 50",
            "Leyenda": "Alcanzar el nivel 100",
            
            # Logros de economía
            "Ahorrador": "Conseguir 1000 monedas",
            "Rico": "Conseguir 10000 monedas",
            "Millonario": "Conseguir 1000000 monedas",
            
            # Logros de comandos
            "Ayudante": "Usar el comando !help 10 veces",
            "Jugador": "Usar el comando !gamble 50 veces",
            "Creativo": "Crear 5 comandos personalizados"
        }
    
    @commands.command(name="perfil", aliases=["profile"])
    async def profile(self, ctx, member: discord.Member = None):
        """Muestra el perfil de un usuario con sus estadísticas y logros
        
        Args:
            member: El miembro del que quieres ver el perfil. Si no se especifica, se muestra tu propio perfil.
        
        Ejemplos:
            !perfil
            !perfil @usuario
        """
        # Si no se especifica un miembro, usar el autor del mensaje
        if member is None:
            member = ctx.author
        
        # Obtener datos del usuario
        user_data = await get_user(member.id)
        
        # Si el usuario no existe en la base de datos
        if not user_data:
            return await ctx.send(f"❌ {member.mention} no tiene un perfil registrado.")
        
        # Obtener logros del usuario
        achievements = await get_user_achievements(member.id)
        
        # Obtener balance económico
        balance = await get_user_balance(member.id)
        
        # Crear embed
        embed = discord.Embed(
            title=f"Perfil de {member.display_name}",
            color=member.color
        )
        
        # Añadir avatar
        embed.set_thumbnail(url=member.avatar_url)
        
        # Añadir estadísticas básicas
        embed.add_field(name="Nivel", value=user_data.get('level', 1), inline=True)
        embed.add_field(name="XP", value=user_data.get('xp', 0), inline=True)
        embed.add_field(name="Monedas", value=balance if balance is not None else 0, inline=True)
        
        # Calcular XP necesario para el siguiente nivel
        current_level = user_data.get('level', 1)
        xp_needed = 100 * (current_level ** 2)
        current_xp = user_data.get('xp', 0)
        
        # Añadir progreso al siguiente nivel
        embed.add_field(
            name="Progreso al siguiente nivel",
            value=f"{current_xp}/{xp_needed} XP ({int((current_xp/xp_needed)*100)}%)",
            inline=False
        )
        
        # Añadir fecha de unión
        embed.add_field(
            name="Fecha de unión",
            value=f"<t:{int(member.joined_at.timestamp())}:R>",
            inline=True
        )
        
        # Añadir fecha de registro
        embed.add_field(
            name="Cuenta creada",
            value=f"<t:{int(member.created_at.timestamp())}:R>",
            inline=True
        )
        
        # Añadir última actividad
        if 'last_active' in user_data and user_data['last_active']:
            # Convertir timestamp a formato Discord
            from datetime import datetime
            try:
                last_active = user_data['last_active']
                if isinstance(last_active, str):
                    # Intentar parsear el formato ISO
                    last_active = datetime.fromisoformat(last_active.replace('Z', '+00:00'))
                
                embed.add_field(
                    name="Última actividad",
                    value=f"<t:{int(last_active.timestamp())}:R>",
                    inline=True
                )
            except:
                embed.add_field(name="Última actividad", value="Desconocida", inline=True)
        
        # Añadir logros
        if achievements:
            achievement_list = []
            for achievement in achievements:
                name = achievement.get('achievement_name', 'Desconocido')
                description = self.achievement_descriptions.get(name, "Logro misterioso")
                achievement_list.append(f"🏆 **{name}**: {description}")
            
            embed.add_field(
                name=f"Logros ({len(achievements)})",
                value="\n".join(achievement_list[:5]) + (f"\n... y {len(achievements) - 5} más" if len(achievements) > 5 else ""),
                inline=False
            )
        else:
            embed.add_field(name="Logros", value="No tiene logros todavía", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="logros", aliases=["achievements"])
    async def achievements(self, ctx, member: discord.Member = None):
        """Muestra todos los logros de un usuario
        
        Args:
            member: El miembro del que quieres ver los logros. Si no se especifica, se muestran tus propios logros.
        
        Ejemplos:
            !logros
            !logros @usuario
        """
        # Si no se especifica un miembro, usar el autor del mensaje
        if member is None:
            member = ctx.author
        
        # Obtener logros del usuario
        achievements = await get_user_achievements(member.id)
        
        # Si no tiene logros
        if not achievements:
            return await ctx.send(f"❌ {member.mention} no tiene logros todavía.")
        
        # Crear embed
        embed = discord.Embed(
            title=f"Logros de {member.display_name}",
            description=f"Total: {len(achievements)} logros",
            color=member.color
        )
        
        # Añadir avatar
        embed.set_thumbnail(url=member.avatar_url)
        
        # Agrupar logros por categoría
        categories = {
            "Mensajes": [],
            "Nivel": [],
            "Economía": [],
            "Comandos": [],
            "Otros": []
        }
        
        for achievement in achievements:
            name = achievement.get('achievement_name', 'Desconocido')
            description = self.achievement_descriptions.get(name, "Logro misterioso")
            date = achievement.get('date_achieved', 'Desconocido')
            
            # Determinar categoría
            if name in ["Chatty", "Conversador", "Comunicador Experto"]:
                category = "Mensajes"
            elif name in ["Principiante", "Intermedio", "Experto", "Maestro", "Leyenda"]:
                category = "Nivel"
            elif name in ["Ahorrador", "Rico", "Millonario"]:
                category = "Economía"
            elif name in ["Ayudante", "Jugador", "Creativo"]:
                category = "Comandos"
            else:
                category = "Otros"
            
            # Formatear fecha
            if isinstance(date, str):
                date_str = f" (Conseguido: {date})"
            else:
                date_str = ""
            
            categories[category].append(f"🏆 **{name}**: {description}{date_str}")
        
        # Añadir campos por categoría
        for category, achievements_list in categories.items():
            if achievements_list:
                embed.add_field(
                    name=category,
                    value="\n".join(achievements_list),
                    inline=False
                )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="top", aliases=["leaderboard"])
    async def leaderboard(self, ctx, tipo="nivel"):
        """Muestra el ranking de usuarios
        
        Args:
            tipo: El tipo de ranking a mostrar. Opciones: nivel, xp, monedas, logros
        
        Ejemplos:
            !top
            !top nivel
            !top monedas
            !top logros
        """
        tipo = tipo.lower()
        
        if tipo not in ["nivel", "xp", "monedas", "logros"]:
            return await ctx.send("❌ Tipo de ranking no válido. Opciones: nivel, xp, monedas, logros")
        
        # Obtener datos según el tipo
        try:
            if tipo == "nivel":
                response = self.bot.supabase.table('users').select('discord_id, username, level').order('level', desc=True).limit(10).execute()
                title = "Top 10 - Nivel"
                field_name = "Nivel"
                field_value = lambda user: user.get('level', 0)
            elif tipo == "xp":
                response = self.bot.supabase.table('users').select('discord_id, username, xp').order('xp', desc=True).limit(10).execute()
                title = "Top 10 - Experiencia"
                field_name = "XP"
                field_value = lambda user: user.get('xp', 0)
            elif tipo == "monedas":
                response = self.bot.supabase.table('economy').select('user_id, balance').order('balance', desc=True).limit(10).execute()
                title = "Top 10 - Monedas"
                field_name = "Monedas"
                field_value = lambda user: user.get('balance', 0)
            elif tipo == "logros":
                # Contar logros por usuario
                response = self.bot.supabase.table('achievements').select('user_id, count').execute()
                
                # Procesar datos para contar por usuario
                user_counts = {}
                for item in response.data:
                    user_id = item.get('user_id')
                    if user_id in user_counts:
                        user_counts[user_id] += 1
                    else:
                        user_counts[user_id] = 1
                
                # Ordenar por cantidad de logros
                sorted_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                
                # Crear datos formateados
                data = []
                for user_id, count in sorted_users:
                    data.append({
                        'user_id': user_id,
                        'count': count
                    })
                
                response.data = data
                title = "Top 10 - Logros"
                field_name = "Logros"
                field_value = lambda user: user.get('count', 0)
            
            # Si no hay datos
            if not response.data:
                return await ctx.send("❌ No hay datos para mostrar.")
            
            # Crear embed
            embed = discord.Embed(
                title=title,
                color=discord.Color.gold()
            )
            
            # Añadir usuarios al ranking
            description = ""
            for i, user_data in enumerate(response.data):
                # Obtener ID de usuario
                user_id = user_data.get('discord_id', user_data.get('user_id'))
                
                # Intentar obtener miembro del servidor
                member = ctx.guild.get_member(int(user_id))
                
                # Nombre a mostrar
                if member:
                    name = member.display_name
                else:
                    # Si no se encuentra, usar nombre de la base de datos o ID
                    name = user_data.get('username', f"Usuario {user_id}")
                
                # Emoji para los primeros lugares
                if i == 0:
                    emoji = "🥇"
                elif i == 1:
                    emoji = "🥈"
                elif i == 2:
                    emoji = "🥉"
                else:
                    emoji = f"{i+1}."
                
                # Añadir línea al ranking
                description += f"{emoji} **{name}**: {field_value(user_data)} {field_name}\n"
            
            embed.description = description
            await ctx.send(embed=embed)
            
        except Exception as e:
            print(f"Error en comando top: {e}")
            await ctx.send(f"❌ Error al obtener el ranking: {e}")

async def setup(bot):
    await bot.add_cog(Achievements(bot))
    return True
