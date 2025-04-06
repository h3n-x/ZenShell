import discord
from discord.ext import commands, tasks
import asyncio
import datetime
import json
import os
import re
import dateutil.parser
from dateutil.relativedelta import relativedelta

class Reminders(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reminders = {}
        self.load_reminders()
        self.check_reminders.start()
    
    def cog_unload(self):
        self.check_reminders.cancel()
    
    def load_reminders(self):
        """Load reminders from file"""
        config_path = 'config/reminders.json'
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.reminders = json.load(f)
            except Exception as e:
                print(f"Error loading reminders: {e}")
    
    def save_reminders(self):
        """Save reminders to file"""
        config_path = 'config/reminders.json'
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        try:
            with open(config_path, 'w') as f:
                json.dump(self.reminders, f, indent=4)
        except Exception as e:
            print(f"Error saving reminders: {e}")
    
    @tasks.loop(seconds=30)
    async def check_reminders(self):
        """Check for due reminders"""
        current_time = datetime.datetime.now().timestamp()
        due_reminders = []
        
        for reminder_id, reminder in self.reminders.items():
            if reminder["due_time"] <= current_time and not reminder.get("completed", False):
                # Mark as completed
                self.reminders[reminder_id]["completed"] = True
                due_reminders.append(reminder_id)
        
        self.save_reminders()
        
        # Process due reminders
        for reminder_id in due_reminders:
            await self.send_reminder(reminder_id)
    
    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()
    
    async def send_reminder(self, reminder_id):
        """Send a reminder notification"""
        reminder = self.reminders[reminder_id]
        
        # Get user and channel
        try:
            user = await self.bot.fetch_user(int(reminder["user_id"]))
            if not user:
                return
            
            channel_id = reminder.get("channel_id")
            channel = None
            
            if channel_id:
                channel = self.bot.get_channel(int(channel_id))
            
            # Create embed
            embed = discord.Embed(
                title="⏰ Reminder",
                description=reminder["content"],
                color=discord.Color.blue(),
                timestamp=datetime.datetime.now()
            )
            
            embed.set_footer(text=f"Reminder ID: {reminder_id}")
            
            # Send reminder
            if channel and reminder.get("public", False):
                await channel.send(f"{user.mention}, here's your reminder:", embed=embed)
            else:
                try:
                    await user.send(embed=embed)
                except discord.Forbidden:
                    # If DMs are closed and we have a channel, send there
                    if channel:
                        await channel.send(f"{user.mention}, I couldn't DM you, so here's your reminder:", embed=embed)
            
        except Exception as e:
            print(f"Error sending reminder: {e}")
    
    @commands.group(invoke_without_command=True, aliases=["remind", "reminder"])
    async def reminders(self, ctx):
        """Manage reminders"""
        await ctx.send_help(ctx.command)
    
    @reminders.command(name="add", aliases=["create", "set"])
    async def add_reminder(self, ctx, time: str, *, content: str):
        """Add a new reminder
        
        Examples:
        !reminders add 1h30m Check the oven
        !reminders add tomorrow at 3pm Call mom
        !reminders add 2023-12-25 Christmas day!
        """
        # Parse the time
        due_time = self.parse_time(time)
        
        if not due_time:
            return await ctx.send("Invalid time format. Please use a valid date/time or a relative time (e.g., 1h30m, tomorrow at 3pm).")
        
        # Check if time is in the past
        if due_time < datetime.datetime.now():
            return await ctx.send("Cannot set a reminder for a time in the past.")
        
        # Generate reminder ID
        reminder_id = str(int(datetime.datetime.now().timestamp()))
        
        # Create reminder
        self.reminders[reminder_id] = {
            "user_id": str(ctx.author.id),
            "channel_id": str(ctx.channel.id),
            "content": content,
            "created_time": datetime.datetime.now().timestamp(),
            "due_time": due_time.timestamp(),
            "completed": False,
            "public": False
        }
        
        self.save_reminders()
        
        # Format due time for display
        time_str = due_time.strftime("%Y-%m-%d %H:%M:%S")
        time_until = self.format_time_until(due_time - datetime.datetime.now())
        
        # Send confirmation
        embed = discord.Embed(
            title="⏰ Reminder Set",
            description=f"I'll remind you about: **{content}**",
            color=discord.Color.green()
        )
        
        embed.add_field(name="When", value=f"{time_str} ({time_until})", inline=False)
        embed.add_field(name="Reminder ID", value=reminder_id, inline=False)
        
        await ctx.send(embed=embed)
    
    @reminders.command(name="list")
    async def list_reminders(self, ctx):
        """List all your active reminders"""
        # Filter reminders for this user
        user_reminders = {}
        for reminder_id, reminder in self.reminders.items():
            if reminder["user_id"] == str(ctx.author.id) and not reminder.get("completed", False):
                user_reminders[reminder_id] = reminder
        
        if not user_reminders:
            return await ctx.send("You don't have any active reminders.")
        
        # Sort reminders by due time
        sorted_reminders = sorted(user_reminders.items(), key=lambda x: x[1]["due_time"])
        
        embed = discord.Embed(
            title="Your Reminders",
            color=discord.Color.blue()
        )
        
        for reminder_id, reminder in sorted_reminders:
            due_time = datetime.datetime.fromtimestamp(reminder["due_time"])
            time_until = self.format_time_until(due_time - datetime.datetime.now())
            
            embed.add_field(
                name=f"ID: {reminder_id}",
                value=f"**Content:** {reminder['content']}\n**Due:** {due_time.strftime('%Y-%m-%d %H:%M:%S')} ({time_until})",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @reminders.command(name="remove", aliases=["delete", "cancel"])
    async def remove_reminder(self, ctx, reminder_id: str):
        """Remove a reminder by ID"""
        if reminder_id not in self.reminders:
            return await ctx.send("Reminder not found. Use `!reminders list` to see your reminders.")
        
        reminder = self.reminders[reminder_id]
        
        # Check if the reminder belongs to the user
        if reminder["user_id"] != str(ctx.author.id):
            return await ctx.send("That reminder doesn't belong to you.")
        
        # Remove the reminder
        content = reminder["content"]
        del self.reminders[reminder_id]
        self.save_reminders()
        
        await ctx.send(f"Reminder canceled: **{content}**")
    
    @reminders.command(name="clear")
    async def clear_reminders(self, ctx):
        """Clear all your reminders"""
        # Filter reminders for this user
        user_reminders = {}
        for reminder_id, reminder in list(self.reminders.items()):
            if reminder["user_id"] == str(ctx.author.id):
                del self.reminders[reminder_id]
        
        self.save_reminders()
        
        await ctx.send("All your reminders have been cleared.")
    
    @reminders.command(name="public")
    async def public_reminder(self, ctx, time: str, *, content: str):
        """Set a public reminder that will be sent in the channel
        
        Examples:
        !reminders public 1h30m Team meeting
        !reminders public tomorrow at 3pm Game night
        """
        # Parse the time
        due_time = self.parse_time(time)
        
        if not due_time:
            return await ctx.send("Invalid time format. Please use a valid date/time or a relative time (e.g., 1h30m, tomorrow at 3pm).")
        
        # Check if time is in the past
        if due_time < datetime.datetime.now():
            return await ctx.send("Cannot set a reminder for a time in the past.")
        
        # Generate reminder ID
        reminder_id = str(int(datetime.datetime.now().timestamp()))
        
        # Create reminder
        self.reminders[reminder_id] = {
            "user_id": str(ctx.author.id),
            "channel_id": str(ctx.channel.id),
            "content": content,
            "created_time": datetime.datetime.now().timestamp(),
            "due_time": due_time.timestamp(),
            "completed": False,
            "public": True
        }
        
        self.save_reminders()
        
        # Format due time for display
        time_str = due_time.strftime("%Y-%m-%d %H:%M:%S")
        time_until = self.format_time_until(due_time - datetime.datetime.now())
        
        # Send confirmation
        embed = discord.Embed(
            title="⏰ Public Reminder Set",
            description=f"I'll remind everyone about: **{content}**",
            color=discord.Color.green()
        )
        
        embed.add_field(name="When", value=f"{time_str} ({time_until})", inline=False)
        embed.add_field(name="Reminder ID", value=reminder_id, inline=False)
        embed.add_field(name="Channel", value=ctx.channel.mention, inline=False)
        
        await ctx.send(embed=embed)
    
    def parse_time(self, time_str):
        """Parse a time string into a datetime object"""
        now = datetime.datetime.now()
        
        # Try to parse as an absolute date/time
        try:
            return dateutil.parser.parse(time_str)
        except:
            pass
        
        # Try to parse as a relative time (e.g., 1h30m)
        time_pattern = re.compile(r'(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?')
        match = time_pattern.fullmatch(time_str)
        
        if match:
            days, hours, minutes, seconds = match.groups()
            
            delta = relativedelta(
                days=int(days) if days else 0,
                hours=int(hours) if hours else 0,
                minutes=int(minutes) if minutes else 0,
                seconds=int(seconds) if seconds else 0
            )
            
            return now + delta
        
        # Try to parse common phrases
        time_str = time_str.lower()
        
        if "tomorrow" in time_str:
            # Tomorrow at specific time
            time_match = re.search(r'at (\d+)(?::(\d+))?\s*(am|pm)?', time_str)
            if time_match:
                hour, minute, ampm = time_match.groups()
                hour = int(hour)
                minute = int(minute) if minute else 0
                
                if ampm:
                    if ampm.lower() == "pm" and hour < 12:
                        hour += 12
                    elif ampm.lower() == "am" and hour == 12:
                        hour = 0
                
                return datetime.datetime(now.year, now.month, now.day, hour, minute) + datetime.timedelta(days=1)
            else:
                # Just tomorrow (same time)
                return now + datetime.timedelta(days=1)
        
        if "next week" in time_str:
            return now + datetime.timedelta(weeks=1)
        
        # Failed to parse
        return None
    
    def format_time_until(self, delta):
        """Format a timedelta into a human-readable string"""
        seconds = int(delta.total_seconds())
        
        if seconds < 0:
            return "in the past"
        
        days, remainder = divmod(seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        
        if days > 0:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        
        if seconds > 0 and not parts:
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
        
        if not parts:
            return "now"
        
        return "in " + ", ".join(parts)

class TodoList(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.todos = {}
        self.load_todos()
    
    def load_todos(self):
        """Load todos from file"""
        config_path = 'config/todos.json'
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.todos = json.load(f)
            except Exception as e:
                print(f"Error loading todos: {e}")
    
    def save_todos(self):
        """Save todos to file"""
        config_path = 'config/todos.json'
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        try:
            with open(config_path, 'w') as f:
                json.dump(self.todos, f, indent=4)
        except Exception as e:
            print(f"Error saving todos: {e}")
    
    @commands.group(invoke_without_command=True, aliases=["todo"])
    async def todos(self, ctx):
        """Manage your to-do list"""
        await self.list_todos(ctx)
    
    @todos.command(name="add")
    async def add_todo(self, ctx, *, content: str):
        """Add a new to-do item"""
        user_id = str(ctx.author.id)
        
        if user_id not in self.todos:
            self.todos[user_id] = []
        
        # Generate todo ID
        todo_id = len(self.todos[user_id]) + 1
        
        # Add todo
        self.todos[user_id].append({
            "id": todo_id,
            "content": content,
            "created_at": datetime.datetime.now().timestamp(),
            "completed": False
        })
        
        self.save_todos()
        
        await ctx.send(f"✅ Added to your to-do list: **{content}**")
    
    @todos.command(name="list")
    async def list_todos(self, ctx):
        """List all your to-do items"""
        user_id = str(ctx.author.id)
        
        if user_id not in self.todos or not self.todos[user_id]:
            return await ctx.send("Your to-do list is empty.")
        
        # Create embed
        embed = discord.Embed(
            title=f"{ctx.author.display_name}'s To-Do List",
            color=discord.Color.blue()
        )
        
        # Add incomplete todos
        incomplete = [todo for todo in self.todos[user_id] if not todo["completed"]]
        if incomplete:
            incomplete_text = "\n".join([f"{todo['id']}. {todo['content']}" for todo in incomplete])
            embed.add_field(name="📝 To Do", value=incomplete_text, inline=False)
        
        # Add completed todos
        completed = [todo for todo in self.todos[user_id] if todo["completed"]]
        if completed:
            completed_text = "\n".join([f"{todo['id']}. ~~{todo['content']}~~" for todo in completed])
            embed.add_field(name="✅ Completed", value=completed_text, inline=False)
        
        await ctx.send(embed=embed)
    
    @todos.command(name="complete", aliases=["done"])
    async def complete_todo(self, ctx, todo_id: int):
        """Mark a to-do item as complete"""
        user_id = str(ctx.author.id)
        
        if user_id not in self.todos:
            return await ctx.send("Your to-do list is empty.")
        
        # Find the todo
        for todo in self.todos[user_id]:
            if todo["id"] == todo_id:
                if todo["completed"]:
                    return await ctx.send("This to-do item is already marked as complete.")
                
                todo["completed"] = True
                self.save_todos()
                
                return await ctx.send(f"✅ Marked as complete: **{todo['content']}**")
        
        await ctx.send(f"No to-do item found with ID {todo_id}.")
    
    @todos.command(name="uncomplete", aliases=["undo"])
    async def uncomplete_todo(self, ctx, todo_id: int):
        """Mark a completed to-do item as incomplete"""
        user_id = str(ctx.author.id)
        
        if user_id not in self.todos:
            return await ctx.send("Your to-do list is empty.")
        
        # Find the todo
        for todo in self.todos[user_id]:
            if todo["id"] == todo_id:
                if not todo["completed"]:
                    return await ctx.send("This to-do item is not marked as complete.")
                
                todo["completed"] = False
                self.save_todos()
                
                return await ctx.send(f"📝 Marked as incomplete: **{todo['content']}**")
        
        await ctx.send(f"No to-do item found with ID {todo_id}.")
    
    @todos.command(name="remove", aliases=["delete"])
    async def remove_todo(self, ctx, todo_id: int):
        """Remove a to-do item"""
        user_id = str(ctx.author.id)
        
        if user_id not in self.todos:
            return await ctx.send("Your to-do list is empty.")
        
        # Find and remove the todo
        for i, todo in enumerate(self.todos[user_id]):
            if todo["id"] == todo_id:
                removed = self.todos[user_id].pop(i)
                self.save_todos()
                
                return await ctx.send(f"🗑️ Removed from your to-do list: **{removed['content']}**")
        
        await ctx.send(f"No to-do item found with ID {todo_id}.")
    
    @todos.command(name="clear")
    async def clear_todos(self, ctx, option: str = "all"):
        """Clear your to-do list
        
        Options:
        all - Clear all items
        completed - Clear only completed items
        """
        user_id = str(ctx.author.id)
        
        if user_id not in self.todos or not self.todos[user_id]:
            return await ctx.send("Your to-do list is already empty.")
        
        if option.lower() == "all":
            self.todos[user_id] = []
            self.save_todos()
            
            await ctx.send("🗑️ Cleared your entire to-do list.")
        
        elif option.lower() == "completed":
            self.todos[user_id] = [todo for todo in self.todos[user_id] if not todo["completed"]]
            self.save_todos()
            
            await ctx.send("🗑️ Cleared all completed items from your to-do list.")
        
        else:
            await ctx.send("Invalid option. Use `all` or `completed`.")

async def setup(bot):
    await bot.add_cog(Reminders(bot))
    await bot.add_cog(TodoList(bot))
