import discord
from discord.ext import commands, tasks
import asyncio
import datetime
import json
import os
import random

class Giveaways(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.giveaways = {}
        self.load_giveaways()
        self.check_giveaways.start()
    
    def cog_unload(self):
        self.check_giveaways.cancel()
    
    def load_giveaways(self):
        """Load giveaways from file"""
        config_path = 'config/giveaways.json'
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.giveaways = json.load(f)
            except Exception as e:
                print(f"Error loading giveaways: {e}")
    
    def save_giveaways(self):
        """Save giveaways to file"""
        config_path = 'config/giveaways.json'
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        try:
            with open(config_path, 'w') as f:
                json.dump(self.giveaways, f, indent=4)
        except Exception as e:
            print(f"Error saving giveaways: {e}")
    
    @tasks.loop(seconds=30)
    async def check_giveaways(self):
        """Check for ended giveaways"""
        current_time = datetime.datetime.now().timestamp()
        ended_giveaways = []
        
        for giveaway_id, giveaway in self.giveaways.items():
            if giveaway["end_time"] <= current_time and not giveaway.get("ended", False):
                # Mark as ended
                self.giveaways[giveaway_id]["ended"] = True
                ended_giveaways.append(giveaway_id)
        
        self.save_giveaways()
        
        # Process ended giveaways
        for giveaway_id in ended_giveaways:
            await self.end_giveaway(giveaway_id)
    
    @check_giveaways.before_loop
    async def before_check_giveaways(self):
        await self.bot.wait_until_ready()
    
    async def end_giveaway(self, giveaway_id):
        """End a giveaway and select winner(s)"""
        giveaway = self.giveaways[giveaway_id]
        
        # Get channel and message
        try:
            channel = self.bot.get_channel(int(giveaway["channel_id"]))
            if not channel:
                return
            
            message = await channel.fetch_message(int(giveaway["message_id"]))
            if not message:
                return
            
            # Get reactions
            reaction = discord.utils.get(message.reactions, emoji="🎉")
            if not reaction:
                await channel.send(f"No one entered the giveaway for {giveaway['prize']}!")
                return
            
            # Get users who reacted
            users = []
            async for user in reaction.users():
                if not user.bot:
                    users.append(user)
            
            if not users:
                await channel.send(f"No one entered the giveaway for {giveaway['prize']}!")
                return
            
            # Select winner(s)
            winners_count = min(giveaway.get("winners", 1), len(users))
            winners = random.sample(users, winners_count)
            
            # Create winners announcement
            winners_mentions = ", ".join([winner.mention for winner in winners])
            
            embed = discord.Embed(
                title="🎉 Giveaway Ended!",
                description=f"Prize: **{giveaway['prize']}**",
                color=discord.Color.green(),
                timestamp=datetime.datetime.now()
            )
            
            embed.add_field(name="Winner(s)", value=winners_mentions, inline=False)
            embed.add_field(name="Total Entries", value=str(len(users)), inline=False)
            embed.set_footer(text=f"Giveaway ID: {giveaway_id}")
            
            # Update original message
            await message.edit(embed=embed)
            
            # Send winner announcement
            await channel.send(
                f"🎉 Congratulations {winners_mentions}! You won **{giveaway['prize']}**!",
                reference=message
            )
            
        except Exception as e:
            print(f"Error ending giveaway: {e}")
    
    @commands.group(invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def giveaway(self, ctx):
        """Manage giveaways"""
        await ctx.send_help(ctx.command)
    
    @giveaway.command()
    @commands.has_permissions(manage_guild=True)
    async def start(self, ctx, duration: str, winners: int, *, prize: str):
        """Start a new giveaway"""
        # Parse duration (e.g., 1d, 2h, 30m)
        duration_seconds = 0
        time_units = {
            'd': 86400,  # days
            'h': 3600,   # hours
            'm': 60      # minutes
        }
        
        import re
        time_pattern = re.compile(r'(\d+)([dhm])')
        matches = time_pattern.findall(duration)
        
        if not matches:
            return await ctx.send("Invalid duration format. Use a combination of numbers and units (d, h, m). Example: 1d12h30m")
        
        for value, unit in matches:
            duration_seconds += int(value) * time_units[unit]
        
        if duration_seconds < 60:
            return await ctx.send("Giveaway duration must be at least 1 minute.")
        
        if winners < 1:
            return await ctx.send("Number of winners must be at least 1.")
        
        # Calculate end time
        end_time = datetime.datetime.now() + datetime.timedelta(seconds=duration_seconds)
        end_timestamp = end_time.timestamp()
        
        # Create embed
        embed = discord.Embed(
            title="🎉 Giveaway!",
            description=f"React with 🎉 to enter!\n\nPrize: **{prize}**",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="End Time", value=f"<t:{int(end_timestamp)}:R>", inline=True)
        embed.add_field(name="Winners", value=str(winners), inline=True)
        embed.add_field(name="Hosted by", value=ctx.author.mention, inline=True)
        embed.set_footer(text=f"Ends at • {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        # Send giveaway message
        giveaway_message = await ctx.send(embed=embed)
        await giveaway_message.add_reaction("🎉")
        
        # Generate giveaway ID
        giveaway_id = str(giveaway_message.id)
        
        # Save giveaway
        self.giveaways[giveaway_id] = {
            "prize": prize,
            "winners": winners,
            "end_time": end_timestamp,
            "channel_id": str(ctx.channel.id),
            "message_id": str(giveaway_message.id),
            "host_id": str(ctx.author.id),
            "ended": False
        }
        
        self.save_giveaways()
        
        await ctx.send(f"Giveaway started! ID: {giveaway_id}", delete_after=5)
    
    @giveaway.command()
    @commands.has_permissions(manage_guild=True)
    async def end(self, ctx, giveaway_id: str):
        """End a giveaway early"""
        if giveaway_id not in self.giveaways:
            return await ctx.send("Giveaway not found.")
        
        if self.giveaways[giveaway_id].get("ended", False):
            return await ctx.send("This giveaway has already ended.")
        
        # Mark as ended
        self.giveaways[giveaway_id]["ended"] = True
        self.save_giveaways()
        
        # End the giveaway
        await self.end_giveaway(giveaway_id)
        await ctx.send("Giveaway ended.")
    
    @giveaway.command()
    @commands.has_permissions(manage_guild=True)
    async def reroll(self, ctx, giveaway_id: str):
        """Reroll a giveaway winner"""
        if giveaway_id not in self.giveaways:
            return await ctx.send("Giveaway not found.")
        
        if not self.giveaways[giveaway_id].get("ended", False):
            return await ctx.send("This giveaway hasn't ended yet.")
        
        giveaway = self.giveaways[giveaway_id]
        
        # Get channel and message
        try:
            channel = self.bot.get_channel(int(giveaway["channel_id"]))
            if not channel:
                return await ctx.send("Giveaway channel not found.")
            
            message = await channel.fetch_message(int(giveaway["message_id"]))
            if not message:
                return await ctx.send("Giveaway message not found.")
            
            # Get reactions
            reaction = discord.utils.get(message.reactions, emoji="🎉")
            if not reaction:
                return await ctx.send("No reactions found on the giveaway message.")
            
            # Get users who reacted
            users = []
            async for user in reaction.users():
                if not user.bot:
                    users.append(user)
            
            if not users:
                return await ctx.send("No valid entries found for the giveaway.")
            
            # Select a new winner
            winner = random.choice(users)
            
            await channel.send(
                f"🎉 Giveaway rerolled! The new winner is {winner.mention}! Congratulations!",
                reference=message
            )
            
        except Exception as e:
            await ctx.send(f"Error rerolling giveaway: {e}")
    
    @giveaway.command()
    @commands.has_permissions(manage_guild=True)
    async def list(self, ctx):
        """List all active giveaways"""
        active_giveaways = {id: g for id, g in self.giveaways.items() if not g.get("ended", False)}
        
        if not active_giveaways:
            return await ctx.send("No active giveaways.")
        
        embed = discord.Embed(
            title="Active Giveaways",
            color=discord.Color.blue()
        )
        
        for giveaway_id, giveaway in active_giveaways.items():
            end_time = datetime.datetime.fromtimestamp(giveaway["end_time"])
            
            embed.add_field(
                name=f"ID: {giveaway_id}",
                value=f"Prize: {giveaway['prize']}\nEnds: <t:{int(giveaway['end_time'])}:R>\nWinners: {giveaway.get('winners', 1)}",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @giveaway.command()
    @commands.has_permissions(manage_guild=True)
    async def cancel(self, ctx, giveaway_id: str):
        """Cancel a giveaway"""
        if giveaway_id not in self.giveaways:
            return await ctx.send("Giveaway not found.")
        
        if self.giveaways[giveaway_id].get("ended", False):
            return await ctx.send("This giveaway has already ended.")
        
        # Get channel and message
        try:
            channel = self.bot.get_channel(int(self.giveaways[giveaway_id]["channel_id"]))
            if channel:
                message = await channel.fetch_message(int(self.giveaways[giveaway_id]["message_id"]))
                if message:
                    # Update embed
                    embed = discord.Embed(
                        title="🚫 Giveaway Cancelled",
                        description=f"Prize: **{self.giveaways[giveaway_id]['prize']}**",
                        color=discord.Color.red()
                    )
                    
                    await message.edit(embed=embed)
        except:
            pass
        
        # Remove from giveaways
        del self.giveaways[giveaway_id]
        self.save_giveaways()
        
        await ctx.send("Giveaway cancelled.")

async def setup(bot):
    await bot.add_cog(Giveaways(bot))
