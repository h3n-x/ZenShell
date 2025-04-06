import discord
from discord.ext import commands
import asyncio
import datetime
import json
import os

class PollView(discord.ui.View):
    def __init__(self, options, timeout=None):
        super().__init__(timeout=timeout)
        self.options = options
        self.votes = {option: 0 for option in options}
        self.voters = {}
        
        # Add buttons for each option
        for i, option in enumerate(options):
            button = discord.ui.Button(
                label=option, 
                custom_id=f"poll_option_{i}",
                style=discord.ButtonStyle.primary
            )
            button.callback = self.vote_callback
            self.add_item(button)
    
    async def vote_callback(self, interaction: discord.Interaction):
        # Get the selected option
        option_id = interaction.data["custom_id"]
        option_index = int(option_id.split("_")[-1])
        selected_option = self.options[option_index]
        
        # Check if user has already voted
        if interaction.user.id in self.voters:
            # Remove previous vote
            previous_option = self.voters[interaction.user.id]
            self.votes[previous_option] -= 1
        
        # Add new vote
        self.votes[selected_option] += 1
        self.voters[interaction.user.id] = selected_option
        
        # Update the message with new vote counts
        embed = interaction.message.embeds[0]
        
        # Update vote counts in the description
        description = embed.description.split("\n\n")[0] + "\n\n"
        for option in self.options:
            votes = self.votes[option]
            description += f"**{option}**: {votes} vote{'s' if votes != 1 else ''}\n"
        
        embed.description = description
        
        await interaction.response.edit_message(embed=embed)

