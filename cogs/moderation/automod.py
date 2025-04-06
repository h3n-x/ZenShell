import discord
from discord.ext import commands
import re
import json
import os
from utils.database import add_punishment

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = {}
        self.load_config()
    
    def load_config(self):
        """Load automod configuration from file"""
        config_path = 'config/automod.json'
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"Error loading automod config: {e}")
        else:
            # Create default config
            self.config = {}
            self.save_config()
    
    def save_config(self):
        """Save automod configuration to file"""
        config_path = 'config/automod.json'
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        try:
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving automod config: {e}")
    
    @commands.group(invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def automod(self, ctx):
        """Manage the auto-moderation system"""
        await ctx.send_help(ctx.command)
    
    @automod.command()
    @commands.has_permissions(administrator=True)
    async def status(self, ctx):
        """View the current automod configuration"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.config:
            return await ctx.send("AutoMod is not configured for this server.")
        
        embed = discord.Embed(
            title="AutoMod Configuration",
            description="Current auto-moderation settings",
            color=discord.Color.blue()
        )
        
        # Add filter status
        filters = self.config[guild_id].get("filters", {})
        filter_status = []
        
        if filters.get("banned_words", {}).get("enabled", False):
            word_count = len(filters.get("banned_words", {}).get("words", []))
            filter_status.append(f"✅ Banned Words: {word_count} words")
        else:
            filter_status.append("❌ Banned Words: Disabled")
        
        if filters.get("caps", {}).get("enabled", False):
            threshold = filters.get("caps", {}).get("threshold", 70)
            filter_status.append(f"✅ Excessive Caps: {threshold}% threshold")
        else:
            filter_status.append("❌ Excessive Caps: Disabled")
        
        if filters.get("spam", {}).get("enabled", False):
            limit = filters.get("spam", {}).get("message_limit", 5)
            seconds = filters.get("spam", {}).get("time_window", 5)
            filter_status.append(f"✅ Anti-Spam: {limit} messages in {seconds}s")
        else:
            filter_status.append("❌ Anti-Spam: Disabled")
        
        if filters.get("links", {}).get("enabled", False):
            filter_status.append("✅ Link Filter: Enabled")
        else:
            filter_status.append("❌ Link Filter: Disabled")
        
        if filters.get("invites", {}).get("enabled", False):
            filter_status.append("✅ Discord Invites: Blocked")
        else:
            filter_status.append("❌ Discord Invites: Allowed")
        
        embed.add_field(name="Filters", value="\n".join(filter_status), inline=False)
        
        # Add punishment settings
        punishments = self.config[guild_id].get("punishments", {})
        punishment_status = []
        
        for violation, action in punishments.items():
            punishment_status.append(f"{violation}: {action}")
        
        if punishment_status:
            embed.add_field(name="Punishments", value="\n".join(punishment_status), inline=False)
        else:
            embed.add_field(name="Punishments", value="No punishments configured", inline=False)
        
        # Add exempt roles/channels
        exempt_roles = self.config[guild_id].get("exempt_roles", [])
        exempt_channels = self.config[guild_id].get("exempt_channels", [])
        
        role_mentions = []
        for role_id in exempt_roles:
            role = ctx.guild.get_role(int(role_id))
            if role:
                role_mentions.append(role.mention)
        
        channel_mentions = []
        for channel_id in exempt_channels:
            channel = ctx.guild.get_channel(int(channel_id))
            if channel:
                channel_mentions.append(channel.mention)
        
        if role_mentions:
            embed.add_field(name="Exempt Roles", value=", ".join(role_mentions), inline=False)
        
        if channel_mentions:
            embed.add_field(name="Exempt Channels", value=", ".join(channel_mentions), inline=False)
        
        await ctx.send(embed=embed)
    
    @automod.group(invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def filter(self, ctx):
        """Manage automod filters"""
        await ctx.send_help(ctx.command)
    
    @filter.command()
    @commands.has_permissions(administrator=True)
    async def words(self, ctx, action="list"):
        """Manage banned words filter"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.config:
            self.config[guild_id] = {}
        
        if "filters" not in self.config[guild_id]:
            self.config[guild_id]["filters"] = {}
        
        if "banned_words" not in self.config[guild_id]["filters"]:
            self.config[guild_id]["filters"]["banned_words"] = {
                "enabled": False,
                "words": []
            }
        
        if action.lower() == "list":
            words = self.config[guild_id]["filters"]["banned_words"].get("words", [])
            enabled = self.config[guild_id]["filters"]["banned_words"].get("enabled", False)
            
            if not words:
                return await ctx.send("No banned words configured.")
            
            status = "Enabled" if enabled else "Disabled"
            
            # Send the list in DM to avoid showing banned words in public channel
            try:
                embed = discord.Embed(
                    title="Banned Words",
                    description=f"Status: {status}\n\n" + "\n".join(words),
                    color=discord.Color.blue()
                )
                await ctx.author.send(embed=embed)
                await ctx.send("Banned words list has been sent to your DMs.")
            except discord.Forbidden:
                await ctx.send("I couldn't send you a DM. Please enable DMs from server members.")
        
        elif action.lower() == "enable":
            self.config[guild_id]["filters"]["banned_words"]["enabled"] = True
            self.save_config()
            await ctx.send("Banned words filter has been enabled.")
        
        elif action.lower() == "disable":
            self.config[guild_id]["filters"]["banned_words"]["enabled"] = False
            self.save_config()
            await ctx.send("Banned words filter has been disabled.")
    
    @filter.command()
    @commands.has_permissions(administrator=True)
    async def addword(self, ctx, *, word):
        """Add a word to the banned words list"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.config:
            self.config[guild_id] = {}
        
        if "filters" not in self.config[guild_id]:
            self.config[guild_id]["filters"] = {}
        
        if "banned_words" not in self.config[guild_id]["filters"]:
            self.config[guild_id]["filters"]["banned_words"] = {
                "enabled": False,
                "words": []
            }
        
        # Add the word if it's not already in the list
        if word.lower() not in [w.lower() for w in self.config[guild_id]["filters"]["banned_words"]["words"]]:
            self.config[guild_id]["filters"]["banned_words"]["words"].append(word.lower())
            self.save_config()
            await ctx.send(f"Added `{word}` to the banned words list.")
        else:
            await ctx.send(f"`{word}` is already in the banned words list.")
    
    @filter.command()
    @commands.has_permissions(administrator=True)
    async def removeword(self, ctx, *, word):
        """Remove a word from the banned words list"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.config:
            return await ctx.send("AutoMod is not configured for this server.")
        
        if "filters" not in self.config[guild_id]:
            return await ctx.send("No filters configured.")
        
        if "banned_words" not in self.config[guild_id]["filters"]:
            return await ctx.send("Banned words filter is not configured.")
        
        # Find the word (case-insensitive) and remove it
        words = self.config[guild_id]["filters"]["banned_words"]["words"]
        for i, banned_word in enumerate(words):
            if banned_word.lower() == word.lower():
                words.pop(i)
                self.save_config()
                return await ctx.send(f"Removed `{banned_word}` from the banned words list.")
        
        await ctx.send(f"`{word}` is not in the banned words list.")
    
    @filter.command()
    @commands.has_permissions(administrator=True)
    async def caps(self, ctx, action="status", threshold: int = 70):
        """Configure the excessive caps filter"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.config:
            self.config[guild_id] = {}
        
        if "filters" not in self.config[guild_id]:
            self.config[guild_id]["filters"] = {}
        
        if "caps" not in self.config[guild_id]["filters"]:
            self.config[guild_id]["filters"]["caps"] = {
                "enabled": False,
                "threshold": 70
            }
        
        if action.lower() == "status":
            enabled = self.config[guild_id]["filters"]["caps"].get("enabled", False)
            current_threshold = self.config[guild_id]["filters"]["caps"].get("threshold", 70)
            
            status = "Enabled" if enabled else "Disabled"
            await ctx.send(f"Excessive caps filter: {status}\nThreshold: {current_threshold}%")
        
        elif action.lower() == "enable":
            self.config[guild_id]["filters"]["caps"]["enabled"] = True
            self.config[guild_id]["filters"]["caps"]["threshold"] = threshold
            self.save_config()
            await ctx.send(f"Excessive caps filter has been enabled with a threshold of {threshold}%.")
        
        elif action.lower() == "disable":
            self.config[guild_id]["filters"]["caps"]["enabled"] = False
            self.save_config()
            await ctx.send("Excessive caps filter has been disabled.")
    
    @filter.command()
    @commands.has_permissions(administrator=True)
    async def links(self, ctx, action="status"):
        """Configure the link filter"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.config:
            self.config[guild_id] = {}
        
        if "filters" not in self.config[guild_id]:
            self.config[guild_id]["filters"] = {}
        
        if "links" not in self.config[guild_id]["filters"]:
            self.config[guild_id]["filters"]["links"] = {
                "enabled": False
            }
        
        if action.lower() == "status":
            enabled = self.config[guild_id]["filters"]["links"].get("enabled", False)
            
            status = "Enabled" if enabled else "Disabled"
            await ctx.send(f"Link filter: {status}")
        
        elif action.lower() == "enable":
            self.config[guild_id]["filters"]["links"]["enabled"] = True
            self.save_config()
            await ctx.send("Link filter has been enabled.")
        
        elif action.lower() == "disable":
            self.config[guild_id]["filters"]["links"]["enabled"] = False
            self.save_config()
            await ctx.send("Link filter has been disabled.")
    
    @filter.command()
    @commands.has_permissions(administrator=True)
    async def invites(self, ctx, action="status"):
        """Configure the Discord invites filter"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.config:
            self.config[guild_id] = {}
        
        if "filters" not in self.config[guild_id]:
            self.config[guild_id]["filters"] = {}
        
        if "invites" not in self.config[guild_id]["filters"]:
            self.config[guild_id]["filters"]["invites"] = {
                "enabled": False
            }
        
        if action.lower() == "status":
            enabled = self.config[guild_id]["filters"]["invites"].get("enabled", False)
            
            status = "Enabled" if enabled else "Disabled"
            await ctx.send(f"Discord invites filter: {status}")
        
        elif action.lower() == "enable":
            self.config[guild_id]["filters"]["invites"]["enabled"] = True
            self.save_config()
            await ctx.send("Discord invites filter has been enabled.")
        
        elif action.lower() == "disable":
            self.config[guild_id]["filters"]["invites"]["enabled"] = False
            self.save_config()
            await ctx.send("Discord invites filter has been disabled.")
    
    @automod.command()
    @commands.has_permissions(administrator=True)
    async def exempt(self, ctx, target_type, target: discord.Role | discord.TextChannel):
        """Add a role or channel to the exempt list"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.config:
            self.config[guild_id] = {}
        
        if target_type.lower() not in ["role", "channel"]:
            return await ctx.send("Target type must be either 'role' or 'channel'.")
        
        if target_type.lower() == "role":
            if "exempt_roles" not in self.config[guild_id]:
                self.config[guild_id]["exempt_roles"] = []
            
            if str(target.id) not in self.config[guild_id]["exempt_roles"]:
                self.config[guild_id]["exempt_roles"].append(str(target.id))
                self.save_config()
                await ctx.send(f"Role {target.mention} is now exempt from automod.")
            else:
                await ctx.send(f"Role {target.mention} is already exempt from automod.")
        
        elif target_type.lower() == "channel":
            if "exempt_channels" not in self.config[guild_id]:
                self.config[guild_id]["exempt_channels"] = []
            
            if str(target.id) not in self.config[guild_id]["exempt_channels"]:
                self.config[guild_id]["exempt_channels"].append(str(target.id))
                self.save_config()
                await ctx.send(f"Channel {target.mention} is now exempt from automod.")
            else:
                await ctx.send(f"Channel {target.mention} is already exempt from automod.")
    
    @automod.command()
    @commands.has_permissions(administrator=True)
    async def unexempt(self, ctx, target_type, target: discord.Role | discord.TextChannel):
        """Remove a role or channel from the exempt list"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.config:
            return await ctx.send("AutoMod is not configured for this server.")
        
        if target_type.lower() not in ["role", "channel"]:
            return await ctx.send("Target type must be either 'role' or 'channel'.")
        
        if target_type.lower() == "role":
            if "exempt_roles" not in self.config[guild_id]:
                return await ctx.send("No exempt roles configured.")
            
            if str(target.id) in self.config[guild_id]["exempt_roles"]:
                self.config[guild_id]["exempt_roles"].remove(str(target.id))
                self.save_config()
                await ctx.send(f"Role {target.mention} is no longer exempt from automod.")
            else:
                await ctx.send(f"Role {target.mention} is not exempt from automod.")
        
        elif target_type.lower() == "channel":
            if "exempt_channels" not in self.config[guild_id]:
                return await ctx.send("No exempt channels configured.")
            
            if str(target.id) in self.config[guild_id]["exempt_channels"]:
                self.config[guild_id]["exempt_channels"].remove(str(target.id))
                self.save_config()
                await ctx.send(f"Channel {target.mention} is no longer exempt from automod.")
            else:
                await ctx.send(f"Channel {target.mention} is not exempt from automod.")
    
    @automod.command()
    @commands.has_permissions(administrator=True)
    async def punishment(self, ctx, violation, action):
        """Set punishment for a violation"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.config:
            self.config[guild_id] = {}
        
        if "punishments" not in self.config[guild_id]:
            self.config[guild_id]["punishments"] = {}
        
        valid_violations = ["banned_words", "caps", "spam", "links", "invites"]
        valid_actions = ["delete", "warn", "mute", "kick", "ban"]
        
        if violation not in valid_violations:
            return await ctx.send(f"Invalid violation type. Valid types: {', '.join(valid_violations)}")
        
        if action not in valid_actions:
            return await ctx.send(f"Invalid action. Valid actions: {', '.join(valid_actions)}")
        
        self.config[guild_id]["punishments"][violation] = action
        self.save_config()
        
        await ctx.send(f"Punishment for {violation} has been set to {action}.")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Check messages for automod violations"""
        # Ignore messages from bots
        if message.author.bot:
            return
        
        # Ignore DMs
        if not message.guild:
            return
        
        guild_id = str(message.guild.id)
        
        # Check if automod is configured for this guild
        if guild_id not in self.config:
            return
        
        # Check if user or channel is exempt
        if "exempt_roles" in self.config[guild_id]:
            user_roles = [str(role.id) for role in message.author.roles]
            if any(role_id in self.config[guild_id]["exempt_roles"] for role_id in user_roles):
                return
        
        if "exempt_channels" in self.config[guild_id]:
            if str(message.channel.id) in self.config[guild_id]["exempt_channels"]:
                return
        
        # Check for violations
        violation = None
        
        # Check banned words
        if "filters" in self.config[guild_id] and "banned_words" in self.config[guild_id]["filters"]:
            if self.config[guild_id]["filters"]["banned_words"].get("enabled", False):
                banned_words = self.config[guild_id]["filters"]["banned_words"].get("words", [])
                content_lower = message.content.lower()
                
                for word in banned_words:
                    if word.lower() in content_lower:
                        violation = "banned_words"
                        break
        
        # Check excessive caps
        if not violation and "filters" in self.config[guild_id] and "caps" in self.config[guild_id]["filters"]:
            if self.config[guild_id]["filters"]["caps"].get("enabled", False):
                threshold = self.config[guild_id]["filters"]["caps"].get("threshold", 70)
                
                if len(message.content) >= 8:  # Only check messages with at least 8 characters
                    caps_count = sum(1 for c in message.content if c.isupper())
                    total_chars = sum(1 for c in message.content if c.isalpha())
                    
                    if total_chars > 0 and (caps_count / total_chars) * 100 >= threshold:
                        violation = "caps"
        
        # Check links
        if not violation and "filters" in self.config[guild_id] and "links" in self.config[guild_id]["filters"]:
            if self.config[guild_id]["filters"]["links"].get("enabled", False):
                # Simple URL pattern
                url_pattern = re.compile(r'https?://\S+')
                if url_pattern.search(message.content):
                    violation = "links"
        
        # Check Discord invites
        if not violation and "filters" in self.config[guild_id] and "invites" in self.config[guild_id]["filters"]:
            if self.config[guild_id]["filters"]["invites"].get("enabled", False):
                invite_pattern = re.compile(r'discord(?:\.gg|app\.com/invite)/\S+')
                if invite_pattern.search(message.content):
                    violation = "invites"
        
        # Apply punishment if violation found
        if violation:
            punishment = self.config[guild_id].get("punishments", {}).get(violation, "delete")
            
            # Delete message
            if punishment in ["delete", "warn", "mute", "kick", "ban"]:
                try:
                    await message.delete()
                except:
                    pass
            
            # Apply additional punishment
            if punishment == "warn":
                await add_punishment(message.author.id, "warn", f"AutoMod: {violation}")
                await message.channel.send(f"{message.author.mention} has been warned for violating the {violation} filter.", delete_after=5)
            
            elif punishment == "mute":
                # Get moderation cog to handle mute
                mod_cog = self.bot.get_cog("Moderation")
                if mod_cog:
                    ctx = await self.bot.get_context(message)
                    await mod_cog.mute(ctx, message.author, 3600, reason=f"AutoMod: {violation}")
            
            elif punishment == "kick":
                try:
                    await message.author.kick(reason=f"AutoMod: {violation}")
                    await message.channel.send(f"{message.author.mention} has been kicked for violating the {violation} filter.", delete_after=5)
                except:
                    pass
            
            elif punishment == "ban":
                try:
                    await message.author.ban(reason=f"AutoMod: {violation}")
                    await message.channel.send(f"{message.author.mention} has been banned for violating the {violation} filter.", delete_after=5)
                except:
                    pass

async def setup(bot):
    await bot.add_cog(AutoMod(bot))
