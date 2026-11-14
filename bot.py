import os
import logging
import discord
from discord import app_commands
from discord.ext import commands

logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('DISCORD_GUILD_ID')
VERIFIED_ROLE = '✅ Verified'
WELCOME_CHANNEL = '👋・welcome'
VERIFY_CHANNEL = '🔐・verification'

ROLES = [
    ('👑 Owner', discord.Colour.gold()),
    ('💻 Developer', discord.Colour.blue()),
    ('🛡️ Administrator', discord.Colour.red()),
    ('🔨 Moderator', discord.Colour.orange()),
    ('🎨 Designer', discord.Colour.purple()),
    ('🧠 Content Creator', discord.Colour.magenta()),
    ('🏆 Tournament Host', discord.Colour.gold()),
    ('📋 Team Manager', discord.Colour.teal()),
    ('⚽ Competitive Player', discord.Colour.green()),
    ('💎 VIP', discord.Colour.blurple()),
    ('🏅 Player', discord.Colour.light_grey()),
    (VERIFIED_ROLE, discord.Colour.green()),
]
CATEGORIES = {
    '📌 INFORMATION': ['👋・welcome', '📜・rules', '📢・announcements', '📰・updates', '🎁・codes', '🔗・links', VERIFY_CHANNEL],
    '💬 COMMUNITY': ['💬・general', '🇪🇸・español', '🌎・english', '📸・media', '🎨・fan-art', '🤖・bot-commands'],
    '⚽ LOCKED GAME': ['🎮・game-discussion', '⚔️・weapons', '🧬・traits', '🔥・flows', '💡・suggestions', '🐛・bug-reports', '🎥・clips'],
    '🏆 COMPETITIVE': ['📋・comp-rules', '📝・team-registration', '🔎・looking-for-team', '⚽・tryouts', '🥅・matchmaking', '🏆・tournaments', '📊・rankings', '📅・match-schedule'],
    '🎫 SUPPORT': ['🎟️・open-ticket', '🚨・player-reports', '❓・help'],
    '🔒 STAFF ONLY': ['💬・staff-chat', '🛠️・dev-log', '📋・mod-logs', '🚨・reports'],
}
VOICE = ['🔊・General VC', '⚽・Team VC 1', '⚽・Team VC 2', '⚽・Team VC 3', '⚽・Team VC 4', '🏆・Tournament VC']

intents = discord.Intents.default()
intents.members = True

class LockedBot(commands.Bot):
    async def setup_hook(self):
        self.add_view(VerifyView())
        try:
            if GUILD_ID:
                guild = discord.Object(id=int(GUILD_ID))
                self.tree.copy_global_to(guild=guild)
                commands_synced = await self.tree.sync(guild=guild)
            else:
                commands_synced = await self.tree.sync()
            logging.info('Synced commands: %s', [c.name for c in commands_synced])
        except (discord.HTTPException, ValueError):
            logging.exception('Command sync failed. Check DISCORD_GUILD_ID and application permissions.')

bot = LockedBot(command_prefix='!', intents=intents)

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Verify', emoji='✅', style=discord.ButtonStyle.success, custom_id='locked_legacy:verify:v1')
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message('Verification is only available in the server.', ephemeral=True)
            return
        role = discord.utils.get(interaction.guild.roles, name=VERIFIED_ROLE)
        if role is None:
            await interaction.response.send_message('Verification role missing. Ask an administrator to run /verification_setup.', ephemeral=True)
            return
        if role in interaction.user.roles:
            await interaction.response.send_message('You are already verified! ⚽', ephemeral=True)
            return
        try:
            await interaction.user.add_roles(role, reason='LOCKED LEGACY verification')
            await interaction.response.send_message('✅ Verified! Welcome to LOCKED: LEGACY.', ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message('I cannot assign the role. Move my bot role above Verified and check Manage Roles.', ephemeral=True)
        except discord.HTTPException:
            await interaction.response.send_message('Verification failed temporarily. Please try again.', ephemeral=True)

@bot.event
async def on_ready():
    logging.info('LOCKED LEGACY BOT online as %s (%s)', bot.user, bot.user.id if bot.user else '?')

@bot.event
async def on_member_join(member: discord.Member):
    channel = discord.utils.get(member.guild.text_channels, name=WELCOME_CHANNEL)
    if channel is None:
        return
    embed = discord.Embed(
        title='⚽ WELCOME TO LOCKED: LEGACY',
        description=(f'Welcome {member.mention}!\n\n'
                     '**Forge Your Legacy. Awaken Your Ego.**\n\n'
                     f'You are player **#{member.guild.member_count}**.\n'
                     f'Head to **#{VERIFY_CHANNEL}** and press **Verify** to unlock the server.\n\n'
                     '**YOUR EGO. YOUR LEGACY. YOUR GAME.**'),
        colour=discord.Colour.from_rgb(34, 123, 235)
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text='LOCKED: LEGACY • Official Community')
    try:
        await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions(users=True))
    except discord.HTTPException:
        logging.exception('Could not send welcome message')

