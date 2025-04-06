import discord
from discord.ext import commands
import random
import asyncio
import datetime
from PIL import Image, ImageDraw, ImageFont
import io
import os
from utils.database import get_user, create_user, update_user_xp, add_achievement

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.xp_cooldown = commands.CooldownMapping.from_cooldown(1, 60, commands.BucketType.user)
        self.level_roles = {}
        self.load_level_roles()
    
    def load_level_roles(self):
        """Load level roles from config file"""
        config_path = 'config/level_roles.json'
        if os.path.exists(config_path):
            try:
                import json
                with open(config_path, 'r') as f:
                    self.level_roles = json.load(f)
            except Exception as e:
                print(f"Error loading level roles config: {e}")
    
    def save_level_roles(self):
        """Save level roles to config file"""
        config_path = 'config/level_roles.json'
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        try:
            import json
            with open(config_path, 'w') as f:
                json.dump(self.level_roles, f, indent=4)
        except Exception as e:
            print(f"Error saving level roles config: {e}")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Award XP for messages"""
        # Ignore bot messages and commands
        if message.author.bot or message.content.startswith(self.bot.command_prefix):
            return
        
        # Check cooldown
        bucket = self.xp_cooldown.get_bucket(message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            return
        
        # Award XP
        xp_to_add = random.randint(15, 25)
        
        # Get or create user
        user = await get_user(message.author.id)
        if not user:
            await create_user(
                message.author.id,
                message.author.name,
                message.author.discriminator
            )
        
        # Update user XP
        updated_user = await update_user_xp(message.author.id, xp_to_add)
        
        # Check if user leveled up
        if updated_user and user and updated_user['level'] > user['level']:
            # Send level up message
            embed = discord.Embed(
                title="Level Up!",
                description=f"🎉 Congratulations {message.author.mention}! You've reached level **{updated_user['level']}**!",
                color=discord.Color.green()
            )
            await message.channel.send(embed=embed)
            
            # Check if there's a role reward for this level
            guild_id = str(message.guild.id)
            if guild_id in self.level_roles:
                level_str = str(updated_user['level'])
                if level_str in self.level_roles[guild_id]:
                    role_id = self.level_roles[guild_id][level_str]
                    role = message.guild.get_role(int(role_id))
                    if role:
                        try:
                            await message.author.add_roles(role)
                            await message.channel.send(f"You've been awarded the {role.mention} role!")
                        except Exception as e:
                            print(f"Error adding role: {e}")
            
            # Check for achievements
            if updated_user['level'] == 5:
                await add_achievement(message.author.id, "Reached Level 5")
            elif updated_user['level'] == 10:
                await add_achievement(message.author.id, "Reached Level 10")
            elif updated_user['level'] == 25:
                await add_achievement(message.author.id, "Reached Level 25")
            elif updated_user['level'] == 50:
                await add_achievement(message.author.id, "Reached Level 50")
            elif updated_user['level'] == 100:
                await add_achievement(message.author.id, "Reached Level 100")
    
    @commands.command()
    async def rank(self, ctx, member: discord.Member = None):
        """Show your or another user's rank"""
        member = member or ctx.author
        
        # Get user data
        user = await get_user(member.id)
        if not user:
            return await ctx.send(f"{member.display_name} hasn't earned any XP yet.")
        
        # Calculate progress to next level
        current_level = user['level']
        current_xp = user['xp']
        
        # XP needed for next level: level * 100
        xp_needed = (current_level + 1) * 100
        
        # XP needed for current level
        xp_current_level = current_level * 100
        
        # XP progress towards next level
        xp_progress = current_xp - xp_current_level
        
        # Percentage progress
        progress_percentage = min(100, int((xp_progress / (xp_needed - xp_current_level)) * 100))
        
        # Create rank card
        try:
            # Create image
            width, height = 800, 250
            image = Image.new("RGBA", (width, height), (44, 47, 51, 255))
            draw = ImageDraw.Draw(image)
            
            # Load fonts (using default if custom fonts not available)
            try:
                username_font = ImageFont.truetype("arial.ttf", 36)
                level_font = ImageFont.truetype("arial.ttf", 30)
                xp_font = ImageFont.truetype("arial.ttf", 24)
            except:
                username_font = ImageFont.load_default()
                level_font = ImageFont.load_default()
                xp_font = ImageFont.load_default()
            
            # Draw user avatar
            try:
                avatar_size = 180
                avatar_bytes = await member.display_avatar.read()
                avatar = Image.open(io.BytesIO(avatar_bytes)).resize((avatar_size, avatar_size))
                
                # Create circular mask
                mask = Image.new("L", (avatar_size, avatar_size), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
                
                # Apply mask to avatar
                avatar_circle = Image.new("RGBA", (avatar_size, avatar_size))
                avatar_circle.paste(avatar, (0, 0), mask)
                
                # Paste avatar onto rank card
                image.paste(avatar_circle, (30, 35), avatar_circle)
            except Exception as e:
                print(f"Error processing avatar: {e}")
            
            # Draw username
            draw.text((240, 50), member.display_name, font=username_font, fill=(255, 255, 255, 255))
            
            # Draw level
            draw.text((240, 100), f"Level: {current_level}", font=level_font, fill=(255, 255, 255, 255))
            
            # Draw XP
            draw.text((240, 140), f"XP: {xp_progress}/{xp_needed - xp_current_level}", font=xp_font, fill=(255, 255, 255, 255))
            
            # Draw progress bar background
            bar_width = 500
            bar_height = 30
            bar_x = 240
            bar_y = 180
            draw.rectangle([(bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height)], fill=(80, 80, 80, 255))
            
            # Draw progress bar
            progress_width = int(bar_width * (progress_percentage / 100))
            draw.rectangle([(bar_x, bar_y), (bar_x + progress_width, bar_y + bar_height)], fill=(114, 137, 218, 255))
            
            # Draw progress percentage
            draw.text((bar_x + bar_width / 2 - 20, bar_y + 5), f"{progress_percentage}%", font=xp_font, fill=(255, 255, 255, 255))
            
            # Save image to buffer
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            buffer.seek(0)
            
            # Send image
            await ctx.send(file=discord.File(buffer, filename="rank.png"))
        
        except Exception as e:
            print(f"Error creating rank card: {e}")
            
            # Fallback to text-based rank
            embed = discord.Embed(
                title=f"{member.display_name}'s Rank",
                color=member.color
            )
            embed.add_field(name="Level", value=str(current_level), inline=True)
            embed.add_field(name="XP", value=f"{current_xp} XP", inline=True)
            embed.add_field(name="Progress to Next Level", value=f"{progress_percentage}%", inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            
            await ctx.send(embed=embed)
    
    @commands.command(name="level_leaderboard", aliases=["level_top", "xp_ranking"])
    async def level_leaderboard(self, ctx, page: int = 1):
        """Muestra el ranking de niveles de los usuarios
        
        Args:
            page: Número de página a mostrar (10 usuarios por página)
        
        Ejemplos:
            !level_leaderboard
            !level_leaderboard 2
        """
        try:
            # Get all users from the database
            response = self.bot.supabase.table('users').select('*').order('xp', desc=True).execute()
            
            if not response.data:
                return await ctx.send("No users found in the leaderboard.")
            
            # Filter users to those in this server
            guild_members = {member.id: member for member in ctx.guild.members}
            leaderboard_data = []
            
            for user_data in response.data:
                if user_data['discord_id'] in guild_members:
                    leaderboard_data.append({
                        'member': guild_members[user_data['discord_id']],
                        'xp': user_data['xp'],
                        'level': user_data['level']
                    })
            
            if not leaderboard_data:
                return await ctx.send("No users found in the leaderboard for this server.")
            
            # Paginate results
            items_per_page = 10
            pages = (len(leaderboard_data) - 1) // items_per_page + 1
            
            if page < 1 or page > pages:
                return await ctx.send(f"Invalid page. Please specify a page between 1 and {pages}.")
            
            start_idx = (page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, len(leaderboard_data))
            
            embed = discord.Embed(
                title=f"{ctx.guild.name} Leaderboard",
                description=f"Page {page}/{pages}",
                color=discord.Color.gold()
            )
            
            for i, data in enumerate(leaderboard_data[start_idx:end_idx], start=start_idx + 1):
                member = data['member']
                xp = data['xp']
                level = data['level']
                
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
                    value=f"Level: {level} | XP: {xp}",
                    inline=False
                )
            
            embed.set_footer(text=f"Use !level_leaderboard {page-1} or !level_leaderboard {page+1} to navigate pages")
            
            await ctx.send(embed=embed)
        
        except Exception as e:
            print(f"Error fetching leaderboard: {e}")
            await ctx.send("An error occurred while fetching the leaderboard.")
    
    @commands.group(invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def levelrole(self, ctx):
        """Manage level roles"""
        await ctx.send_help(ctx.command)
    
    @levelrole.command()
    @commands.has_permissions(administrator=True)
    async def add(self, ctx, level: int, role: discord.Role):
        """Add a role reward for a specific level"""
        if level < 1:
            return await ctx.send("Level must be at least 1.")
        
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.level_roles:
            self.level_roles[guild_id] = {}
        
        self.level_roles[guild_id][str(level)] = str(role.id)
        self.save_level_roles()
        
        await ctx.send(f"Role {role.mention} will now be awarded at level {level}.")
    
    @levelrole.command()
    @commands.has_permissions(administrator=True)
    async def remove(self, ctx, level: int):
        """Remove a role reward for a specific level"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.level_roles:
            return await ctx.send("No level roles configured for this server.")
        
        if str(level) not in self.level_roles[guild_id]:
            return await ctx.send(f"No role configured for level {level}.")
        
        role_id = self.level_roles[guild_id].pop(str(level))
        self.save_level_roles()
        
        role = ctx.guild.get_role(int(role_id))
        role_mention = role.mention if role else f"role with ID {role_id}"
        
        await ctx.send(f"Removed {role_mention} from level {level} rewards.")
    
    @levelrole.command()
    @commands.has_permissions(administrator=True)
    async def list(self, ctx):
        """List all level role rewards"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.level_roles or not self.level_roles[guild_id]:
            return await ctx.send("No level roles configured for this server.")
        
        embed = discord.Embed(
            title="Level Role Rewards",
            description="Roles awarded for reaching specific levels",
            color=discord.Color.blue()
        )
        
        # Sort by level
        sorted_levels = sorted(self.level_roles[guild_id].items(), key=lambda x: int(x[0]))
        
        for level, role_id in sorted_levels:
            role = ctx.guild.get_role(int(role_id))
            role_mention = role.mention if role else f"Unknown role ({role_id})"
            
            embed.add_field(name=f"Level {level}", value=role_mention, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def givexp(self, ctx, member: discord.Member, amount: int):
        """Give XP to a user (admin only)"""
        if amount <= 0:
            return await ctx.send("Amount must be positive.")
        
        # Get or create user
        user = await get_user(member.id)
        if not user:
            await create_user(
                member.id,
                member.name,
                member.discriminator
            )
        
        # Update user XP
        updated_user = await update_user_xp(member.id, amount)
        
        if updated_user:
            await ctx.send(f"Added {amount} XP to {member.mention}. They are now level {updated_user['level']} with {updated_user['xp']} XP.")
        else:
            await ctx.send(f"Failed to add XP to {member.mention}.")

async def setup(bot):
    await bot.add_cog(Leveling(bot))
