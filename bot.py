import os
import discord
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('DISCORD_GUILD_ID')

intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

ROLES = [
    ('👑 Owner', discord.Colour.gold()),
    ('💻 Developer', discord.Colour.blue()),
    ('🛡️ Administrator', discord.Colour.red()),
    ('🔨 Moderator', discord.Colour.orange()),
    ('🎨 Designer', discord.Colour.purple()),
    ('📹 Content Creator', discord.Colour.magenta()),
    ('🏆 Tournament Host', discord.Colour.gold()),
    ('📋 Team Manager', discord.Colour.teal()),
    ('⚽ Competitive Player', discord.Colour.green()),
    ('💎 VIP', discord.Colour.blurple()),
    ('👤 Player', discord.Colour.light_grey()),
]

CATEGORIES = [
    ('📌 INFORMATION', ['👋・welcome', '📜・rules', '📢・announcements', '📰・updates', '🎁・codes', '🔗・links']),
    ('💬 COMMUNITY', ['💬・general', '🇲🇽・español', '🌎・english', '📸・media', '🎨・fan-art', '🤖・bot-commands']),
    ('⚽ LOCKED GAME', ['🎮・game-discussion', '⚔️・weapons', '🧬・traits', '🔥・flows', '💡・suggestions', '🐛・bug-reports', '🎥・clips']),
    ('🏆 COMPETITIVE', ['📋・comp-rules', '📝・team-registration', '🔎・looking-for-team', '📣・tryouts', '🏟️・matchmaking', '🏆・tournaments', '📊・rankings', '📅・match-schedule']),
    ('🎫 SUPPORT', ['🎟️・open-ticket', '🚨・player-reports', '❓・help']),
    ('🔒 STAFF ONLY', ['💬・staff-chat', '🛠️・dev-log', '📋・mod-logs', '🚨・reports']),
]
VOICE = ['🔊・General VC', '⚽・Team VC 1', '⚽・Team VC 2', '⚽・Team VC 3', '⚽・Team VC 4', '🏆・Tournament VC']

@bot.event
async def on_ready():
    if GUILD_ID:
        guild = discord.Object(id=int(GUILD_ID))
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
    else:
        await bot.tree.sync()
    print(f'Conectado como {bot.user}')

@bot.tree.command(name='setup', description='Crea la estructura oficial del servidor LOCKED')
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    guild = interaction.guild
    if guild is None:
        return await interaction.followup.send('Este comando solo funciona dentro de un servidor.', ephemeral=True)
    try:
        role_map = {}
        for name, color in ROLES:
            role = discord.utils.get(guild.roles, name=name)
            if role is None:
                # Roles decorativos: no se conceden permisos administrativos automáticamente.
                role = await guild.create_role(name=name, colour=color, reason='LOCKED setup')
            role_map[name] = role

        staff_names = ['👑 Owner', '💻 Developer', '🛡️ Administrator', '🔨 Moderator']
        staff_overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
        for name in staff_names:
            staff_overwrites[role_map[name]] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        info_overwrites = {guild.default_role: discord.PermissionOverwrite(send_messages=False, view_channel=True)}
        info_overwrites[guild.me] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        created_channels = {}
        for category_name, channels in CATEGORIES:
            category = discord.utils.get(guild.categories, name=category_name)
            is_staff = category_name.startswith('🔒')
            if category is None:
                category = await guild.create_category(
                 category_name,
                 overwrites=staff_overwrites if is_staff else {},
                 reason='LOCKED setup'
                )
            elif is_staff:
                await category.edit(overwrites=staff_overwrites, reason='Proteger categoría de staff')
            for name in channels:
                channel = discord.utils.get(category.text_channels, name=name)
                if channel is None:
                    overwrites = info_overwrites if category_name.startswith('📌') else {}
                    channel = await guild.create_text_channel(name, category=category, overwrites=overwrites, reason='LOCKED setup')
                created_channels[name] = channel

        voice_cat = discord.utils.get(guild.categories, name='🎙️ VOICE CHANNELS')
        if voice_cat is None:
            voice_cat = await guild.create_category('🎙️ VOICE CHANNELS', reason='LOCKED setup')
        for name in VOICE:
            if discord.utils.get(voice_cat.voice_channels, name=name) is None:
                await guild.create_voice_channel(name, category=voice_cat, reason='LOCKED setup')

        # Los mensajes solo se publican una vez, buscando un marcador en el historial.
        posts = {
            '👋・welcome': ('LOCKED • OFFICIAL WELCOME', '⚽ **WELCOME TO LOCKED!**\n\nTHE FIELD IS WAITING FOR YOU.\n\n🔥 Discover weapons, traits and flows.\n🏆 Build your team and compete in tournaments.\n📢 Find events, codes and announcements here.\n\n**YOUR EGO. YOUR WEAPON. YOUR LEGACY.**'),
            '📜・rules': ('LOCKED • SERVER RULES', '📜 **SERVER RULES**\n\n1. Respect everyone. No harassment or discrimination.\n2. No spam, scams or malicious links.\n3. No cheats, exploits or unfair competitive play.\n4. Keep content in its appropriate channel.\n5. Protect personal information.\n6. Follow Discord and Roblox rules.\n7. Follow reasonable staff instructions.\n\nViolations may lead to moderation actions.'),
            '📋・comp-rules': ('LOCKED • COMP RULES', '🏆 **COMPETITIVE RULES**\n\n• Every team must have a manager (DT).\n• The DT does not play in official matches.\n• Tryouts last 45 minutes.\n• All COMP cards begin at Bronze (F).\n• Follow tournament announcements for match-specific rules.'),
        }
        for channel_name, (marker, body) in posts.items():
            channel = created_channels[channel_name]
            found = False
            async for message in channel.history(limit=100):
                if message.author == bot.user and marker in message.content:
                    found = True
                    break
            if not found:
                await channel.send(f'**{marker}**\n\n{body}')

        await interaction.followup.send('✅ ¡Servidor LOCKED configurado! Categorías, roles, canales y mensajes iniciales listos. Asigna manualmente los roles de staff a personas de confianza.', ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send('❌ Faltan permisos. Dale al bot Manage Channels, Manage Roles y Send Messages, y coloca su rol por encima de los roles que creará.', ephemeral=True)
    except discord.HTTPException as exc:
        await interaction.followup.send(f'❌ Error de Discord: {exc}', ephemeral=True)

@setup.error
async def setup_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message('❌ Necesitas el permiso de Administrador.', ephemeral=True)
    else:
        if not interaction.response.is_done():
            await interaction.response.send_message('❌ No se pudo ejecutar el comando.', ephemeral=True)
        print(f'Error: {error}')

if not TOKEN:
    raise RuntimeError('Configura DISCORD_TOKEN como variable de entorno.')
bot.run(TOKEN)
