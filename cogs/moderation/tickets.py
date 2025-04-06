import discord
from discord.ext import commands
import asyncio
import json
import os
import datetime

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        # Get the ticket system cog
        ticket_cog = interaction.client.get_cog("Tickets")
        if not ticket_cog:
            return await interaction.followup.send("Ticket system is not available right now.", ephemeral=True)
        
        # Create the ticket
        await ticket_cog.create_ticket(interaction)

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        # Get the ticket system cog
        ticket_cog = interaction.client.get_cog("Tickets")
        if not ticket_cog:
            return await interaction.followup.send("Ticket system is not available right now.", ephemeral=True)
        
        # Close the ticket
        await ticket_cog.close_ticket(interaction)

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tickets_config = {}
        self.load_config()
        
        # Register persistent views
        bot.add_view(TicketView())
        bot.add_view(TicketCloseView())
    
    def load_config(self):
        """Load ticket configuration from file"""
        config_path = 'config/tickets.json'
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    self.tickets_config = json.load(f)
            except Exception as e:
                print(f"Error loading tickets config: {e}")
    
    def save_config(self):
        """Save ticket configuration to file"""
        config_path = 'config/tickets.json'
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        try:
            with open(config_path, 'w') as f:
                json.dump(self.tickets_config, f, indent=4)
        except Exception as e:
            print(f"Error saving tickets config: {e}")
    
    @commands.group(invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def tickets(self, ctx):
        """Manage the ticket system"""
        await ctx.send_help(ctx.command)
    
    @tickets.command()
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx, category: discord.CategoryChannel = None, support_role: discord.Role = None):
        """Set up the ticket system"""
        guild_id = str(ctx.guild.id)
        
        # Create category if not provided
        if not category:
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                ctx.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }
            
            if support_role:
                overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            
            category = await ctx.guild.create_category("Support Tickets", overwrites=overwrites)
            await ctx.send(f"Created ticket category: {category.name}")
        
        # Update configuration
        if guild_id not in self.tickets_config:
            self.tickets_config[guild_id] = {}
        
        self.tickets_config[guild_id]["category_id"] = category.id
        
        if support_role:
            self.tickets_config[guild_id]["support_role_id"] = support_role.id
        
        self.save_config()
        
        # Create ticket panel
        embed = discord.Embed(
            title="Support Tickets",
            description="Click the button below to create a support ticket.",
            color=discord.Color.blue()
        )
        
        view = TicketView()
        await ctx.send(embed=embed, view=view)
        
        await ctx.send("Ticket system has been set up successfully!")
    
    @tickets.command()
    @commands.has_permissions(administrator=True)
    async def panel(self, ctx, channel: discord.TextChannel = None):
        """Create a ticket panel in the specified channel"""
        channel = channel or ctx.channel
        
        embed = discord.Embed(
            title="Support Tickets",
            description="Click the button below to create a support ticket.",
            color=discord.Color.blue()
        )
        
        view = TicketView()
        await channel.send(embed=embed, view=view)
        
        await ctx.send(f"Ticket panel created in {channel.mention}")
    
    async def create_ticket(self, interaction: discord.Interaction):
        """Create a new ticket"""
        guild_id = str(interaction.guild.id)
        user = interaction.user
        
        # Check if configuration exists
        if guild_id not in self.tickets_config:
            return await interaction.followup.send("Ticket system is not set up for this server.", ephemeral=True)
        
        # Get category
        category_id = self.tickets_config[guild_id].get("category_id")
        if not category_id:
            return await interaction.followup.send("Ticket category is not configured.", ephemeral=True)
        
        category = interaction.guild.get_channel(category_id)
        if not category:
            return await interaction.followup.send("Ticket category not found.", ephemeral=True)
        
        # Check if user already has an open ticket
        for channel in category.channels:
            if channel.name.lower() == f"ticket-{user.name.lower()}-{user.discriminator}":
                return await interaction.followup.send(f"You already have an open ticket: {channel.mention}", ephemeral=True)
        
        # Create permissions
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # Add support role if configured
        support_role_id = self.tickets_config[guild_id].get("support_role_id")
        if support_role_id:
            support_role = interaction.guild.get_role(support_role_id)
            if support_role:
                overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        # Create ticket channel
        channel_name = f"ticket-{user.name.lower()}-{user.discriminator}"
        channel = await category.create_text_channel(channel_name, overwrites=overwrites)
        
        # Send welcome message
        embed = discord.Embed(
            title="Support Ticket",
            description=f"Welcome {user.mention}! Please describe your issue and a staff member will assist you shortly.",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now()
        )
        
        view = TicketCloseView()
        await channel.send(embed=embed, view=view)
        
        # Mention support role if configured
        if support_role_id:
            support_role = interaction.guild.get_role(support_role_id)
            if support_role:
                await channel.send(f"{support_role.mention} A new ticket has been created.")
        
        await interaction.followup.send(f"Your ticket has been created: {channel.mention}", ephemeral=True)
    
    async def close_ticket(self, interaction: discord.Interaction):
        """Close a ticket"""
        channel = interaction.channel
        
        # Check if this is a ticket channel
        if not channel.name.startswith("ticket-"):
            return await interaction.followup.send("This is not a ticket channel.", ephemeral=True)
        
        # Confirm closure
        embed = discord.Embed(
            title="Close Ticket",
            description="Are you sure you want to close this ticket? This will delete the channel.",
            color=discord.Color.red()
        )
        
        class ConfirmView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.confirmed = False
            
            @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
            async def confirm(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                self.confirmed = True
                self.stop()
                await button_interaction.response.defer()
            
            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
            async def cancel(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                self.stop()
                await button_interaction.response.defer()
        
        view = ConfirmView()
        message = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
        # Wait for confirmation
        await view.wait()
        
        if view.confirmed:
            # Send closure message
            embed = discord.Embed(
                title="Ticket Closed",
                description=f"This ticket has been closed by {interaction.user.mention}.",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now()
            )
            
            await channel.send(embed=embed)
            
            # Wait a moment before deleting
            await asyncio.sleep(5)
            
            try:
                await channel.delete(reason=f"Ticket closed by {interaction.user}")
            except Exception as e:
                await interaction.followup.send(f"Error deleting channel: {e}", ephemeral=True)
        else:
            await interaction.followup.send("Ticket closure cancelled.", ephemeral=True)
    
    @tickets.command()
    @commands.has_permissions(administrator=True)
    async def close(self, ctx):
        """Close a ticket (admin command)"""
        if not ctx.channel.name.startswith("ticket-"):
            return await ctx.send("This is not a ticket channel.")
        
        # Send closure message
        embed = discord.Embed(
            title="Ticket Closed",
            description=f"This ticket has been closed by {ctx.author.mention}.",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        
        await ctx.send(embed=embed)
        
        # Wait a moment before deleting
        await asyncio.sleep(5)
        
        try:
            await ctx.channel.delete(reason=f"Ticket closed by {ctx.author}")
        except Exception as e:
            await ctx.send(f"Error deleting channel: {e}")

async def setup(bot):
    await bot.add_cog(Tickets(bot))
