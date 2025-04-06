import discord
from discord.ext import commands
import asyncio
import re
from utils.database import add_role, get_roles

class Roles(commands.Cog):
    """Comandos para gestionar roles en el servidor"""
    
    def __init__(self, bot):
        self.bot = bot
        self.level_roles = {
            5: "Nivel 5",
            10: "Nivel 10",
            20: "Nivel 20",
            50: "Nivel 50",
            100: "Nivel 100"
        }
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Se ejecuta cuando el bot está listo"""
        # Sincronizar roles al inicio
        await self.sync_roles_with_db()
        print("Roles sincronizados con la base de datos")
    
    async def sync_roles_with_db(self):
        """Sincroniza los roles de Discord con la base de datos"""
        print("Sincronizando roles con la base de datos...")
        for guild in self.bot.guilds:
            for role in guild.roles:
                # Ignorar el rol @everyone
                if role.name != "@everyone":
                    # Convertir permisos a lista de strings
                    permissions = []
                    for perm, value in role.permissions:
                        if value:
                            permissions.append(perm)
                    
                    # Añadir rol a la base de datos
                    await add_role(role.name, f"Rol de Discord: {role.name}", permissions)
        
        # Sincronizar roles de nivel
        for level, role_name in self.level_roles.items():
            await add_role(role_name, f"Rol automático para nivel {level}", ["send_messages", "read_messages"])
        
        print("Sincronización de roles completada")
    
    @commands.group(name="role", aliases=["rol"])
    @commands.has_permissions(manage_roles=True)
    async def role(self, ctx):
        """Grupo de comandos para gestionar roles
        
        Este comando por sí solo muestra la ayuda. Usa los subcomandos para gestionar roles.
        
        Ejemplos:
            !role add @usuario @rol
            !role remove @usuario @rol
            !role create nombre color
            !role delete nombre
            !role info nombre
            !role list
        """
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="Gestión de Roles",
                description="Usa los siguientes subcomandos para gestionar roles:",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="!role add @usuario @rol",
                value="Añade un rol a un usuario",
                inline=False
            )
            
            embed.add_field(
                name="!role remove @usuario @rol",
                value="Quita un rol a un usuario",
                inline=False
            )
            
            embed.add_field(
                name="!role create nombre color",
                value="Crea un nuevo rol (color en formato hexadecimal, ej: #FF0000)",
                inline=False
            )
            
            embed.add_field(
                name="!role delete nombre",
                value="Elimina un rol",
                inline=False
            )
            
            embed.add_field(
                name="!role info nombre",
                value="Muestra información de un rol",
                inline=False
            )
            
            embed.add_field(
                name="!role list",
                value="Lista todos los roles del servidor",
                inline=False
            )
            
            await ctx.send(embed=embed)
    
    @role.command(name="add")
    async def role_add(self, ctx, member: discord.Member, role: discord.Role):
        """Añade un rol a un usuario
        
        Args:
            member: El miembro al que añadir el rol
            role: El rol a añadir
        
        Ejemplos:
            !role add @usuario @rol
        """
        # Comprobar que el bot tiene permisos para gestionar este rol
        if ctx.guild.me.top_role <= role:
            return await ctx.send("❌ No puedo asignar un rol que está por encima o igual a mi rol más alto.")
        
        # Comprobar que el autor tiene permisos para gestionar este rol
        if ctx.author.top_role <= role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("❌ No puedes asignar un rol que está por encima o igual a tu rol más alto.")
        
        # Añadir rol
        try:
            await member.add_roles(role, reason=f"Asignado por {ctx.author}")
            await ctx.send(f"✅ Rol {role.mention} añadido a {member.mention}")
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para asignar este rol.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Error al asignar el rol: {e}")
    
    @role.command(name="remove")
    async def role_remove(self, ctx, member: discord.Member, role: discord.Role):
        """Quita un rol a un usuario
        
        Args:
            member: El miembro al que quitar el rol
            role: El rol a quitar
        
        Ejemplos:
            !role remove @usuario @rol
        """
        # Comprobar que el bot tiene permisos para gestionar este rol
        if ctx.guild.me.top_role <= role:
            return await ctx.send("❌ No puedo quitar un rol que está por encima o igual a mi rol más alto.")
        
        # Comprobar que el autor tiene permisos para gestionar este rol
        if ctx.author.top_role <= role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("❌ No puedes quitar un rol que está por encima o igual a tu rol más alto.")
        
        # Quitar rol
        try:
            await member.remove_roles(role, reason=f"Quitado por {ctx.author}")
            await ctx.send(f"✅ Rol {role.mention} quitado a {member.mention}")
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para quitar este rol.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Error al quitar el rol: {e}")
    
    @role.command(name="create")
    async def role_create(self, ctx, name: str, color: str = None):
        """Crea un nuevo rol
        
        Args:
            name: Nombre del rol
            color: Color del rol en formato hexadecimal (ej: #FF0000)
        
        Ejemplos:
            !role create "Nuevo Rol" #FF0000
            !role create "Nuevo Rol"
        """
        # Validar color
        role_color = discord.Color.default()
        if color:
            # Comprobar si es un color hexadecimal válido
            hex_pattern = re.compile(r'^#(?:[0-9a-fA-F]{3}){1,2}$')
            if hex_pattern.match(color):
                # Convertir color hexadecimal a int
                color_int = int(color.lstrip('#'), 16)
                role_color = discord.Color(color_int)
            else:
                return await ctx.send("❌ Color inválido. Usa formato hexadecimal (ej: #FF0000)")
        
        # Crear rol
        try:
            new_role = await ctx.guild.create_role(
                name=name,
                color=role_color,
                reason=f"Creado por {ctx.author}"
            )
            
            # Añadir a la base de datos
            await add_role(name, f"Rol creado por {ctx.author}", [])
            
            await ctx.send(f"✅ Rol {new_role.mention} creado correctamente")
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para crear roles.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Error al crear el rol: {e}")
    
    @role.command(name="delete")
    async def role_delete(self, ctx, *, role: discord.Role):
        """Elimina un rol
        
        Args:
            role: El rol a eliminar
        
        Ejemplos:
            !role delete @rol
            !role delete "Nombre del Rol"
        """
        # Comprobar que el bot tiene permisos para gestionar este rol
        if ctx.guild.me.top_role <= role:
            return await ctx.send("❌ No puedo eliminar un rol que está por encima o igual a mi rol más alto.")
        
        # Comprobar que el autor tiene permisos para gestionar este rol
        if ctx.author.top_role <= role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("❌ No puedes eliminar un rol que está por encima o igual a tu rol más alto.")
        
        # Eliminar rol
        try:
            role_name = role.name
            await role.delete(reason=f"Eliminado por {ctx.author}")
            await ctx.send(f"✅ Rol **{role_name}** eliminado correctamente")
        except discord.Forbidden:
            await ctx.send("❌ No tengo permisos para eliminar este rol.")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Error al eliminar el rol: {e}")
    
    @role.command(name="info")
    async def role_info(self, ctx, *, role: discord.Role):
        """Muestra información de un rol
        
        Args:
            role: El rol del que mostrar información
        
        Ejemplos:
            !role info @rol
            !role info "Nombre del Rol"
        """
        # Crear embed
        embed = discord.Embed(
            title=f"Información del rol: {role.name}",
            color=role.color
        )
        
        # Añadir información básica
        embed.add_field(name="ID", value=role.id, inline=True)
        embed.add_field(name="Color", value=f"#{role.color.value:06x}", inline=True)
        embed.add_field(name="Posición", value=role.position, inline=True)
        embed.add_field(name="Mencionable", value="Sí" if role.mentionable else "No", inline=True)
        embed.add_field(name="Mostrado separadamente", value="Sí" if role.hoist else "No", inline=True)
        embed.add_field(name="Creado", value=f"<t:{int(role.created_at.timestamp())}:R>", inline=True)
        
        # Añadir miembros con este rol
        members_with_role = [member.mention for member in role.members]
        if members_with_role:
            # Limitar a 10 miembros para no sobrecargar el embed
            members_text = ", ".join(members_with_role[:10])
            if len(members_with_role) > 10:
                members_text += f" y {len(members_with_role) - 10} más"
        else:
            members_text = "Ningún miembro tiene este rol"
        
        embed.add_field(name=f"Miembros ({len(role.members)})", value=members_text, inline=False)
        
        # Añadir permisos
        permissions = []
        for perm, value in role.permissions:
            if value:
                # Traducir nombres de permisos comunes
                perm_translations = {
                    "administrator": "Administrador",
                    "manage_guild": "Gestionar Servidor",
                    "manage_roles": "Gestionar Roles",
                    "manage_channels": "Gestionar Canales",
                    "manage_messages": "Gestionar Mensajes",
                    "kick_members": "Expulsar Miembros",
                    "ban_members": "Banear Miembros",
                    "mention_everyone": "Mencionar @everyone",
                    "manage_nicknames": "Gestionar Apodos",
                    "manage_webhooks": "Gestionar Webhooks",
                    "manage_emojis": "Gestionar Emojis"
                }
                
                perm_name = perm_translations.get(perm, perm.replace("_", " ").title())
                permissions.append(f"✅ {perm_name}")
        
        if permissions:
            # Limitar a 15 permisos para no sobrecargar el embed
            perms_text = "\n".join(permissions[:15])
            if len(permissions) > 15:
                perms_text += f"\n... y {len(permissions) - 15} más"
        else:
            perms_text = "Este rol no tiene permisos especiales"
        
        embed.add_field(name="Permisos", value=perms_text, inline=False)
        
        await ctx.send(embed=embed)
    
    @role.command(name="list")
    async def role_list(self, ctx):
        """Lista todos los roles del servidor
        
        Ejemplos:
            !role list
        """
        # Obtener roles ordenados por posición (de mayor a menor)
        roles = sorted(ctx.guild.roles, key=lambda r: r.position, reverse=True)
        
        # Crear embed
        embed = discord.Embed(
            title=f"Roles en {ctx.guild.name}",
            description=f"Total: {len(roles) - 1} roles (excluyendo @everyone)",
            color=discord.Color.blue()
        )
        
        # Agrupar roles por categorías según sus permisos
        admin_roles = []
        mod_roles = []
        special_roles = []
        normal_roles = []
        
        for role in roles:
            if role.name == "@everyone":
                continue
                
            if role.permissions.administrator:
                admin_roles.append(role)
            elif any([role.permissions.ban_members, role.permissions.kick_members, 
                     role.permissions.manage_messages, role.permissions.manage_channels]):
                mod_roles.append(role)
            elif role.hoist or role.mentionable or role.color != discord.Color.default():
                special_roles.append(role)
            else:
                normal_roles.append(role)
        
        # Función para formatear lista de roles
        def format_roles(role_list):
            return "\n".join([f"{role.mention} - {len(role.members)} miembros" for role in role_list]) or "Ninguno"
        
        # Añadir campos para cada categoría
        if admin_roles:
            embed.add_field(name="🛡️ Roles de Administrador", value=format_roles(admin_roles), inline=False)
        
        if mod_roles:
            embed.add_field(name="🔨 Roles de Moderador", value=format_roles(mod_roles), inline=False)
        
        if special_roles:
            embed.add_field(name="✨ Roles Especiales", value=format_roles(special_roles), inline=False)
        
        if normal_roles:
            embed.add_field(name="📝 Otros Roles", value=format_roles(normal_roles), inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="autoroles")
    @commands.has_permissions(manage_roles=True)
    async def autoroles(self, ctx):
        """Muestra los roles automáticos por nivel
        
        Ejemplos:
            !autoroles
        """
        embed = discord.Embed(
            title="Roles Automáticos por Nivel",
            description="Los siguientes roles se asignan automáticamente al alcanzar cierto nivel:",
            color=discord.Color.green()
        )
        
        for level, role_name in sorted(self.level_roles.items()):
            # Buscar si el rol existe en el servidor
            role = discord.utils.get(ctx.guild.roles, name=role_name)
            
            if role:
                embed.add_field(
                    name=f"Nivel {level}",
                    value=f"{role.mention}",
                    inline=True
                )
            else:
                embed.add_field(
                    name=f"Nivel {level}",
                    value=f"{role_name} (No creado)",
                    inline=True
                )
        
        embed.set_footer(text="Estos roles se crean automáticamente si no existen cuando un usuario alcanza el nivel correspondiente")
        
        await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Evento que se dispara cuando un miembro se actualiza"""
        # Comprobar si se ha actualizado el nivel del usuario
        if hasattr(after, 'level') and (not hasattr(before, 'level') or before.level != after.level):
            await self.check_level_roles(after)
    
    async def check_level_roles(self, member):
        """Comprueba y asigna roles basados en el nivel del usuario"""
        # Obtener nivel del usuario
        from utils.database import get_user
        user_data = await get_user(member.id)
        
        if not user_data or 'level' not in user_data:
            return
        
        level = user_data['level']
        
        # Comprobar roles de nivel
        for req_level, role_name in self.level_roles.items():
            if level >= req_level:
                # Buscar rol en el servidor
                role = discord.utils.get(member.guild.roles, name=role_name)
                
                # Si el rol no existe, crearlo
                if not role:
                    try:
                        # Crear rol con color basado en el nivel
                        colors = {
                            5: discord.Color.green(),
                            10: discord.Color.blue(),
                            20: discord.Color.purple(),
                            50: discord.Color.gold(),
                            100: discord.Color.red()
                        }
                        
                        role = await member.guild.create_role(
                            name=role_name,
                            color=colors.get(req_level, discord.Color.default()),
                            reason=f"Rol automático para nivel {req_level}"
                        )
                    except:
                        continue
                
                # Asignar rol si el usuario no lo tiene
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role, reason=f"Alcanzó nivel {req_level}")
                        
                        # Intentar notificar al usuario
                        try:
                            channel = member.guild.system_channel or discord.utils.get(member.guild.text_channels, name="general")
                            if channel:
                                await channel.send(f"🎉 ¡Felicidades {member.mention}! Has alcanzado el nivel {req_level} y has recibido el rol {role.mention}")
                        except:
                            pass
                    except:
                        pass

async def setup(bot):
    await bot.add_cog(Roles(bot))
    return True
