import os
import asyncio
from supabase import create_client, Client
from dotenv import load_dotenv
import datetime
import discord

# Load environment variables
load_dotenv()

# Supabase configuration
url = os.getenv("URL_SUPABASE")
key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

async def create_tables():
    """Create all necessary tables in the database if they don't exist"""
    # These tables are already created in Supabase as mentioned in the requirements
    # This function is a placeholder for any additional setup or validation
    try:
        # Check if we can connect to the database
        response = supabase.table('users').select('id').limit(1).execute()
        print("Database connection successful!")
    except Exception as e:
        print(f"Error connecting to database: {e}")

async def get_user(discord_id):
    """Get a user from the database by Discord ID"""
    try:
        response = supabase.table('users').select('*').eq('discord_id', discord_id).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"Error getting user: {e}")
        return None

async def create_user(discord_id, username, discriminator):
    """Create a new user in the database"""
    try:
        user_data = {
            'discord_id': discord_id,
            'username': username,
            'discriminator': discriminator
        }
        response = supabase.table('users').insert(user_data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error creating user: {e}")
        return None

async def update_user_xp(discord_id, xp_amount):
    """Update a user's XP and check for level up"""
    try:
        # Get current user data
        user = await get_user(discord_id)
        
        # If user doesn't exist, create them
        if not user:
            user = await create_user(discord_id, f"User_{discord_id}", "0000")
            if not user:
                return None
        
        # Calculate current XP and level
        current_xp = user.get('xp', 0) + xp_amount
        current_level = user.get('level', 1)
        
        # Check if user should level up
        # Formula: 100 * level^2 XP needed for next level
        xp_needed = 100 * (current_level ** 2)
        
        # Level up if enough XP
        level_up = False
        while current_xp >= xp_needed:
            current_level += 1
            current_xp -= xp_needed
            xp_needed = 100 * (current_level ** 2)
            level_up = True
        
        # Update user data
        update_data = {
            'xp': current_xp,
            'level': current_level,
            'last_active': 'now()'
        }
        
        response = supabase.table('users').update(update_data).eq('discord_id', discord_id).execute()
        
        # Return updated user data with level_up flag
        if response.data:
            updated_user = response.data[0]
            updated_user['level_up'] = level_up
            return updated_user
        return None
    except Exception as e:
        print(f"Error updating user XP: {e}")
        return None

async def record_message(discord_id, content):
    """Record a message in the database"""
    try:
        # First check if user exists
        user = await get_user(discord_id)
        
        # If user doesn't exist, create them
        if not user:
            await create_user(discord_id, f"User_{discord_id}", "0000")
        
        # Record the message
        message_data = {
            'user_id': discord_id,
            'content': content[:500]  # Limit content length to 500 chars
        }
        
        response = supabase.table('messages').insert(message_data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error recording message: {e}")
        return None

async def add_achievement(discord_id, achievement_name):
    """Add an achievement for a user"""
    try:
        # First check if user exists
        user = await get_user(discord_id)
        
        # If user doesn't exist, create them
        if not user:
            await create_user(discord_id, f"User_{discord_id}", "0000")
        
        # Check if achievement already exists for this user
        response = supabase.table('achievements').select('*').eq('user_id', discord_id).eq('achievement_name', achievement_name).execute()
        
        # Only add if the user doesn't already have this achievement
        if not response.data:
            achievement_data = {
                'user_id': discord_id,
                'achievement_name': achievement_name
            }
            
            response = supabase.table('achievements').insert(achievement_data).execute()
            return response.data[0] if response.data else None
        else:
            return response.data[0]
    except Exception as e:
        print(f"Error adding achievement: {e}")
        return None

async def get_user_achievements(discord_id):
    """Get all achievements for a user"""
    try:
        response = supabase.table('achievements').select('*').eq('user_id', discord_id).execute()
        return response.data
    except Exception as e:
        print(f"Error getting user achievements: {e}")
        return []

async def add_role(role_name, description, permissions=None):
    """Add a role to the database"""
    try:
        # Check if role already exists
        response = supabase.table('roles').select('*').eq('role_name', role_name).execute()
        
        if not response.data:
            role_data = {
                'role_name': role_name,
                'description': description,
                'permissions': permissions or []
            }
            
            response = supabase.table('roles').insert(role_data).execute()
            return response.data[0] if response.data else None
        else:
            return response.data[0]
    except Exception as e:
        print(f"Error adding role: {e}")
        return None

async def get_roles():
    """Get all roles from the database"""
    try:
        response = supabase.table('roles').select('*').execute()
        return response.data
    except Exception as e:
        print(f"Error getting roles: {e}")
        return []

async def get_user_balance(discord_id):
    """Get a user's economy balance"""
    try:
        response = supabase.table('economy').select('balance').eq('user_id', discord_id).execute()
        if response.data:
            return response.data[0]['balance']
        return 0
    except Exception as e:
        print(f"Error getting user balance: {e}")
        return 0

async def update_user_balance(discord_id, amount_to_add):
    """Update a user's economy balance"""
    try:
        # Check if user has an economy record
        response = supabase.table('economy').select('*').eq('user_id', discord_id).execute()
        
        if response.data:
            # Update existing record
            current_balance = response.data[0]['balance']
            new_balance = current_balance + amount_to_add
            response = supabase.table('economy').update({'balance': new_balance}).eq('user_id', discord_id).execute()
        else:
            # Create new record
            response = supabase.table('economy').insert({'user_id': discord_id, 'balance': amount_to_add}).execute()
        
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error updating user balance: {e}")
        return None

async def add_punishment(discord_id, punishment_type, reason, duration=None):
    """Add a punishment record for a user"""
    try:
        # Primero verificamos si el usuario existe
        user = await get_user(discord_id)
        
        # Si el usuario no existe, lo creamos primero
        if not user:
            # Creamos un usuario con valores predeterminados ya que no tenemos el nombre de usuario real
            await create_user(discord_id, f"User_{discord_id}", "0000")
        
        # Convertir la duración a un formato de timestamp si es un número
        if duration is not None and isinstance(duration, (int, float)):
            # Convertir segundos a un formato de timestamp ISO
            duration_timestamp = (discord.utils.utcnow() + datetime.timedelta(seconds=duration)).isoformat()
        else:
            duration_timestamp = duration
        
        punishment_data = {
            'user_id': discord_id,
            'punishment_type': punishment_type,
            'reason': reason,
            'duration': duration_timestamp
        }
        response = supabase.table('punishments').insert(punishment_data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error adding punishment: {e}")
        return None

async def get_user_punishments(discord_id):
    """Get all punishments for a user"""
    try:
        response = supabase.table('punishments').select('*').eq('user_id', discord_id).execute()
        return response.data
    except Exception as e:
        print(f"Error getting user punishments: {e}")
        return []
