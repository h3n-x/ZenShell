import discord
from discord.ext import commands
import random
import asyncio
import datetime
import json
import os
from utils.database import get_user, create_user, get_user_balance, update_user_balance

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_cooldown = commands.CooldownMapping.from_cooldown(1, 86400, commands.BucketType.user)  # 24 hours
        self.work_cooldown = commands.CooldownMapping.from_cooldown(1, 3600, commands.BucketType.user)  # 1 hour
        self.streak_data = {}
        self.shop_items = {}
        self.load_streak_data()
        self.load_shop_items()
    
    def load_streak_data(self):
        """Load streak data from file"""
        config_path = 'config/streaks.json'
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.streak_data = json.load(f)
            except Exception as e:
                print(f"Error loading streak data: {e}")
    
    def save_streak_data(self):
        """Save streak data to file"""
        config_path = 'config/streaks.json'
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        try:
            with open(config_path, 'w') as f:
                json.dump(self.streak_data, f, indent=4)
        except Exception as e:
            print(f"Error saving streak data: {e}")
    
    def load_shop_items(self):
        """Load shop items from file"""
        config_path = 'config/shop.json'
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.shop_items = json.load(f)
            except Exception as e:
                print(f"Error loading shop items: {e}")
        else:
            # Create default shop items
            self.shop_items = {
                "roles": {},
                "items": {
                    "1": {
                        "name": "VIP Status",
                        "description": "A special status that shows up in your profile",
                        "price": 5000,
                        "type": "status"
                    },
                    "2": {
                        "name": "Custom Command",
                        "description": "Create a custom command that responds with a message of your choice",
                        "price": 10000,
                        "type": "command"
                    }
                }
            }
            self.save_shop_items()
    
    def save_shop_items(self):
        """Save shop items to file"""
        config_path = 'config/shop.json'
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        try:
            with open(config_path, 'w') as f:
                json.dump(self.shop_items, f, indent=4)
        except Exception as e:
            print(f"Error saving shop items: {e}")
    
    @commands.command(aliases=["bal"])
    async def balance(self, ctx, member: discord.Member = None):
        """Check your or someone else's balance"""
        member = member or ctx.author
        
        # Get user data
        user = await get_user(member.id)
        if not user:
            # Create user if they don't exist
            await create_user(
                member.id,
                member.name,
                member.discriminator
            )
        
        # Get balance
        balance = await get_user_balance(member.id)
        
        # Create embed
        embed = discord.Embed(
            title=f"{member.display_name}'s Balance",
            color=member.color
        )
        embed.add_field(name="Coins", value=f"💰 {balance:,}", inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def daily(self, ctx):
        """Claim your daily reward"""
        # Check cooldown
        bucket = self.daily_cooldown.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()
        
        if retry_after:
            # Format time remaining
            hours, remainder = divmod(int(retry_after), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            time_str = ""
            if hours > 0:
                time_str += f"{hours} hour{'s' if hours != 1 else ''} "
            if minutes > 0:
                time_str += f"{minutes} minute{'s' if minutes != 1 else ''} "
            if seconds > 0:
                time_str += f"{seconds} second{'s' if seconds != 1 else ''}"
            
            return await ctx.send(f"You've already claimed your daily reward. Try again in {time_str}.")
        
        # Get user data
        user = await get_user(ctx.author.id)
        if not user:
            # Create user if they don't exist
            await create_user(
                ctx.author.id,
                ctx.author.name,
                ctx.author.discriminator
            )
        
        # Check streak
        user_id = str(ctx.author.id)
        current_time = datetime.datetime.now().timestamp()
        
        if user_id not in self.streak_data:
            self.streak_data[user_id] = {
                "last_claim": current_time,
                "streak": 1
            }
        else:
            last_claim = self.streak_data[user_id]["last_claim"]
            time_diff = current_time - last_claim
            
            # If claimed within 48 hours (24h cooldown + 24h grace period)
            if time_diff < 172800:  # 48 hours in seconds
                self.streak_data[user_id]["streak"] += 1
            else:
                # Streak broken
                self.streak_data[user_id]["streak"] = 1
            
            self.streak_data[user_id]["last_claim"] = current_time
        
        self.save_streak_data()
        
        # Calculate reward
        streak = self.streak_data[user_id]["streak"]
        base_reward = 100
        streak_bonus = min(streak * 10, 200)  # Cap streak bonus at 200
        total_reward = base_reward + streak_bonus
        
        # Update balance
        await update_user_balance(ctx.author.id, total_reward)
        
        # Create embed
        embed = discord.Embed(
            title="Daily Reward Claimed!",
            description=f"You've received **{total_reward}** coins!",
            color=discord.Color.green()
        )
        embed.add_field(name="Base Reward", value=f"{base_reward} coins", inline=True)
        embed.add_field(name="Streak Bonus", value=f"{streak_bonus} coins", inline=True)
        embed.add_field(name="Current Streak", value=f"🔥 {streak} day{'s' if streak != 1 else ''}", inline=False)
        
        # Add streak milestone bonuses
        if streak == 7:
            bonus = 500
            await update_user_balance(ctx.author.id, bonus)
            embed.add_field(name="7-Day Streak Bonus!", value=f"🎉 +{bonus} coins", inline=False)
        elif streak == 30:
            bonus = 2000
            await update_user_balance(ctx.author.id, bonus)
            embed.add_field(name="30-Day Streak Bonus!", value=f"🎉 +{bonus} coins", inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def work(self, ctx):
        """Work to earn coins"""
        # Check cooldown
        bucket = self.work_cooldown.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()
        
        if retry_after:
            # Format time remaining
            minutes, seconds = divmod(int(retry_after), 60)
            
            time_str = ""
            if minutes > 0:
                time_str += f"{minutes} minute{'s' if minutes != 1 else ''} "
            if seconds > 0:
                time_str += f"{seconds} second{'s' if seconds != 1 else ''}"
            
            return await ctx.send(f"You're still on break. You can work again in {time_str}.")
        
        # Get user data
        user = await get_user(ctx.author.id)
        if not user:
            # Create user if they don't exist
            await create_user(
                ctx.author.id,
                ctx.author.name,
                ctx.author.discriminator
            )
        
        # List of possible jobs
        jobs = [
            {"name": "Software Developer", "min": 150, "max": 300},
            {"name": "Teacher", "min": 100, "max": 250},
            {"name": "Chef", "min": 120, "max": 280},
            {"name": "Delivery Driver", "min": 80, "max": 200},
            {"name": "Streamer", "min": 50, "max": 500},
            {"name": "Artist", "min": 100, "max": 400},
            {"name": "Doctor", "min": 200, "max": 350},
            {"name": "Lawyer", "min": 180, "max": 320},
            {"name": "Musician", "min": 90, "max": 280},
            {"name": "Astronaut", "min": 250, "max": 400}
        ]
        
        # Choose a random job
        job = random.choice(jobs)
        
        # Calculate earnings
        earnings = random.randint(job["min"], job["max"])
        
        # Update balance
        await update_user_balance(ctx.author.id, earnings)
        
        # Create embed
        embed = discord.Embed(
            title="You worked as a " + job["name"],
            description=f"You earned **{earnings}** coins!",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def gamble(self, ctx, amount: int):
        """Gamble your coins for a chance to win more"""
        if amount <= 0:
            return await ctx.send("Amount must be positive.")
        
        # Get current balance
        balance = await get_user_balance(ctx.author.id)
        if not balance or balance < amount:
            return await ctx.send("You don't have enough coins.")
        
        # Roll the dice (1-100)
        roll = random.randint(1, 100)
        
        embed = discord.Embed(
            title="🎲 Gambling Results",
            color=discord.Color.gold()
        )
        
        # Determine outcome
        if roll <= 40:  # 40% chance to lose everything
            # Lose the bet
            await update_user_balance(ctx.author.id, -amount)
            embed.description = f"You rolled **{roll}** and lost **{amount}** coins!"
            embed.color = discord.Color.red()
        elif roll <= 60:  # 20% chance to break even
            # Break even
            embed.description = f"You rolled **{roll}** and broke even. Your bet has been returned."
            embed.color = discord.Color.blue()
        elif roll <= 90:  # 30% chance to win 1.5x
            # Win 1.5x
            winnings = int(amount * 1.5)
            await update_user_balance(ctx.author.id, winnings - amount)
            embed.description = f"You rolled **{roll}** and won **{winnings}** coins! (1.5x your bet)"
            embed.color = discord.Color.green()
        else:  # 10% chance to win 2x
            # Win 2x
            winnings = amount * 2
            await update_user_balance(ctx.author.id, winnings - amount)
            embed.description = f"You rolled **{roll}** and won **{winnings}** coins! (2x your bet)"
            embed.color = discord.Color.green()
        
        # Show new balance
        new_balance = await get_user_balance(ctx.author.id)
        embed.add_field(name="New Balance", value=f"💰 {new_balance} coins")
        
        await ctx.send(embed=embed)
    
    @commands.command()
    async def give(self, ctx, member: discord.Member, amount: int):
        """Give coins to another user"""
        if member.id == ctx.author.id:
            return await ctx.send("You can't give coins to yourself.")
        
        if amount <= 0:
            return await ctx.send("You must give a positive amount of coins.")
        
        # Get user balance
        balance = await get_user_balance(ctx.author.id)
        
        if amount > balance:
            return await ctx.send("You don't have enough coins to give that amount.")
        
        # Deduct from sender
        await update_user_balance(ctx.author.id, -amount)
        
        # Add to receiver
        await update_user_balance(member.id, amount)
        
        # Create embed
        embed = discord.Embed(
            title="Coins Transferred",
            description=f"{ctx.author.mention} gave {member.mention} **{amount}** coins!",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
    
    @commands.group(invoke_without_command=True)
    async def shop(self, ctx):
        """View the shop"""
        embed = discord.Embed(
            title="Server Shop",
            description="Use `!buy <item_id>` to purchase an item",
            color=discord.Color.gold()
        )
        
        # Add roles section if there are any
        guild_id = str(ctx.guild.id)
        if guild_id in self.shop_items.get("roles", {}) and self.shop_items["roles"][guild_id]:
            embed.add_field(name="Roles", value="", inline=False)
            
            for item_id, item in self.shop_items["roles"][guild_id].items():
                role = ctx.guild.get_role(int(item["role_id"]))
                if role:
                    embed.add_field(
                        name=f"ID: {item_id} - {role.name}",
                        value=f"Price: {item['price']} coins",
                        inline=True
                    )
        
        # Add items section
        if self.shop_items.get("items", {}):
            embed.add_field(name="Items", value="", inline=False)
            
            for item_id, item in self.shop_items["items"].items():
                embed.add_field(
                    name=f"ID: {item_id} - {item['name']}",
                    value=f"Price: {item['price']} coins\n{item['description']}",
                    inline=True
                )
        
        await ctx.send(embed=embed)
    
    @shop.command()
    @commands.has_permissions(administrator=True)
    async def addrole(self, ctx, role: discord.Role, price: int):
        """Add a role to the shop (admin only)"""
        if price <= 0:
            return await ctx.send("Price must be positive.")
        
        guild_id = str(ctx.guild.id)
        
        if "roles" not in self.shop_items:
            self.shop_items["roles"] = {}
        
        if guild_id not in self.shop_items["roles"]:
            self.shop_items["roles"][guild_id] = {}
        
        # Generate a new item ID
        item_id = str(len(self.shop_items["roles"][guild_id]) + 1)
        
        # Add the role to the shop
        self.shop_items["roles"][guild_id][item_id] = {
            "role_id": str(role.id),
            "price": price
        }
        
        self.save_shop_items()
        
        await ctx.send(f"Added {role.mention} to the shop for {price} coins.")
    
    @shop.command()
    @commands.has_permissions(administrator=True)
    async def removerole(self, ctx, item_id: str):
        """Remove a role from the shop (admin only)"""
        guild_id = str(ctx.guild.id)
        
        if "roles" not in self.shop_items or guild_id not in self.shop_items["roles"]:
            return await ctx.send("No roles in the shop for this server.")
        
        if item_id not in self.shop_items["roles"][guild_id]:
            return await ctx.send(f"No role with ID {item_id} in the shop.")
        
        role_id = self.shop_items["roles"][guild_id][item_id]["role_id"]
        role = ctx.guild.get_role(int(role_id))
        role_mention = role.mention if role else f"role with ID {role_id}"
        
        del self.shop_items["roles"][guild_id][item_id]
        self.save_shop_items()
        
        await ctx.send(f"Removed {role_mention} from the shop.")
    
    @shop.command()
    @commands.has_permissions(administrator=True)
    async def additem(self, ctx, name: str, price: int, *, description: str):
        """Add an item to the shop (admin only)"""
        if price <= 0:
            return await ctx.send("Price must be positive.")
        
        if "items" not in self.shop_items:
            self.shop_items["items"] = {}
        
        # Generate a new item ID
        item_id = str(len(self.shop_items["items"]) + 1)
        
        # Add the item to the shop
        self.shop_items["items"][item_id] = {
            "name": name,
            "description": description,
            "price": price,
            "type": "item"
        }
        
        self.save_shop_items()
        
        await ctx.send(f"Added {name} to the shop for {price} coins.")
    
    @shop.command()
    @commands.has_permissions(administrator=True)
    async def removeitem(self, ctx, item_id: str):
        """Remove an item from the shop (admin only)"""
        if "items" not in self.shop_items:
            return await ctx.send("No items in the shop.")
        
        if item_id not in self.shop_items["items"]:
            return await ctx.send(f"No item with ID {item_id} in the shop.")
        
        item_name = self.shop_items["items"][item_id]["name"]
        
        del self.shop_items["items"][item_id]
        self.save_shop_items()
        
        await ctx.send(f"Removed {item_name} from the shop.")
    
    @commands.command()
    async def buy(self, ctx, item_id: str):
        """Buy an item from the shop"""
        # Check if it's a role
        guild_id = str(ctx.guild.id)
        
        if "roles" in self.shop_items and guild_id in self.shop_items["roles"] and item_id in self.shop_items["roles"][guild_id]:
            # It's a role
            item = self.shop_items["roles"][guild_id][item_id]
            price = item["price"]
            role_id = item["role_id"]
            
            # Check if user has enough coins
            balance = await get_user_balance(ctx.author.id)
            
            if balance < price:
                return await ctx.send(f"You don't have enough coins. You need {price} coins, but you only have {balance}.")
            
            # Get the role
            role = ctx.guild.get_role(int(role_id))
            if not role:
                return await ctx.send("That role no longer exists.")
            
            # Check if user already has the role
            if role in ctx.author.roles:
                return await ctx.send(f"You already have the {role.name} role.")
            
            # Deduct coins
            await update_user_balance(ctx.author.id, -price)
            
            # Add role
            try:
                await ctx.author.add_roles(role)
                await ctx.send(f"You purchased the {role.mention} role for {price} coins!")
            except Exception as e:
                # Refund if role couldn't be added
                await update_user_balance(ctx.author.id, price)
                await ctx.send(f"Error adding role: {e}")
        
        # Check if it's an item
        elif "items" in self.shop_items and item_id in self.shop_items["items"]:
            # It's an item
            item = self.shop_items["items"][item_id]
            price = item["price"]
            
            # Check if user has enough coins
            balance = await get_user_balance(ctx.author.id)
            
            if balance < price:
                return await ctx.send(f"You don't have enough coins. You need {price} coins, but you only have {balance}.")
            
            # Deduct coins
            await update_user_balance(ctx.author.id, -price)
            
            # Handle item purchase
            await ctx.send(f"You purchased {item['name']} for {price} coins!")
            
            # Additional handling based on item type
            if item["type"] == "status":
                await ctx.send(f"{ctx.author.mention} now has {item['name']}!")
            elif item["type"] == "command":
                await ctx.send(f"Please use `!customcommand create <name> <response>` to set up your custom command.")
        
        else:
            await ctx.send("Invalid item ID. Use `!shop` to see available items.")
    
    @commands.command()
    async def customcommand(self, ctx, action=None, name=None, *, response=None):
        """Create, edit, or delete a custom command"""
        if not action:
            return await ctx.send("Please specify an action: `create`, `edit`, or `delete`.")
        
        if action.lower() not in ["create", "edit", "delete"]:
            return await ctx.send("Invalid action. Please use `create`, `edit`, or `delete`.")
        
        if not name:
            return await ctx.send("Please specify a command name.")
        
        # Check if user has the custom command item
        user_items = await self.get_user_items(ctx.author.id)
        has_custom_command = False
        
        for item in user_items:
            if item["type"] == "command":
                has_custom_command = True
                break
        
        if not has_custom_command:
            return await ctx.send("You need to purchase a Custom Command from the shop first.")
        
        # Handle command creation
        if action.lower() == "create":
            if not response:
                return await ctx.send("Please specify a response for your command.")
            
            # Check if command already exists
            custom_commands = await self.get_custom_commands()
            
            if name.lower() in custom_commands:
                return await ctx.send(f"A command with the name `{name}` already exists.")
            
            # Add the command
            await self.add_custom_command(ctx.author.id, name.lower(), response)
            
            await ctx.send(f"Custom command `!{name}` created successfully!")
        
        # Handle command editing
        elif action.lower() == "edit":
            if not response:
                return await ctx.send("Please specify a new response for your command.")
            
            # Check if command exists and belongs to the user
            custom_commands = await self.get_custom_commands()
            
            if name.lower() not in custom_commands:
                return await ctx.send(f"No command with the name `{name}` exists.")
            
            if custom_commands[name.lower()]["owner_id"] != ctx.author.id:
                return await ctx.send("You can only edit your own custom commands.")
            
            # Update the command
            await self.edit_custom_command(name.lower(), response)
            
            await ctx.send(f"Custom command `!{name}` updated successfully!")
        
        # Handle command deletion
        elif action.lower() == "delete":
            # Check if command exists and belongs to the user
            custom_commands = await self.get_custom_commands()
            
            if name.lower() not in custom_commands:
                return await ctx.send(f"No command with the name `{name}` exists.")
            
            if custom_commands[name.lower()]["owner_id"] != ctx.author.id:
                return await ctx.send("You can only delete your own custom commands.")
            
            # Delete the command
            await self.delete_custom_command(name.lower())
            
            await ctx.send(f"Custom command `!{name}` deleted successfully!")
    
    async def get_user_items(self, user_id):
        """Get items owned by a user"""
        # This is a placeholder - implement actual database query
        # For now, we'll assume the user has the item if they've purchased it
        return [{"type": "command", "name": "Custom Command"}]
    
    async def get_custom_commands(self):
        """Get all custom commands"""
        try:
            # Intentar obtener comandos de la base de datos
            try:
                response = self.bot.supabase.table('custom_commands').select('*').execute()
                
                commands = {}
                for command in response.data:
                    commands[command['name']] = {
                        "response": command['response'],
                        "owner_id": command['owner_id']
                    }
                
                return commands
            except Exception as db_error:
                # Si hay error con la base de datos, usar archivo JSON local
                import json
                import os
                
                # Crear directorio config si no existe
                os.makedirs('config', exist_ok=True)
                
                # Ruta al archivo JSON
                file_path = 'config/custom_commands.json'
                
                # Verificar si el archivo existe
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r') as f:
                            return json.load(f)
                    except Exception as json_error:
                        print(f"Error loading custom commands from JSON: {json_error}")
                        return {}
                else:
                    # Crear archivo vacío
                    with open(file_path, 'w') as f:
                        json.dump({}, f)
                    return {}
        except Exception as e:
            print(f"Error getting custom commands: {e}")
            return {}
    
    async def add_custom_command(self, owner_id, name, response):
        """Add a custom command to the database"""
        try:
            # Intentar añadir a la base de datos
            try:
                command_data = {
                    'owner_id': owner_id,
                    'name': name,
                    'response': response
                }
                
                self.bot.supabase.table('custom_commands').insert(command_data).execute()
                return True
            except Exception as db_error:
                # Si hay error con la base de datos, usar archivo JSON local
                import json
                import os
                
                # Ruta al archivo JSON
                file_path = 'config/custom_commands.json'
                
                # Cargar comandos existentes
                commands = {}
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        commands = json.load(f)
                
                # Añadir nuevo comando
                commands[name] = {
                    "response": response,
                    "owner_id": owner_id
                }
                
                # Guardar comandos
                with open(file_path, 'w') as f:
                    json.dump(commands, f, indent=4)
                
                return True
        except Exception as e:
            print(f"Error adding custom command: {e}")
            return False
    
    async def edit_custom_command(self, name, response):
        """Edit an existing custom command"""
        try:
            # Intentar editar en la base de datos
            try:
                self.bot.supabase.table('custom_commands').update({'response': response}).eq('name', name).execute()
                return True
            except Exception as db_error:
                # Si hay error con la base de datos, usar archivo JSON local
                import json
                import os
                
                # Ruta al archivo JSON
                file_path = 'config/custom_commands.json'
                
                # Cargar comandos existentes
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        commands = json.load(f)
                    
                    # Actualizar comando
                    if name in commands:
                        commands[name]["response"] = response
                        
                        # Guardar comandos
                        with open(file_path, 'w') as f:
                            json.dump(commands, f, indent=4)
                        
                        return True
                
                return False
        except Exception as e:
            print(f"Error editing custom command: {e}")
            return False
    
    async def delete_custom_command(self, name):
        """Delete a custom command"""
        try:
            # Intentar eliminar de la base de datos
            try:
                self.bot.supabase.table('custom_commands').delete().eq('name', name).execute()
                return True
            except Exception as db_error:
                # Si hay error con la base de datos, usar archivo JSON local
                import json
                import os
                
                # Ruta al archivo JSON
                file_path = 'config/custom_commands.json'
                
                # Cargar comandos existentes
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        commands = json.load(f)
                    
                    # Eliminar comando
                    if name in commands:
                        del commands[name]
                        
                        # Guardar comandos
                        with open(file_path, 'w') as f:
                            json.dump(commands, f, indent=4)
                        
                        return True
                
                return False
        except Exception as e:
            print(f"Error deleting custom command: {e}")
            return False
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for custom commands"""
        if message.author.bot:
            return
        
        if not message.content.startswith('!'):
            return
        
        # Extract command name
        command_name = message.content[1:].split(' ')[0].lower()
        
        # Check if it's a custom command
        custom_commands = await self.get_custom_commands()
        
        if command_name in custom_commands:
            await message.channel.send(custom_commands[command_name]["response"])
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def addcoins(self, ctx, member: discord.Member, amount: int):
        """Add coins to a user (admin only)"""
        if amount <= 0:
            return await ctx.send("Amount must be positive.")
        
        # Update balance
        await update_user_balance(member.id, amount)
        
        await ctx.send(f"Added {amount} coins to {member.mention}.")
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def removecoins(self, ctx, member: discord.Member, amount: int):
        """Remove coins from a user (admin only)"""
        if amount <= 0:
            return await ctx.send("Amount must be positive.")
        
        # Get current balance
        balance = await get_user_balance(member.id)
        
        # Make sure we don't go negative
        amount = min(amount, balance)
        
        # Update balance
        await update_user_balance(member.id, -amount)
        
        await ctx.send(f"Removed {amount} coins from {member.mention}.")
    
    @commands.command(aliases=["eltop", "moneytop"])
    async def economy_leaderboard(self, ctx, page: int = 1):
        """Show the server's economy leaderboard"""
        try:
            # Get all users from the database
            response = self.bot.supabase.table('economy').select('*').order('balance', desc=True).execute()
            
            if not response.data:
                return await ctx.send("No users found in the economy leaderboard.")
            
            # Filter users to those in this server
            guild_members = {member.id: member for member in ctx.guild.members}
            leaderboard_data = []
            
            for user_data in response.data:
                if user_data['user_id'] in guild_members:
                    leaderboard_data.append({
                        'member': guild_members[user_data['user_id']],
                        'balance': user_data['balance']
                    })
            
            if not leaderboard_data:
                return await ctx.send("No users found in the economy leaderboard for this server.")
            
            # Paginate results
            items_per_page = 10
            pages = (len(leaderboard_data) - 1) // items_per_page + 1
            
            if page < 1 or page > pages:
                return await ctx.send(f"Invalid page. Please specify a page between 1 and {pages}.")
            
            start_idx = (page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, len(leaderboard_data))
            
            embed = discord.Embed(
                title=f"{ctx.guild.name} Economy Leaderboard",
                description=f"Page {page}/{pages}",
                color=discord.Color.gold()
            )
            
            for i, data in enumerate(leaderboard_data[start_idx:end_idx], start=start_idx + 1):
                member = data['member']
                balance = data['balance']
                
                # Add medal emoji for top 3
                medal = ""
                if i == 1:
                    medal = "🥇 "
                elif i == 2:
                    medal = "🥈 "
                elif i == 3:
                    medal = "🥉 "
                
                embed.add_field(
                    name=f"{medal}#{i}: {member.display_name}",
                    value=f"💰 {balance:,} coins",
                    inline=False
                )
            
            embed.set_footer(text=f"Use !economy_leaderboard {page-1} or !economy_leaderboard {page+1} to navigate pages")
            
            await ctx.send(embed=embed)
        
        except Exception as e:
            print(f"Error fetching economy leaderboard: {e}")
            await ctx.send("An error occurred while fetching the leaderboard.")

async def setup(bot):
    await bot.add_cog(Economy(bot))
