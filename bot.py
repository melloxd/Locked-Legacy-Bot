import os
import logging
import io
import asyncio
from PIL import Image, ImageDraw, ImageFont, ImageOps
import discord
from discord import app_commands
from discord.ext import commands

logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('DISCORD_GUILD_ID')
VERIFIED_ROLE = '✅ Verified'
WELCOME_CHANNEL = '👋・welcome'
VERIFY_CHANNEL = '🔐・verification'
TICKET_CHANNEL = '🎟️・open-ticket'
TICKET_CATEGORY = '🎫 ACTIVE TICKETS'
TICKET_STAFF_ROLES = {'👑 Owner', '🛡️ Administrator', '🔨 Moderator'}

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
        self.add_view(TicketPanelView())
        self.add_view(TicketCloseView())
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

def ticket_owner_id(channel: discord.TextChannel) -> int | None:
    topic = channel.topic or ''
    if topic.startswith('locked-ticket-owner:'):
        try:
            return int(topic.split(':', 1)[1])
        except ValueError:
            return None
    return None


def is_ticket_staff(member: discord.Member) -> bool:
    return member.guild_permissions.administrator or any(role.name in TICKET_STAFF_ROLES for role in member.roles)


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Open Ticket', emoji='🎫', style=discord.ButtonStyle.primary,
                       custom_id='locked_legacy:ticket_open:v1')
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        if guild is None or not isinstance(member, discord.Member):
            await interaction.response.send_message('Tickets are available only in the server.', ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY)
        if category is None:
            await interaction.followup.send('Ticket system is not configured. Ask staff to run /tickets_setup.', ephemeral=True)
            return
        existing = next((c for c in category.text_channels if ticket_owner_id(c) == member.id), None)
        if existing:
            await interaction.followup.send(f'You already have an open ticket: {existing.mention}', ephemeral=True)
            return
        if len(category.channels) >= 45:
            await interaction.followup.send('Ticket capacity reached. Please try again later.', ephemeral=True)
            return
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True,
                                                 attach_files=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True,
                                                   manage_channels=True, read_message_history=True),
        }
        for role in guild.roles:
            if role.name in TICKET_STAFF_ROLES:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True,
                                                                read_message_history=True)
        try:
            channel = await guild.create_text_channel(
                name=f'ticket-{member.id}', category=category, overwrites=overwrites,
                topic=f'locked-ticket-owner:{member.id}', reason=f'Ticket opened by {member.id}')
            embed = discord.Embed(title='🎫 LOCKED LEGACY | SUPPORT',
                description=f'Hello {member.mention}! Describe your issue here.\n\n'
                            'Our staff will respond when available. Press **Close Ticket** when finished.',
                colour=discord.Colour.from_rgb(145, 79, 230))
            await channel.send(embed=embed, view=TicketCloseView(),
                               allowed_mentions=discord.AllowedMentions(users=True))
            await interaction.followup.send(f'✅ Ticket created: {channel.mention}', ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send('❌ I need Manage Channels and permission to manage this category.', ephemeral=True)
        except discord.HTTPException:
            logging.exception('Could not open ticket')
            await interaction.followup.send('❌ Could not create your ticket. Try again later.', ephemeral=True)


class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Close Ticket', emoji='🔒', style=discord.ButtonStyle.danger,
                       custom_id='locked_legacy:ticket_close:v1')
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        member = interaction.user
        if not isinstance(channel, discord.TextChannel) or not isinstance(member, discord.Member):
            await interaction.response.send_message('This button only works in a ticket.', ephemeral=True)
            return
        owner_id = ticket_owner_id(channel)
        if owner_id is None or (member.id != owner_id and not is_ticket_staff(member)):
            await interaction.response.send_message('Only the ticket owner or support staff can close this ticket.', ephemeral=True)
            return
        await interaction.response.send_message('🔒 Closing this ticket...', ephemeral=True)
        try:
            await channel.delete(reason=f'Ticket closed by {member.id}')
        except discord.HTTPException:
            logging.exception('Could not close ticket')