class Polls(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_polls = {}
        self.load_polls()
    
    def load_polls(self):
        """Load active polls from file"""
        config_path = 'config/polls.json'
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.active_polls = json.load(f)
            except Exception as e:
                print(f"Error loading polls: {e}")
    
    def save_polls(self):
        """Save active polls to file"""
        config_path = 'config/polls.json'
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        try:
            with open(config_path, 'w') as f:
                json.dump(self.active_polls, f, indent=4)
        except Exception as e:
            print(f"Error saving polls: {e}")
    
    @commands.group(invoke_without_command=True)
    async def poll(self, ctx):
        """Create and manage polls"""
        await ctx.send_help(ctx.command)
    
    @poll.command()
    async def create(self, ctx, question: str, *options):
        """Create a new poll with the given question and options"""
        if len(options) < 2:
            return await ctx.send("You need to provide at least 2 options for a poll.")
        
        if len(options) > 10:
            return await ctx.send("You can only have up to 10 options in a poll.")
        
        # Create embed
        embed = discord.Embed(
            title=f"📊 Poll: {question}",
            description=f"Vote by clicking on one of the options below.\n\n" + "\n".join([f"**{option}**: 0 votes" for option in options]),
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        
        embed.set_footer(text=f"Poll created by {ctx.author.display_name}")
        
        # Create view with buttons
        view = PollView(options)
        
        # Send poll message
        poll_message = await ctx.send(embed=embed, view=view)
        
        # Save poll data
        poll_id = str(poll_message.id)
        self.active_polls[poll_id] = {
            "question": question,
            "options": list(options),
            "channel_id": str(ctx.channel.id),
            "message_id": poll_id,
            "creator_id": str(ctx.author.id),
            "created_at": datetime.datetime.now().timestamp()
        }
        
        self.save_polls()
    
    @poll.command()
    async def quickpoll(self, ctx, *, question: str):
        """Create a quick yes/no poll"""
        options = ["Yes", "No"]
        
        # Create embed
        embed = discord.Embed(
            title=f"📊 Poll: {question}",
            description=f"Vote by clicking on one of the options below.\n\n" + "\n".join([f"**{option}**: 0 votes" for option in options]),
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        
        embed.set_footer(text=f"Poll created by {ctx.author.display_name}")
        
        # Create view with buttons
        view = PollView(options)
        
        # Send poll message
        poll_message = await ctx.send(embed=embed, view=view)
        
        # Save poll data
        poll_id = str(poll_message.id)
        self.active_polls[poll_id] = {
            "question": question,
            "options": options,
            "channel_id": str(ctx.channel.id),
            "message_id": poll_id,
            "creator_id": str(ctx.author.id),
            "created_at": datetime.datetime.now().timestamp()
        }
        
        self.save_polls()
    
    @poll.command()
    async def end(self, ctx, message_id: str):
        """End a poll and display the results"""
        if message_id not in self.active_polls:
            return await ctx.send("Poll not found. Make sure you're using the correct message ID.")
        
        poll_data = self.active_polls[message_id]
        
        # Check if user is the creator or has manage messages permission
        if str(ctx.author.id) != poll_data["creator_id"] and not ctx.author.guild_permissions.manage_messages:
            return await ctx.send("You don't have permission to end this poll.")
        
        # Get the poll message
        try:
            channel = self.bot.get_channel(int(poll_data["channel_id"]))
            if not channel:
                return await ctx.send("Poll channel not found.")
            
            message = await channel.fetch_message(int(message_id))
            if not message:
                return await ctx.send("Poll message not found.")
            
            # Get the current votes
            embed = message.embeds[0]
            description = embed.description.split("\n\n")[1]
            
            # Parse vote counts
            votes = {}
            for line in description.split("\n"):
                if line:
                    option, count = line.split("**: ")
                    option = option.replace("**", "")
                    count = int(count.split(" ")[0])
                    votes[option] = count
            
            # Find the winner(s)
            max_votes = max(votes.values()) if votes else 0
            winners = [option for option, count in votes.items() if count == max_votes]
            
            # Create results embed
            results_embed = discord.Embed(
                title=f"📊 Poll Results: {poll_data['question']}",
                color=discord.Color.green(),
                timestamp=datetime.datetime.now()
            )
            
            # Add results
            results_text = ""
            for option in poll_data["options"]:
                vote_count = votes.get(option, 0)
                winner_marker = " 👑" if option in winners and max_votes > 0 else ""
                results_text += f"**{option}**: {vote_count} vote{'s' if vote_count != 1 else ''}{winner_marker}\n"
            
            results_embed.description = results_text
            
            # Add winner announcement
            if max_votes > 0:
                if len(winners) == 1:
                    results_embed.add_field(
                        name="Winner",
                        value=f"**{winners[0]}** with {max_votes} vote{'s' if max_votes != 1 else ''}!",
                        inline=False
                    )
                else:
                    results_embed.add_field(
                        name="Tie",
                        value=f"It's a tie between **{', '.join(winners)}** with {max_votes} vote{'s' if max_votes != 1 else ''} each!",
                        inline=False
                    )
            else:
                results_embed.add_field(
                    name="No Votes",
                    value="No one voted in this poll.",
                    inline=False
                )
            
            results_embed.set_footer(text=f"Poll ended by {ctx.author.display_name}")
            
            # Update the original message
            await message.edit(embed=results_embed, view=None)
            
            # Remove from active polls
            del self.active_polls[message_id]
            self.save_polls()
            
            await ctx.send("Poll ended and results displayed.")
            
        except Exception as e:
            await ctx.send(f"Error ending poll: {e}")
    
    @poll.command()
    async def list(self, ctx):
        """List all active polls in this server"""
        # Filter polls for this guild
        guild_polls = {}
        for poll_id, poll_data in self.active_polls.items():
            channel = self.bot.get_channel(int(poll_data["channel_id"]))
            if channel and channel.guild.id == ctx.guild.id:
                guild_polls[poll_id] = poll_data
        
        if not guild_polls:
            return await ctx.send("No active polls in this server.")
        
        embed = discord.Embed(
            title="Active Polls",
            color=discord.Color.blue()
        )
        
        for poll_id, poll_data in guild_polls.items():
            created_at = datetime.datetime.fromtimestamp(poll_data["created_at"])
            time_ago = (datetime.datetime.now() - created_at).total_seconds()
            
            # Format time ago
            if time_ago < 60:
                time_str = f"{int(time_ago)} seconds ago"
            elif time_ago < 3600:
                time_str = f"{int(time_ago / 60)} minutes ago"
            elif time_ago < 86400:
                time_str = f"{int(time_ago / 3600)} hours ago"
            else:
                time_str = f"{int(time_ago / 86400)} days ago"
            
            channel = self.bot.get_channel(int(poll_data["channel_id"]))
            channel_mention = channel.mention if channel else "Unknown channel"
            
            embed.add_field(
                name=f"ID: {poll_id}",
                value=f"Question: {poll_data['question']}\nCreated: {time_str}\nChannel: {channel_mention}",
                inline=False
            )
        
        await ctx.send(embed=embed)

class Voting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def vote(self, ctx, *, question: str):
        """Start a reaction-based vote"""
        # Create embed
        embed = discord.Embed(
            title="🗳️ Vote",
            description=question,
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        
        embed.set_footer(text=f"Vote started by {ctx.author.display_name}")
        
        # Send message
        vote_message = await ctx.send(embed=embed)
        
        # Add reactions
        await vote_message.add_reaction("👍")
        await vote_message.add_reaction("👎")
        await vote_message.add_reaction("🤷")
    
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def strawpoll(self, ctx, title: str, *options):
        """Create a strawpoll"""
        if len(options) < 2:
            return await ctx.send("You need to provide at least 2 options for a strawpoll.")
        
        if len(options) > 10:
            return await ctx.send("You can only have up to 10 options in a strawpoll.")
        
        # Create embed
        embed = discord.Embed(
            title=f"🗳️ {title}",
            description="React with the corresponding emoji to vote!",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        
        # Add options with number emojis
        number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        for i, option in enumerate(options):
            embed.add_field(name=f"{number_emojis[i]} {option}", value="\u200b", inline=False)
        
        embed.set_footer(text=f"Poll created by {ctx.author.display_name}")
        
        # Send message
        poll_message = await ctx.send(embed=embed)
        
        # Add reactions
        for i in range(len(options)):
            await poll_message.add_reaction(number_emojis[i])

async def setup(bot):
    await bot.add_cog(Polls(bot))
    await bot.add_cog(Voting(bot))
