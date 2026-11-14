import os
import discord
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('DISCORD_GUILD_ID')

intents = discord.Intents.default()
intents.members = True
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
    bot.add_view(VerifyView())
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
                category = await guild.create_category(category_name, overwrites=staff_overwrites if is_staff else {}, reason='LOCKED setup')
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


# LOCKED LEGACY: Bienvenida y verificación
VERIFIED_ROLE = '✅ Verified'
WELCOME_CHANNEL = '👋・welcome'
VERIFY_CHANNEL = '🔐・verification'
PUBLIC_CHANNEL_EXCEPTIONS = {'👋・welcome', '🔐・verification', '📜・rules'}

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Verify', emoji='✅', style=discord.ButtonStyle.success, custom_id='locked_legacy:verify:v1')
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message('Verification is only available in the server.', ephemeral=True)
        role = discord.utils.get(interaction.guild.roles, name=VERIFIED_ROLE)
        if role is None:
            return await interaction.response.send_message('Verification is not configured. Contact staff.', ephemeral=True)
        if role in interaction.user.roles:
            return await interaction.response.send_message('You are already verified! ⚽', ephemeral=True)
        try:
            await interaction.user.add_roles(role, reason='LOCKED LEGACY button verification')
            await interaction.response.send_message('✅ Verified! Welcome to LOCKED: LEGACY. Forge your legacy!', ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message('I cannot assign the role. Ask staff to move my bot role above Verified.', ephemeral=True)
        except discord.HTTPException:
            await interaction.response.send_message('Verification failed temporarily. Please try again.', ephemeral=True)

@bot.event
async def on_member_join(member: discord.Member):
    channel = discord.utils.get(member.guild.text_channels, name=WELCOME_CHANNEL)
    if channel is None:
        return
    embed = discord.Embed(
        title='⚽ WELCOME TO LOCKED: LEGACY',
        description=(f'Welcome {member.mention}!\n\n'
                     '⛓️ **Forge Your Legacy. Awaken Your Ego.**\n\n'
                     f'You are player **#{member.guild.member_count}**.\n'
                     f'Head to **#{VERIFY_CHANNEL}** and press **Verify** to unlock the server.\n\n'
                     '**YOUR EGO. YOUR LEGACY. YOUR GAME.**'),
        color=discord.Color.from_rgb(34, 123, 235))
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text='LOCKED: LEGACY • Official Community')
    try:
        await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions(users=True))
    except discord.HTTPException as exc:
        print(f'Welcome message failed: {exc}')

@bot.tree.command(name='verification_setup', description='Configura el panel de verificación LOCKED LEGACY')
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def verification_setup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    if guild is None:
        return await interaction.followup.send('Only available in a server.', ephemeral=True)
    try:
        role = discord.utils.get(guild.roles, name=VERIFIED_ROLE)
        if role is None:
            role = await guild.create_role(name=VERIFIED_ROLE, colour=discord.Colour.green(), reason='LOCKED verification')
        category = discord.utils.get(guild.categories, name='📌 INFORMATION')
        if category is None:
            category = await guild.create_category('📌 INFORMATION')
        channel = discord.utils.get(guild.text_channels, name=VERIFY_CHANNEL)
        if channel is None:
            channel = await guild.create_text_channel(VERIFY_CHANNEL, category=category)
        # Gating by role: unverified members cannot see other public channels.
        # Explicit channel overwrites are set to override category-level access.
        for ch in guild.channels:
            if isinstance(ch, discord.CategoryChannel) or isinstance(ch, discord.Thread):
                continue
            if ch.category and ch.category.name == '🔒 STAFF ONLY':
                continue
            if ch.name in PUBLIC_CHANNEL_EXCEPTIONS:
                await ch.set_permissions(guild.default_role, view_channel=True, reason='LOCKED verification')
                await ch.set_permissions(role, view_channel=True, reason='LOCKED verification')
                if ch.name in {VERIFY_CHANNEL, '📜・rules'}:
                    await ch.set_permissions(guild.default_role, send_messages=False, reason='LOCKED verification')
            else:
                await ch.set_permissions(guild.default_role, view_channel=False, reason='LOCKED verification')
                await ch.set_permissions(role, view_channel=True, reason='LOCKED verification')
        # Restrict the verification channel to a read-only panel for everyone.
        await channel.set_permissions(guild.default_role, view_channel=True, send_messages=False)
        await channel.set_permissions(role, view_channel=True, send_messages=False)
        marker = 'LOCKED: LEGACY — VERIFICATION'
        found = False
        async for msg in channel.history(limit=100):
            if msg.author.id == bot.user.id and msg.embeds and msg.embeds[0].title == marker:
                found = True
                break
        if not found:
            embed = discord.Embed(title=marker,
                description='⚽ **Welcome to the field.**\n\nRead the rules and press **Verify** to unlock the community.\n\n⛓️ **Forge Your Legacy. Awaken Your Ego.**',
                color=discord.Color.blue())
            await channel.send(embed=embed, view=VerifyView())
        await interaction.followup.send('✅ Verification configured! Test with a non-staff account. Existing members may need the Verified role assigned manually.', ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send('❌ Missing Manage Roles/Manage Channels permissions, or the bot role is below Verified.', ephemeral=True)
    except discord.HTTPException as exc:
        await interaction.followup.send(f'❌ Discord error: {exc}', ephemeral=True)

if not TOKEN:
    raise RuntimeError('Configura DISCORD_TOKEN como variable de entorno.')
bot.run(TOKEN)
