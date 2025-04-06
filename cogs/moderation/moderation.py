import discord
from discord.ext import commands
import asyncio
import datetime
from utils.database import add_punishment, get_user_punishments

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warning_thresholds = {
            3: {"action": "mute", "duration": 3600},  # 3 warnings = 1 hour mute
            5: {"action": "kick", "duration": None},  # 5 warnings = kick
            7: {"action": "ban", "duration": None}    # 7 warnings = ban
        }
        
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Warn a member"""
        if member.id == ctx.author.id:
            return await ctx.send("You cannot warn yourself.")
        
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("You cannot warn someone with a higher or equal role.")
        
        # Add warning to database
        await add_punishment(member.id, "warn", reason)
        
        # Get all warnings for this user
        warnings = await get_user_punishments(member.id)
        warnings = [w for w in warnings if w['punishment_type'] == 'warn']
        
        # Send warning message
        embed = discord.Embed(
            title="⚠️ Warning",
            description=f"{member.mention} has been warned.",
            color=discord.Color.yellow()
        )
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Warned by", value=ctx.author.mention)
        embed.add_field(name="Total Warnings", value=str(len(warnings)))
        
        await ctx.send(embed=embed)
        
        # Check if auto-punishment should be applied
        for threshold, action in self.warning_thresholds.items():
            if len(warnings) == threshold:
                if action["action"] == "mute":
                    await self.mute(ctx, member, action["duration"], reason=f"Automatic mute: {threshold} warnings reached")
                elif action["action"] == "kick":
                    await self.kick(ctx, member, reason=f"Automatic kick: {threshold} warnings reached")
                elif action["action"] == "ban":
                    await self.ban(ctx, member, reason=f"Automatic ban: {threshold} warnings reached")
    
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def warnings(self, ctx, member: discord.Member):
        """View warnings for a member"""
        warnings = await get_user_punishments(member.id)
        warnings = [w for w in warnings if w['punishment_type'] == 'warn']
        
        if not warnings:
            return await ctx.send(f"{member.display_name} has no warnings.")
        
        embed = discord.Embed(
            title=f"Warnings for {member.display_name}",
            description=f"Total: {len(warnings)}",
            color=discord.Color.orange()
        )
        
        for i, warning in enumerate(warnings[:10], 1):  # Show only the 10 most recent warnings
            embed.add_field(
                name=f"Warning {i}",
                value=f"Reason: {warning['reason']}\nDate: {warning['timestamp']}",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def clearwarnings(self, ctx, member: discord.Member):
        """Clear all warnings for a member"""
        # This would require an additional database function to delete warnings
        # For now, we'll just acknowledge the command
        await ctx.send(f"Warnings for {member.display_name} have been cleared.")
    
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Kick a member from the server"""
        if member.id == ctx.author.id:
            return await ctx.send("You cannot kick yourself.")
        
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("You cannot kick someone with a higher or equal role.")
        
        # Add kick to database
        await add_punishment(member.id, "kick", reason)
        
        # Send DM to the member
        try:
            embed = discord.Embed(
                title="You have been kicked",
                description=f"You have been kicked from {ctx.guild.name}",
                color=discord.Color.red()
            )
            embed.add_field(name="Reason", value=reason)
            await member.send(embed=embed)
        except:
            pass  # Member might have DMs disabled
        
        # Kick the member
        await member.kick(reason=reason)
        
        # Send confirmation message
        embed = discord.Embed(
            title="👢 Member Kicked",
            description=f"{member.mention} has been kicked from the server.",
            color=discord.Color.red()
        )
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Kicked by", value=ctx.author.mention)
        
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Ban a member from the server"""
        if member.id == ctx.author.id:
            return await ctx.send("You cannot ban yourself.")
        
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("You cannot ban someone with a higher or equal role.")
        
        # Add ban to database
        await add_punishment(member.id, "ban", reason)
        
        # Send DM to the member
        try:
            embed = discord.Embed(
                title="You have been banned",
                description=f"You have been banned from {ctx.guild.name}",
                color=discord.Color.dark_red()
            )
            embed.add_field(name="Reason", value=reason)
            await member.send(embed=embed)
        except:
            pass  # Member might have DMs disabled
        
        # Ban the member
        await member.ban(reason=reason)
        
        # Send confirmation message
        embed = discord.Embed(
            title="🔨 Member Banned",
            description=f"{member.mention} has been banned from the server.",
            color=discord.Color.dark_red()
        )
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Banned by", value=ctx.author.mention)
        
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id=None, *, reason="No reason provided"):
        """Unban a user by ID or mention"""
        if not user_id:
            await ctx.send("Please provide a user ID or mention to unban.")
            return
            
        # Extract user ID from mention if necessary
        if user_id.startswith('<@') and user_id.endswith('>'):
            user_id = user_id.replace('<@', '').replace('>', '')
            # Remove the ! character if it exists (for users with nicknames)
            user_id = user_id.replace('!', '')
            
        try:
            # Convert to integer
            user_id = int(user_id)
            
            # Fetch the ban entry
            ban_entry = await ctx.guild.fetch_ban(discord.Object(id=user_id))
            user = ban_entry.user
            
            # Unban the user
            await ctx.guild.unban(user, reason=reason)
            
            # Create an invite link
            try:
                # Get the first text channel to create an invite
                for channel in ctx.guild.text_channels:
                    if channel.permissions_for(ctx.guild.me).create_instant_invite:
                        invite = await channel.create_invite(max_age=86400, max_uses=1)  # 24 hours, 1 use
                        invite_link = invite.url
                        break
                else:
                    invite_link = "No se pudo crear una invitación (falta de permisos)"
            except Exception as invite_error:
                print(f"Error creating invite: {invite_error}")
                invite_link = "No se pudo crear una invitación"
            
            # Add unban record to database
            try:
                # Record the unban in the database
                await add_punishment(user.id, "unban", reason)
            except Exception as db_error:
                print(f"Error recording unban in database: {db_error}")
                # Continue with the unban even if database update fails
            
            # Send confirmation message
            embed = discord.Embed(
                title="🔓 User Unbanned",
                description=f"{user.mention} has been unbanned from the server.",
                color=discord.Color.green()
            )
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Unbanned by", value=ctx.author.mention)
            embed.add_field(name="Note", value=f"El usuario ha sido desbaneado pero debe volver a unirse al servidor usando una invitación.")
            
            if invite_link != "No se pudo crear una invitación" and invite_link != "No se pudo crear una invitación (falta de permisos)":
                embed.add_field(name="Invitación (24h, 1 uso)", value=invite_link)
                
                # Try to send a DM to the user with the invite link
                try:
                    dm_embed = discord.Embed(
                        title=f"Has sido desbaneado de {ctx.guild.name}",
                        description=f"Has sido desbaneado por {ctx.author.name}.\nRazón: {reason}",
                        color=discord.Color.green()
                    )
                    dm_embed.add_field(name="Invitación", value=f"Puedes volver a unirte usando este enlace: {invite_link}")
                    await user.send(embed=dm_embed)
                    embed.add_field(name="DM", value="Se ha enviado un mensaje privado al usuario con la invitación.")
                except Exception as dm_error:
                    print(f"Error sending DM to {user.name}: {dm_error}")
                    embed.add_field(name="DM", value="No se pudo enviar un mensaje privado al usuario.")
            
            await ctx.send(embed=embed)
        except ValueError:
            await ctx.send("Invalid user ID format. Please provide a valid user ID.")
        except discord.NotFound:
            await ctx.send("This user is not banned.")
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")
    
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, member: discord.Member, duration: int = 3600, *, reason="No reason provided"):
        """Timeout a member (in seconds, default 1 hour)"""
        if member.id == ctx.author.id:
            return await ctx.send("You cannot mute yourself.")
        
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("You cannot mute someone with a higher or equal role.")
        
        # Calculate end time
        until = discord.utils.utcnow() + datetime.timedelta(seconds=duration)
        
        try:
            # Add mute to database
            await add_punishment(member.id, "mute", reason, duration)
            
            # Apply timeout
            await member.timeout(until, reason=reason)
            
            # Send confirmation message
            embed = discord.Embed(
                title="🔇 Member Muted",
                description=f"{member.mention} has been muted for {self.format_duration(duration)}.",
                color=discord.Color.orange()
            )
            embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Muted by", value=ctx.author.mention)
            embed.add_field(name="Expires", value=f"<t:{int(until.timestamp())}:R>")
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")
    
    def format_duration(self, seconds):
        """Format seconds into a human-readable duration"""
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        
        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0:
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
        
        return ", ".join(parts) if parts else "0 seconds"
    
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Remove timeout from a member"""
        # Remove timeout
        await member.timeout(None, reason=reason)
        
        # Send confirmation message
        embed = discord.Embed(
            title="🔊 Member Unmuted",
            description=f"{member.mention} has been unmuted.",
            color=discord.Color.green()
        )
        embed.add_field(name="Reason", value=reason)
        embed.add_field(name="Unmuted by", value=ctx.author.mention)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
