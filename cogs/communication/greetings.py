import discord
from discord.ext import commands
import json
import os
import random
from utils.database import get_user, create_user

class Greetings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.greetings_config = {}
        self.load_config()
    
    def load_config(self):
        """Load greetings configuration from file"""
        config_path = 'config/greetings.json'
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.greetings_config = json.load(f)
            except Exception as e:
                print(f"Error loading greetings config: {e}")
    
    def save_config(self):
        """Save greetings configuration to file"""
        config_path = 'config/greetings.json'
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        try:
            with open(config_path, 'w') as f:
                json.dump(self.greetings_config, f, indent=4)
        except Exception as e:
            print(f"Error saving greetings config: {e}")
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Send welcome message when a member joins"""
        guild_id = str(member.guild.id)
        
        if guild_id not in self.greetings_config:
            return
        
        # Create user in database
        await create_user(
            member.id,
            member.name,
            member.discriminator
        )
        
        # Check if welcome messages are enabled
        if not self.greetings_config[guild_id].get("welcome_enabled", False):
            return
        
        # Get welcome channel
        welcome_channel_id = self.greetings_config[guild_id].get("welcome_channel")
        if not welcome_channel_id:
            return
        
        welcome_channel = member.guild.get_channel(int(welcome_channel_id))
        if not welcome_channel:
            return
        
        # Get welcome messages
        welcome_messages = self.greetings_config[guild_id].get("welcome_messages", [])
        if not welcome_messages:
            welcome_messages = [
                "Welcome {user} to {server}! Enjoy your stay!",
                "Hey {user}, welcome to {server}!",
                "{user} just joined {server}! Everyone say hello!"
            ]
        
        # Select a random message
        message = random.choice(welcome_messages)
        
        # Replace placeholders
        message = message.replace("{user}", member.mention)
        message = message.replace("{server}", member.guild.name)
        message = message.replace("{count}", str(len(member.guild.members)))
        
        # Create embed
        embed = discord.Embed(
            title="👋 Welcome!",
            description=message,
            color=discord.Color.green()
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Add server icon if available
        if member.guild.icon:
            embed.set_footer(text=f"Joined {member.guild.name}", icon_url=member.guild.icon.url)
        
        # Send welcome message
        await welcome_channel.send(embed=embed)
        
        # Send DM if enabled
        if self.greetings_config[guild_id].get("welcome_dm_enabled", False):
            dm_message = self.greetings_config[guild_id].get("welcome_dm_message", "Welcome to {server}! We hope you enjoy your stay.")
            
            # Replace placeholders
            dm_message = dm_message.replace("{user}", member.name)
            dm_message = dm_message.replace("{server}", member.guild.name)
            
            try:
                await member.send(dm_message)
            except:
                # Member might have DMs disabled
                pass
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Send farewell message when a member leaves"""
        guild_id = str(member.guild.id)
        
        if guild_id not in self.greetings_config:
            return
        
        # Check if farewell messages are enabled
        if not self.greetings_config[guild_id].get("farewell_enabled", False):
            return
        
        # Get farewell channel
        farewell_channel_id = self.greetings_config[guild_id].get("farewell_channel")
        if not farewell_channel_id:
            return
        
        farewell_channel = member.guild.get_channel(int(farewell_channel_id))
        if not farewell_channel:
            return
        
        # Get farewell messages
        farewell_messages = self.greetings_config[guild_id].get("farewell_messages", [])
        if not farewell_messages:
            farewell_messages = [
                "Goodbye {user}! We'll miss you!",
                "{user} has left {server}. Farewell!",
                "Sad to see you go, {user}!"
            ]
        
        # Select a random message
        message = random.choice(farewell_messages)
        
        # Replace placeholders
        message = message.replace("{user}", member.name)
        message = message.replace("{server}", member.guild.name)
        message = message.replace("{count}", str(len(member.guild.members)))
        
        # Create embed
        embed = discord.Embed(
            title="👋 Farewell!",
            description=message,
            color=discord.Color.red()
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Add server icon if available
        if member.guild.icon:
            embed.set_footer(text=f"Left {member.guild.name}", icon_url=member.guild.icon.url)
        
        # Send farewell message
        await farewell_channel.send(embed=embed)
    
    @commands.group(invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def greetings(self, ctx):
        """Manage welcome and farewell messages"""
        await ctx.send_help(ctx.command)
    
    @greetings.command()
    @commands.has_permissions(manage_guild=True)
    async def welcome(self, ctx, channel: discord.TextChannel = None):
        """Set up welcome messages"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.greetings_config:
            self.greetings_config[guild_id] = {}
        
        if channel:
            self.greetings_config[guild_id]["welcome_channel"] = str(channel.id)
            self.greetings_config[guild_id]["welcome_enabled"] = True
            
            await ctx.send(f"Welcome messages will now be sent to {channel.mention}.")
        else:
            # Toggle welcome messages
            current = self.greetings_config[guild_id].get("welcome_enabled", False)
            self.greetings_config[guild_id]["welcome_enabled"] = not current
            
            status = "enabled" if not current else "disabled"
            await ctx.send(f"Welcome messages are now {status}.")
        
        self.save_config()
    
    @greetings.command()
    @commands.has_permissions(manage_guild=True)
    async def farewell(self, ctx, channel: discord.TextChannel = None):
        """Set up farewell messages"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.greetings_config:
            self.greetings_config[guild_id] = {}
        
        if channel:
            self.greetings_config[guild_id]["farewell_channel"] = str(channel.id)
            self.greetings_config[guild_id]["farewell_enabled"] = True
            
            await ctx.send(f"Farewell messages will now be sent to {channel.mention}.")
        else:
            # Toggle farewell messages
            current = self.greetings_config[guild_id].get("farewell_enabled", False)
            self.greetings_config[guild_id]["farewell_enabled"] = not current
            
            status = "enabled" if not current else "disabled"
            await ctx.send(f"Farewell messages are now {status}.")
        
        self.save_config()
    
    @greetings.command()
    @commands.has_permissions(manage_guild=True)
    async def addwelcome(self, ctx, *, message: str):
        """Add a custom welcome message"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.greetings_config:
            self.greetings_config[guild_id] = {}
        
        if "welcome_messages" not in self.greetings_config[guild_id]:
            self.greetings_config[guild_id]["welcome_messages"] = []
        
        self.greetings_config[guild_id]["welcome_messages"].append(message)
        self.save_config()
        
        await ctx.send("Welcome message added.")
        await ctx.send("Available placeholders: {user}, {server}, {count}")
    
    @greetings.command()
    @commands.has_permissions(manage_guild=True)
    async def addfarewell(self, ctx, *, message: str):
        """Add a custom farewell message"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.greetings_config:
            self.greetings_config[guild_id] = {}
        
        if "farewell_messages" not in self.greetings_config[guild_id]:
            self.greetings_config[guild_id]["farewell_messages"] = []
        
        self.greetings_config[guild_id]["farewell_messages"].append(message)
        self.save_config()
        
        await ctx.send("Farewell message added.")
        await ctx.send("Available placeholders: {user}, {server}, {count}")
    
    @greetings.command()
    @commands.has_permissions(manage_guild=True)
    async def listwelcome(self, ctx):
        """List all custom welcome messages"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.greetings_config:
            return await ctx.send("No welcome messages configured.")
        
        welcome_messages = self.greetings_config[guild_id].get("welcome_messages", [])
        
        if not welcome_messages:
            return await ctx.send("No custom welcome messages configured.")
        
        embed = discord.Embed(
            title="Welcome Messages",
            color=discord.Color.green()
        )
        
        for i, message in enumerate(welcome_messages):
            embed.add_field(name=f"Message {i+1}", value=message, inline=False)
        
        await ctx.send(embed=embed)
    
    @greetings.command()
    @commands.has_permissions(manage_guild=True)
    async def listfarewell(self, ctx):
        """List all custom farewell messages"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.greetings_config:
            return await ctx.send("No farewell messages configured.")
        
        farewell_messages = self.greetings_config[guild_id].get("farewell_messages", [])
        
        if not farewell_messages:
            return await ctx.send("No custom farewell messages configured.")
        
        embed = discord.Embed(
            title="Farewell Messages",
            color=discord.Color.red()
        )
        
        for i, message in enumerate(farewell_messages):
            embed.add_field(name=f"Message {i+1}", value=message, inline=False)
        
        await ctx.send(embed=embed)
    
    @greetings.command()
    @commands.has_permissions(manage_guild=True)
    async def removewelcome(self, ctx, index: int):
        """Remove a custom welcome message by index"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.greetings_config:
            return await ctx.send("No welcome messages configured.")
        
        welcome_messages = self.greetings_config[guild_id].get("welcome_messages", [])
        
        if not welcome_messages:
            return await ctx.send("No custom welcome messages configured.")
        
        if index < 1 or index > len(welcome_messages):
            return await ctx.send(f"Invalid index. Please specify a number between 1 and {len(welcome_messages)}.")
        
        removed_message = welcome_messages.pop(index - 1)
        self.greetings_config[guild_id]["welcome_messages"] = welcome_messages
        self.save_config()
        
        await ctx.send(f"Removed welcome message: {removed_message}")
    
    @greetings.command()
    @commands.has_permissions(manage_guild=True)
    async def removefarewell(self, ctx, index: int):
        """Remove a custom farewell message by index"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.greetings_config:
            return await ctx.send("No farewell messages configured.")
        
        farewell_messages = self.greetings_config[guild_id].get("farewell_messages", [])
        
        if not farewell_messages:
            return await ctx.send("No custom farewell messages configured.")
        
        if index < 1 or index > len(farewell_messages):
            return await ctx.send(f"Invalid index. Please specify a number between 1 and {len(farewell_messages)}.")
        
        removed_message = farewell_messages.pop(index - 1)
        self.greetings_config[guild_id]["farewell_messages"] = farewell_messages
        self.save_config()
        
        await ctx.send(f"Removed farewell message: {removed_message}")
    
    @greetings.command()
    @commands.has_permissions(manage_guild=True)
    async def welcomedm(self, ctx, enabled: bool = None, *, message: str = None):
        """Configure welcome DMs"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.greetings_config:
            self.greetings_config[guild_id] = {}
        
        if enabled is not None:
            self.greetings_config[guild_id]["welcome_dm_enabled"] = enabled
            
            status = "enabled" if enabled else "disabled"
            await ctx.send(f"Welcome DMs are now {status}.")
        
        if message:
            self.greetings_config[guild_id]["welcome_dm_message"] = message
            await ctx.send("Welcome DM message updated.")
            await ctx.send("Available placeholders: {user}, {server}")
        
        self.save_config()
    
    @greetings.command()
    @commands.has_permissions(manage_guild=True)
    async def status(self, ctx):
        """View current greetings configuration"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.greetings_config:
            return await ctx.send("Greetings are not configured for this server.")
        
        embed = discord.Embed(
            title="Greetings Configuration",
            color=discord.Color.blue()
        )
        
        # Welcome status
        welcome_enabled = self.greetings_config[guild_id].get("welcome_enabled", False)
        welcome_channel_id = self.greetings_config[guild_id].get("welcome_channel")
        welcome_channel = ctx.guild.get_channel(int(welcome_channel_id)) if welcome_channel_id else None
        
        welcome_status = f"Enabled: {welcome_enabled}\n"
        welcome_status += f"Channel: {welcome_channel.mention if welcome_channel else 'Not set'}\n"
        welcome_status += f"Custom Messages: {len(self.greetings_config[guild_id].get('welcome_messages', []))}"
        
        embed.add_field(name="Welcome Messages", value=welcome_status, inline=False)
        
        # Farewell status
        farewell_enabled = self.greetings_config[guild_id].get("farewell_enabled", False)
        farewell_channel_id = self.greetings_config[guild_id].get("farewell_channel")
        farewell_channel = ctx.guild.get_channel(int(farewell_channel_id)) if farewell_channel_id else None
        
        farewell_status = f"Enabled: {farewell_enabled}\n"
        farewell_status += f"Channel: {farewell_channel.mention if farewell_channel else 'Not set'}\n"
        farewell_status += f"Custom Messages: {len(self.greetings_config[guild_id].get('farewell_messages', []))}"
        
        embed.add_field(name="Farewell Messages", value=farewell_status, inline=False)
        
        # Welcome DM status
        welcome_dm_enabled = self.greetings_config[guild_id].get("welcome_dm_enabled", False)
        welcome_dm_message = self.greetings_config[guild_id].get("welcome_dm_message", "Not set")
        
        dm_status = f"Enabled: {welcome_dm_enabled}\n"
        dm_status += f"Message: {welcome_dm_message}"
        
        embed.add_field(name="Welcome DMs", value=dm_status, inline=False)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Greetings(bot))