@bot.tree.command(name='tickets_setup', description='Create the LOCKED LEGACY support ticket panel')
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def tickets_setup(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message('Only available in a server.', ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    guild = interaction.guild
    try:
        support_category = discord.utils.get(guild.categories, name='🎫 SUPPORT')
        if support_category is None:
            support_category = await guild.create_category('🎫 SUPPORT', reason='LOCKED ticket setup')
        panel_channel = discord.utils.get(guild.text_channels, name=TICKET_CHANNEL)
        if panel_channel is None:
            panel_channel = await guild.create_text_channel(TICKET_CHANNEL, category=support_category,
                                                             reason='LOCKED ticket setup')
        await panel_channel.set_permissions(guild.default_role, view_channel=False)
        verified = discord.utils.get(guild.roles, name=VERIFIED_ROLE)
        if verified:
            await panel_channel.set_permissions(verified, view_channel=True, send_messages=False,
                                                read_message_history=True)
        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY)
        if category is None:
            await guild.create_category(TICKET_CATEGORY,
                overwrites={guild.default_role: discord.PermissionOverwrite(view_channel=False)},
                reason='LOCKED private ticket category')
        embed = discord.Embed(title='🎫 LOCKED LEGACY | SUPPORT CENTER',
            description='Need help with LOCKED LEGACY?\n\n'
                        'Press **Open Ticket** to create a private support channel. '
                        'Only you and the support team will be able to read it.\n\n'
                        '**Please do not share passwords or personal information.**',
            colour=discord.Colour.from_rgb(145, 79, 230))
        embed.set_footer(text='LOCKED LEGACY • Official Support')
        old_panel = None
        async for message in panel_channel.history(limit=100):
            if message.author.id == bot.user.id and message.embeds and message.embeds[0].title == embed.title:
                old_panel = message
                break
        if old_panel:
            await old_panel.edit(embed=embed, view=TicketPanelView())
        else:
            await panel_channel.send(embed=embed, view=TicketPanelView())
        await interaction.followup.send(f'✅ Ticket panel ready in {panel_channel.mention}. '
            'Assign Owner, Administrator or Moderator roles to your support staff.', ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send('❌ Missing Manage Channels or channel permissions.', ephemeral=True)
    except discord.HTTPException:
        logging.exception('Ticket setup failed')
        await interaction.followup.send('❌ Ticket setup failed. Check Railway logs.', ephemeral=True)


@bot.event
async def on_ready():
    logging.info('LOCKED LEGACY BOT online as %s (%s)', bot.user, bot.user.id if bot.user else '?')

def _font(size: int, bold: bool = False):
    name = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()


def _welcome_card(avatar_bytes: bytes, player_name: str, member_number: int) -> io.BytesIO:
    """Render a 1000x360 welcome card off the Discord event loop."""
    w, h = 1000, 360
    im = Image.new('RGB', (w, h), (14, 11, 24))
    d = ImageDraw.Draw(im)
    # Purple ambient lighting and angular accents.
    for i in range(160, 0, -1):
        c = (min(255, 15 + (160-i)//8), 11, min(255, 25 + (160-i)//3))
        d.ellipse((710-i*2, 140-i*2, 710+i*2, 140+i*2), outline=c, width=2)
    d.polygon([(0,0),(380,0),(250,360),(0,360)], fill=(25,17,42))
    d.polygon([(835,0),(1000,0),(1000,360),(720,360)], fill=(33,19,53))
    d.rounded_rectangle((14,14,986,346), radius=22, outline=(125,65,205), width=3)
    d.line((310,75,310,285), fill=(133,74,205), width=3)
    # Avatar with purple ring.
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert('RGB')
    avatar = ImageOps.fit(avatar, (208,208), method=Image.Resampling.LANCZOS)
    mask = Image.new('L',(208,208),0)
    ImageDraw.Draw(mask).ellipse((0,0,207,207),fill=255)
    d.ellipse((48,65,272,289),fill=(145,79,230))
    im.paste(avatar,(56,73),mask)
    d.text((355,62),'LOCKED LEGACY  /  NEW PLAYER',font=_font(22,True),fill=(187,142,255))
    d.text((355,112),'WELCOME TO LEGACY',font=_font(43,True),fill=(250,248,255))
    safe_name = player_name[:25]
    d.text((355,181),safe_name,font=_font(31,True),fill=(224,209,255))
    d.text((355,238),f'PLAYER #{member_number:04d}',font=_font(23,True),fill=(186,143,246))
    d.text((355,289),'YOUR EGO. YOUR LEGACY. YOUR GAME.',font=_font(18),fill=(202,194,218))
    out = io.BytesIO()
    im.save(out,format='PNG',optimize=True)
    out.seek(0)
    return out


async def send_legacy_welcome(member: discord.Member, channel: discord.TextChannel):
    try:
        avatar_bytes = await member.display_avatar.replace(size=256,format='png').read()
        card = await asyncio.to_thread(_welcome_card, avatar_bytes, member.display_name, member.guild.member_count or 0)
        embed = discord.Embed(
            description=(f'Welcome {member.mention}! ⚽\n'
                         f'Head to **{VERIFY_CHANNEL}** and press **Verify** to unlock the server.\n'
                         '**Forge your legacy. Awaken your ego.**'),
            colour=discord.Colour.from_rgb(145, 79, 230)
        )
        embed.set_image(url='attachment://legacy_welcome.png')
        embed.set_footer(text='LOCKED LEGACY • Official Community')
        await channel.send(embed=embed, file=discord.File(card,filename='legacy_welcome.png'),
                           allowed_mentions=discord.AllowedMentions(users=True))
    except (discord.HTTPException, OSError, ValueError):
        logging.exception('Could not send Legacy welcome card')


@bot.event
async def on_member_join(member: discord.Member):
    channel = discord.utils.get(member.guild.text_channels, name=WELCOME_CHANNEL)
    if channel is not None:
        await send_legacy_welcome(member, channel)


@bot.tree.command(name='welcome_test', description='Preview the LOCKED LEGACY welcome card')
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def welcome_test(interaction: discord.Interaction):
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message('Only available in a server.', ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    channel = discord.utils.get(interaction.guild.text_channels, name=WELCOME_CHANNEL)
    if channel is None:
        await interaction.followup.send('Welcome channel not found. Run /setup first.', ephemeral=True)
        return
    await send_legacy_welcome(interaction.user, channel)
    await interaction.followup.send(f'Welcome preview sent to {channel.mention}.', ephemeral=True)


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

async def ensure_legacy_roles(guild: discord.Guild) -> tuple[list[str], list[str]]:
    """Create missing decorative roles without granting privileged permissions."""
    created, existing = [], []
    for name, colour in ROLES:
        role = discord.utils.get(guild.roles, name=name)
        if role is None:
            await guild.create_role(name=name, colour=colour, permissions=discord.Permissions.none(),
                                    reason='LOCKED LEGACY role configuration')
            created.append(name)
        else:
            existing.append(name)
    return created, existing


@bot.tree.command(name='roles_setup', description='Create missing LOCKED LEGACY roles safely')
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def roles_setup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    guild = interaction.guild
    if guild is None:
        await interaction.followup.send('Only available inside a server.', ephemeral=True)
        return
    try:
        created, existing = await ensure_legacy_roles(guild)
        await interaction.followup.send(
            f'✅ Roles configured. Created: {len(created)}; already present: {len(existing)}.\n'
            'Roles are decorative by default: assign Owner, Developer, Administrator and Moderator manually. '
            'Move the bot role above Verified so the verification button works.', ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send('❌ Give the bot Manage Roles and position its role above the roles it creates.', ephemeral=True)
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
        await ensure_legacy_roles(guild)
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
        await interaction.followup.send('✅ LOCKED LEGACY server structure and roles configured. Run /verification_setup. Assign staff roles manually.', ephemeral=True)
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