@bot.tree.command(name='verification_setup', description='Create or update the LOCKED LEGACY verification panel')
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def verification_setup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    if guild is None:
        await interaction.followup.send('This command only works in a server.', ephemeral=True)
        return
    try:
        role = discord.utils.get(guild.roles, name=VERIFIED_ROLE)
        if role is None:
            role = await guild.create_role(name=VERIFIED_ROLE, colour=discord.Colour.green(), reason='LOCKED verification')
        category = discord.utils.get(guild.categories, name='📌 INFORMATION')
        if category is None:
            category = await guild.create_category('📌 INFORMATION', reason='LOCKED verification')
        channel = discord.utils.get(guild.text_channels, name=VERIFY_CHANNEL)
        if channel is None:
            channel = await guild.create_text_channel(VERIFY_CHANNEL, category=category, reason='LOCKED verification')
        await channel.set_permissions(guild.default_role, view_channel=True, send_messages=False)
        embed = discord.Embed(
            title='🔐 LOCKED: LEGACY | VERIFICATION',
            description='**Forge Your Legacy. Awaken Your Ego.**\n\nPress **Verify** below to receive access to the community.\n\n⚽ One click. Your journey starts here.',
            colour=discord.Colour.from_rgb(34, 123, 235)
        )
        embed.set_footer(text='LOCKED: LEGACY • Official Community')
        # Update an existing bot panel if possible, avoiding duplicates.
        panel = None
        async for msg in channel.history(limit=100):
            if msg.author.id == bot.user.id and msg.embeds and msg.embeds[0].title == embed.title:
                panel = msg
                break
        if panel:
            await panel.edit(embed=embed, view=VerifyView())
        else:
            await channel.send(embed=embed, view=VerifyView())
        await interaction.followup.send(f'✅ Verification panel ready in {channel.mention}.', ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send('❌ Missing permissions. Grant Manage Roles, Manage Channels, View Channel and Send Messages; keep the bot role above Verified.', ephemeral=True)
    except discord.HTTPException as exc:
        await interaction.followup.send(f'❌ Discord API error: {exc}', ephemeral=True)

@bot.tree.command(name='setup', description='Create the official LOCKED LEGACY server structure')
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    guild = interaction.guild
    if guild is None:
        await interaction.followup.send('This command only works in a server.', ephemeral=True)
        return
    try:
        for name, colour in ROLES:
            if discord.utils.get(guild.roles, name=name) is None:
                await guild.create_role(name=name, colour=colour, reason='LOCKED setup')
        verified = discord.utils.get(guild.roles, name=VERIFIED_ROLE)
        staff_names = {'👑 Owner', '💻 Developer', '🛡️ Administrator', '🔨 Moderator'}
        staff_overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
        for role in guild.roles:
            if role.name in staff_names:
                staff_overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        for category_name, channels in CATEGORIES.items():
            category = discord.utils.get(guild.categories, name=category_name)
            if category is None:
                category = await guild.create_category(category_name, overwrites=staff_overwrites if category_name == '🔒 STAFF ONLY' else {}, reason='LOCKED setup')
            elif category_name == '🔒 STAFF ONLY':
                await category.edit(overwrites=staff_overwrites, reason='Protect LOCKED staff channels')
            for channel_name in channels:
                channel = discord.utils.get(guild.text_channels, name=channel_name)
                if channel is None:
                    channel = await guild.create_text_channel(channel_name, category=category, reason='LOCKED setup')
                if category_name == '🔒 STAFF ONLY':
                    await channel.edit(sync_permissions=True, reason='Protect LOCKED staff channels')
                elif channel_name == VERIFY_CHANNEL:
                    await channel.set_permissions(guild.default_role, view_channel=True, send_messages=False)
                elif channel_name != WELCOME_CHANNEL and verified:
                    await channel.set_permissions(guild.default_role, view_channel=False)
                    await channel.set_permissions(verified, view_channel=True)
                elif channel_name == WELCOME_CHANNEL:
                    await channel.set_permissions(guild.default_role, view_channel=True, send_messages=False)
        voice_category = discord.utils.get(guild.categories, name='🔊 VOICE CHANNELS')
        if voice_category is None:
            voice_category = await guild.create_category('🔊 VOICE CHANNELS', reason='LOCKED setup')
        for name in VOICE:
            if discord.utils.get(guild.voice_channels, name=name) is None:
                await guild.create_voice_channel(name, category=voice_category, reason='LOCKED setup')
        if verified:
            await voice_category.set_permissions(guild.default_role, view_channel=False)
            await voice_category.set_permissions(verified, view_channel=True)
        await interaction.followup.send('✅ LOCKED LEGACY server structure created. Now run /verification_setup.', ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send('❌ Missing permissions: Manage Roles or Manage Channels. Check the bot role position.', ephemeral=True)
    except discord.HTTPException as exc:
        await interaction.followup.send(f'❌ Discord API error: {exc}', ephemeral=True)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        message = '❌ Only server administrators can use this command.'
    else:
        logging.error('Slash command failed: %r', error)
        message = '❌ An unexpected error occurred. Check the bot logs.'
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)

if __name__ == '__main__':
    if not TOKEN:
        raise RuntimeError('Set DISCORD_TOKEN in Railway Variables.')
    if GUILD_ID:
        try:
            int(GUILD_ID)
        except ValueError as exc:
            raise RuntimeError('DISCORD_GUILD_ID must be a numeric server ID.') from exc
    bot.run(TOKEN)
