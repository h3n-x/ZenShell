import discord
from discord.ext import commands
import datetime
import json
import os

class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_channels = {}
        self.load_config()
    
    def load_config(self):
        """Load logging configuration from file"""
        config_path = 'config/logging.json'
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.log_channels = json.load(f)
            except Exception as e:
                print(f"Error loading logging config: {e}")
    
    def save_config(self):
        """Save logging configuration to file"""
        config_path = 'config/logging.json'
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        try:
            with open(config_path, 'w') as f:
                json.dump(self.log_channels, f, indent=4)
        except Exception as e:
            print(f"Error saving logging config: {e}")
    
    @commands.group(invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def logging(self, ctx):
        """Manage server logging"""
        await ctx.send_help(ctx.command)
    
    @logging.command()
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx, log_type, channel: discord.TextChannel = None):
        """Set up logging for a specific event type"""
        valid_types = ["moderation", "messages", "members", "server", "voice", "all"]
        
        if log_type not in valid_types:
            return await ctx.send(f"Invalid log type. Valid types: {', '.join(valid_types)}")
        
        channel = channel or ctx.channel
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.log_channels:
            self.log_channels[guild_id] = {}
        
        if log_type == "all":
            for type_name in valid_types:
                if type_name != "all":
                    self.log_channels[guild_id][type_name] = channel.id
        else:
            self.log_channels[guild_id][log_type] = channel.id
        
        self.save_config()
        
        await ctx.send(f"Logging for {log_type} events has been set to {channel.mention}")
    
    @logging.command()
    @commands.has_permissions(administrator=True)
    async def disable(self, ctx, log_type):
        """Disable logging for a specific event type"""
        valid_types = ["moderation", "messages", "members", "server", "voice", "all"]
        
        if log_type not in valid_types:
            return await ctx.send(f"Invalid log type. Valid types: {', '.join(valid_types)}")
        
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.log_channels:
            return await ctx.send("Logging is not set up for this server.")
        
        if log_type == "all":
            self.log_channels.pop(guild_id, None)
        else:
            if log_type in self.log_channels[guild_id]:
                self.log_channels[guild_id].pop(log_type, None)
        
        self.save_config()
        
        await ctx.send(f"Logging for {log_type} events has been disabled")
    
    @logging.command()
    async def status(self, ctx):
        """View the current logging configuration"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.log_channels or not self.log_channels[guild_id]:
            return await ctx.send("Logging is not set up for this server.")
        
        embed = discord.Embed(
            title="Logging Configuration",
            description="Current logging channels for this server",
            color=discord.Color.blue()
        )
        
        for log_type, channel_id in self.log_channels[guild_id].items():
            channel = ctx.guild.get_channel(channel_id)
            channel_mention = channel.mention if channel else "Channel not found"
            embed.add_field(name=log_type.capitalize(), value=channel_mention, inline=True)
        
        await ctx.send(embed=embed)
    
    async def log_event(self, guild, log_type, embed):
        """Log an event to the appropriate channel"""
        guild_id = str(guild.id)
        
        if guild_id not in self.log_channels:
            return
        
        if log_type not in self.log_channels[guild_id]:
            return
        
        channel_id = self.log_channels[guild_id][log_type]
        channel = guild.get_channel(channel_id)
        
        if channel:
            try:
                await channel.send(embed=embed)
            except Exception as e:
                print(f"Error sending log message: {e}")
    
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Log deleted messages"""
        if message.author.bot:
            return
        
        embed = discord.Embed(
            title="Message Deleted",
            description=f"Message by {message.author.mention} deleted in {message.channel.mention}",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        
        if message.content:
            if len(message.content) > 1024:
                embed.add_field(name="Content", value=message.content[:1021] + "...", inline=False)
            else:
                embed.add_field(name="Content", value=message.content, inline=False)
        
        if message.attachments:
            attachment_list = "\n".join([f"[{a.filename}]({a.url})" for a in message.attachments])
            embed.add_field(name="Attachments", value=attachment_list, inline=False)
        
        embed.set_footer(text=f"User ID: {message.author.id} | Message ID: {message.id}")
        
        await self.log_event(message.guild, "messages", embed)
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Log edited messages"""
        if before.author.bot:
            return
        
        if before.content == after.content:
            return
        
        embed = discord.Embed(
            title="Message Edited",
            description=f"Message by {before.author.mention} edited in {before.channel.mention}",
            color=discord.Color.gold(),
            timestamp=datetime.datetime.now()
        )
        
        if before.content:
            if len(before.content) > 1024:
                embed.add_field(name="Before", value=before.content[:1021] + "...", inline=False)
            else:
                embed.add_field(name="Before", value=before.content, inline=False)
        
        if after.content:
            if len(after.content) > 1024:
                embed.add_field(name="After", value=after.content[:1021] + "...", inline=False)
            else:
                embed.add_field(name="After", value=after.content, inline=False)
        
        embed.add_field(name="Jump to Message", value=f"[Click Here]({after.jump_url})", inline=False)
        embed.set_footer(text=f"User ID: {before.author.id} | Message ID: {before.id}")
        
        await self.log_event(before.guild, "messages", embed)
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Log member joins"""
        embed = discord.Embed(
            title="Member Joined",
            description=f"{member.mention} joined the server",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now()
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        embed.set_footer(text=f"User ID: {member.id}")
        
        await self.log_event(member.guild, "members", embed)
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Log member leaves"""
        embed = discord.Embed(
            title="Member Left",
            description=f"{member.mention} left the server",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Joined Server", value=f"<t:{int(member.joined_at.timestamp()) if member.joined_at else 0}:R>", inline=True)
        embed.add_field(name="Roles", value=", ".join([role.mention for role in member.roles[1:]]) or "None", inline=False)
        embed.set_footer(text=f"User ID: {member.id}")
        
        await self.log_event(member.guild, "members", embed)
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Log member updates (roles, nickname)"""
        if before.roles != after.roles:
            # Roles updated
            added_roles = [role for role in after.roles if role not in before.roles]
            removed_roles = [role for role in before.roles if role not in after.roles]
            
            if added_roles or removed_roles:
                embed = discord.Embed(
                    title="Member Roles Updated",
                    description=f"{after.mention}'s roles were updated",
                    color=discord.Color.blue(),
                    timestamp=datetime.datetime.now()
                )
                
                if added_roles:
                    embed.add_field(name="Added Roles", value=", ".join([role.mention for role in added_roles]), inline=False)
                
                if removed_roles:
                    embed.add_field(name="Removed Roles", value=", ".join([role.mention for role in removed_roles]), inline=False)
                
                embed.set_thumbnail(url=after.display_avatar.url)
                embed.set_footer(text=f"User ID: {after.id}")
                
                await self.log_event(after.guild, "members", embed)
        
        if before.nick != after.nick:
            # Nickname updated
            embed = discord.Embed(
                title="Nickname Changed",
                description=f"{after.mention}'s nickname was changed",
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )
            
            embed.add_field(name="Before", value=before.nick or "None", inline=True)
            embed.add_field(name="After", value=after.nick or "None", inline=True)
            embed.set_thumbnail(url=after.display_avatar.url)
            embed.set_footer(text=f"User ID: {after.id}")
            
            await self.log_event(after.guild, "members", embed)

async def setup(bot):
    await bot.add_cog(Logging(bot))
