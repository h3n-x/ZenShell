import discord
from discord.ext import commands

class DatabaseTest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    async def dbtest(self, ctx):
        """Test the database connection"""
        try:
            # Try to query the database
            response = self.bot.supabase.table('economy').select('*').limit(5).execute()
            
            # Create an embed with the results
            embed = discord.Embed(
                title="Database Connection Test",
                description="Successfully connected to Supabase!",
                color=discord.Color.green()
            )
            
            # Add some stats
            embed.add_field(
                name="Economy Records", 
                value=f"Found {len(response.data)} records (showing max 5)",
                inline=False
            )
            
            # Show some sample data if available
            if response.data:
                for i, record in enumerate(response.data[:5]):
                    embed.add_field(
                        name=f"Record {i+1}",
                        value=f"User ID: {record.get('user_id')}\nBalance: {record.get('balance')}",
                        inline=True
                    )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            # If there's an error, show it
            embed = discord.Embed(
                title="Database Connection Error",
                description=f"Failed to connect to the database: ```{str(e)}```",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(DatabaseTest(bot))
