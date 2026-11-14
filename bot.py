import os
import logging
import io
import asyncio
import sqlite3
import time
import math
import random
from pathlib import Path
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
# Message content intent is NOT required: we count message events, not their text.

class LockedBot(commands.Bot):
    async def setup_hook(self):
        init_levels_db()
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

# V9: Language is private to each Discord user, not a server-wide setting.
LANGUAGES = {'en': 'English', 'es': 'Español', 'pt': 'Português', 'fr': 'Français', 'de': 'Deutsch', 'it': 'Italiano'}
LOCALE_TO_LANGUAGE = {'en': 'en', 'es': 'es', 'pt': 'pt', 'fr': 'fr', 'de': 'de', 'it': 'it'}
TRANSLATIONS = {
 'en': {'saved':'Your language is now **{language}**.','current':'Your current language is **{language}**.','server_only':'This command only works in a server.','already_verified':'Already verified.','verified':'✅ Verified! Welcome to LOCKED LEGACY.','verify_missing':'Verify missing.','verify_forbidden':'Verify forbidden.','verify_error':'Verify error.','tickets_server':'Tickets server.','ticket_missing':'Ticket missing.','ticket_existing':'You already have an open ticket: {channel}','ticket_full':'Ticket full.','ticket_created':'✅ Ticket created: {channel}','ticket_forbidden':'❌ I need Manage Channels permission.','ticket_error':'Ticket error.','ticket_greeting':'Hello {member}! Describe your issue here. Our staff will respond when available. Press **Close Ticket** when finished.','ticket_only':'Ticket only.','ticket_not_owner':'Ticket not owner.','ticket_closing':'Ticket closing.','db_error':'Db error.','top_error':'Top error.','rank_fallback':'{member}: Level {level} · {xp:,} XP · {messages:,} messages','levelup':'🎉 {member} reached **Level {level}**!','welcome':'Welcome {member}! ⚽\nHead to **{channel}** and press **Verify** to unlock the server.\n**Forge your legacy. Awaken your ego.**','admin_only':'Admin only.','unexpected':'Unexpected.','welcome_missing':'Welcome missing.','welcome_sent':'Welcome preview sent to {channel}.','verify_ready':'✅ Verification panel ready in {channel}.','ticket_ready':'✅ Ticket panel ready in {channel}.','setup_error':'❌ Missing permissions. Check the bot role and permissions.'},
 'es': {'saved':'Tu idioma ahora es **{language}**.','current':'Tu idioma actual es **{language}**.','server_only':'Este comando solo funciona en un servidor.','already_verified':'¡Ya estás verificado! ⚽','verified':'✅ ¡Verificado! Bienvenido a LOCKED LEGACY.','verify_missing':'Falta el rol de verificación. Pide a un administrador que ejecute /verification_setup.','verify_forbidden':'No puedo asignar el rol. Coloca mi rol por encima de Verified y revisa Gestionar roles.','verify_error':'La verificación falló temporalmente. Inténtalo de nuevo.','tickets_server':'Los tickets solo están disponibles en el servidor.','ticket_missing':'Los tickets no están configurados. Pide al staff que ejecute /tickets_setup.','ticket_existing':'Ya tienes un ticket abierto: {channel}','ticket_full':'Se alcanzó el límite de tickets. Inténtalo más tarde.','ticket_created':'✅ Ticket creado: {channel}','ticket_forbidden':'❌ Necesito permiso para gestionar canales.','ticket_error':'❌ No pude crear tu ticket. Inténtalo más tarde.','ticket_greeting':'¡Hola {member}! Describe aquí tu problema. El equipo de soporte responderá cuando pueda. Pulsa **Close Ticket** para cerrar.','ticket_only':'Este botón solo funciona en un ticket.','ticket_not_owner':'Solo el dueño del ticket o el staff puede cerrarlo.','ticket_closing':'🔒 Cerrando ticket...','db_error':'La base de datos de niveles no está disponible.','top_error':'No se pudo generar la tarjeta del top. Inténtalo de nuevo.','rank_fallback':'{member}: Nivel {level} · {xp:,} XP · {messages:,} mensajes','levelup':'🎉 ¡{member} alcanzó el **nivel {level}**!','welcome':'¡Bienvenido, {member}! ⚽\nVe a **{channel}** y pulsa **Verify** para desbloquear el servidor.\n**Construye tu legado. Despierta tu ego.**','admin_only':'❌ Solo los administradores pueden usar este comando.','unexpected':'❌ Ocurrió un error inesperado. Revisa los registros del bot.','welcome_missing':'No encontré el canal de bienvenida. Ejecuta /setup primero.','welcome_sent':'Vista previa enviada a {channel}.','verify_ready':'✅ Panel de verificación listo en {channel}.','ticket_ready':'✅ Panel de tickets listo en {channel}.','setup_error':'❌ Faltan permisos. Revisa el rol y los permisos del bot.'},
 'pt': {'saved':'Seu idioma agora é **{language}**.','current':'Seu idioma atual é **{language}**.','server_only':'Este comando só funciona em um servidor.','already_verified':'Você já está verificado! ⚽','verified':'✅ Verificado! Bem-vindo ao LOCKED LEGACY.','verify_missing':'Cargo de verificação ausente. Peça a um administrador para usar /verification_setup.','verify_forbidden':'Não consigo atribuir o cargo. Coloque meu cargo acima de Verified e confira Gerenciar Cargos.','verify_error':'Falha temporária na verificação. Tente novamente.','tickets_server':'Os tickets só estão disponíveis no servidor.','ticket_missing':'Sistema de tickets não configurado. Peça à equipe para usar /tickets_setup.','ticket_existing':'Você já tem um ticket aberto: {channel}','ticket_full':'Limite de tickets atingido. Tente mais tarde.','ticket_created':'✅ Ticket criado: {channel}','ticket_forbidden':'❌ Preciso da permissão Gerenciar Canais.','ticket_error':'❌ Não foi possível criar seu ticket. Tente mais tarde.','ticket_greeting':'Olá {member}! Descreva seu problema aqui. Nossa equipe responderá assim que possível. Clique em **Close Ticket** ao terminar.','ticket_only':'Este botão só funciona em um ticket.','ticket_not_owner':'Apenas o autor ou a equipe de suporte pode fechar o ticket.','ticket_closing':'🔒 Fechando ticket...','db_error':'Banco de dados de níveis indisponível.','top_error':'Não foi possível gerar o ranking. Tente novamente.','rank_fallback':'{member}: Nível {level} · {xp:,} XP · {messages:,} mensagens','levelup':'🎉 {member} chegou ao **nível {level}**!','welcome':'Bem-vindo, {member}! ⚽\nVá até **{channel}** e clique em **Verify** para acessar o servidor.\n**Construa seu legado. Desperte seu ego.**','admin_only':'❌ Apenas administradores podem usar este comando.','unexpected':'❌ Ocorreu um erro inesperado. Confira os logs do bot.','welcome_missing':'Canal de boas-vindas não encontrado. Use /setup primeiro.','welcome_sent':'Prévia enviada para {channel}.','verify_ready':'✅ Painel de verificação pronto em {channel}.','ticket_ready':'✅ Painel de tickets pronto em {channel}.','setup_error':'❌ Permissões insuficientes. Confira o cargo do bot.'},
 'fr': {'saved':'Votre langue est maintenant **{language}**.','current':'Votre langue actuelle est **{language}**.','server_only':'Cette commande fonctionne uniquement sur un serveur.','already_verified':'Vous êtes déjà vérifié ! ⚽','verified':'✅ Vérifié ! Bienvenue sur LOCKED LEGACY.','verify_missing':'Rôle de vérification introuvable. Demandez à un administrateur de lancer /verification_setup.','verify_forbidden':'Impossible d’attribuer le rôle. Placez mon rôle au-dessus de Verified et vérifiez Gérer les rôles.','verify_error':'La vérification a échoué temporairement. Réessayez.','tickets_server':'Les tickets sont disponibles uniquement sur le serveur.','ticket_missing':'Tickets non configurés. Demandez au staff de lancer /tickets_setup.','ticket_existing':'Vous avez déjà un ticket ouvert : {channel}','ticket_full':'Limite de tickets atteinte. Réessayez plus tard.','ticket_created':'✅ Ticket créé : {channel}','ticket_forbidden':'❌ Il me faut la permission Gérer les salons.','ticket_error':'❌ Impossible de créer votre ticket. Réessayez plus tard.','ticket_greeting':'Bonjour {member} ! Décrivez votre problème ici. Le support répondra dès que possible. Appuyez sur **Close Ticket** pour terminer.','ticket_only':'Ce bouton fonctionne uniquement dans un ticket.','ticket_not_owner':'Seuls le propriétaire du ticket et le staff peuvent le fermer.','ticket_closing':'🔒 Fermeture du ticket...','db_error':'Base de données des niveaux indisponible.','top_error':'Impossible de générer le classement. Réessayez.','rank_fallback':'{member} : Niveau {level} · {xp:,} XP · {messages:,} messages','levelup':'🎉 {member} a atteint le **niveau {level}** !','welcome':'Bienvenue {member} ! ⚽\nAllez dans **{channel}** et appuyez sur **Verify** pour accéder au serveur.\n**Forgez votre héritage. Réveillez votre ego.**','admin_only':'❌ Seuls les administrateurs peuvent utiliser cette commande.','unexpected':'❌ Une erreur inattendue est survenue. Consultez les journaux du bot.','welcome_missing':'Salon de bienvenue introuvable. Lancez /setup.','welcome_sent':'Aperçu envoyé dans {channel}.','verify_ready':'✅ Panneau de vérification prêt dans {channel}.','ticket_ready':'✅ Panneau de tickets prêt dans {channel}.','setup_error':'❌ Permissions insuffisantes. Vérifiez le rôle du bot.'},
 'de': {'saved':'Deine Sprache ist jetzt **{language}**.','current':'Deine aktuelle Sprache ist **{language}**.','server_only':'Dieser Befehl funktioniert nur auf einem Server.','already_verified':'Du bist bereits verifiziert! ⚽','verified':'✅ Verifiziert! Willkommen bei LOCKED LEGACY.','verify_missing':'Verifizierungsrolle fehlt. Bitte einen Admin, /verification_setup auszuführen.','verify_forbidden':'Rolle kann nicht vergeben werden. Verschiebe meine Rolle über Verified und prüfe Rollen verwalten.','verify_error':'Verifizierung vorübergehend fehlgeschlagen. Bitte erneut versuchen.','tickets_server':'Tickets sind nur auf dem Server verfügbar.','ticket_missing':'Tickets sind nicht eingerichtet. Bitte das Team, /tickets_setup auszuführen.','ticket_existing':'Du hast bereits ein offenes Ticket: {channel}','ticket_full':'Ticket-Limit erreicht. Versuche es später erneut.','ticket_created':'✅ Ticket erstellt: {channel}','ticket_forbidden':'❌ Ich benötige die Berechtigung Kanäle verwalten.','ticket_error':'❌ Ticket konnte nicht erstellt werden. Versuche es später erneut.','ticket_greeting':'Hallo {member}! Beschreibe hier dein Problem. Unser Team antwortet so bald wie möglich. Drücke **Close Ticket**, wenn du fertig bist.','ticket_only':'Dieser Button funktioniert nur in einem Ticket.','ticket_not_owner':'Nur der Ticketinhaber oder das Supportteam darf es schließen.','ticket_closing':'🔒 Ticket wird geschlossen...','db_error':'Level-Datenbank nicht verfügbar.','top_error':'Rangliste konnte nicht erstellt werden. Bitte erneut versuchen.','rank_fallback':'{member}: Level {level} · {xp:,} XP · {messages:,} Nachrichten','levelup':'🎉 {member} hat **Level {level}** erreicht!','welcome':'Willkommen {member}! ⚽\nGehe zu **{channel}** und drücke **Verify**, um den Server freizuschalten.\n**Schmiede dein Vermächtnis. Erwecke dein Ego.**','admin_only':'❌ Nur Administratoren dürfen diesen Befehl verwenden.','unexpected':'❌ Ein unerwarteter Fehler ist aufgetreten. Prüfe die Bot-Logs.','welcome_missing':'Willkommenskanal nicht gefunden. Führe zuerst /setup aus.','welcome_sent':'Vorschau in {channel} gesendet.','verify_ready':'✅ Verifizierungspanel bereit in {channel}.','ticket_ready':'✅ Ticket-Panel bereit in {channel}.','setup_error':'❌ Fehlende Berechtigungen. Prüfe die Bot-Rolle.'},
 'it': {'saved':'La tua lingua ora è **{language}**.','current':'La tua lingua attuale è **{language}**.','server_only':'Questo comando funziona solo in un server.','already_verified':'Sei già verificato! ⚽','verified':'✅ Verificato! Benvenuto su LOCKED LEGACY.','verify_missing':'Ruolo di verifica mancante. Chiedi a un amministratore di eseguire /verification_setup.','verify_forbidden':'Non posso assegnare il ruolo. Sposta il mio ruolo sopra Verified e controlla Gestisci ruoli.','verify_error':'Verifica temporaneamente non riuscita. Riprova.','tickets_server':'I ticket sono disponibili solo nel server.','ticket_missing':'Sistema ticket non configurato. Chiedi allo staff di usare /tickets_setup.','ticket_existing':'Hai già un ticket aperto: {channel}','ticket_full':'Limite di ticket raggiunto. Riprova più tardi.','ticket_created':'✅ Ticket creato: {channel}','ticket_forbidden':'❌ Mi serve il permesso Gestisci canali.','ticket_error':'❌ Impossibile creare il ticket. Riprova più tardi.','ticket_greeting':'Ciao {member}! Descrivi qui il problema. Il supporto risponderà appena possibile. Premi **Close Ticket** al termine.','ticket_only':'Questo pulsante funziona solo in un ticket.','ticket_not_owner':'Solo il proprietario del ticket o lo staff può chiuderlo.','ticket_closing':'🔒 Chiusura ticket...','db_error':'Database dei livelli non disponibile.','top_error':'Impossibile generare la classifica. Riprova.','rank_fallback':'{member}: Livello {level} · {xp:,} XP · {messages:,} messaggi','levelup':'🎉 {member} ha raggiunto il **livello {level}**!','welcome':'Benvenuto {member}! ⚽\nVai su **{channel}** e premi **Verify** per sbloccare il server.\n**Crea la tua leggenda. Risveglia il tuo ego.**','admin_only':'❌ Solo gli amministratori possono usare questo comando.','unexpected':'❌ Si è verificato un errore imprevisto. Controlla i log.','welcome_missing':'Canale di benvenuto non trovato. Esegui /setup.','welcome_sent':'Anteprima inviata in {channel}.','verify_ready':'✅ Pannello di verifica pronto in {channel}.','ticket_ready':'✅ Pannello ticket pronto in {channel}.','setup_error':'❌ Permessi insufficienti. Controlla il ruolo del bot.'},
}
CARD_LABELS = {
 'en': ('PLAYER RANK / IDENTITY','LEVEL','MESSAGES','TOP 10 / EXPERIENCE','TOP 10 / MESSAGES','NO ACTIVITY RECORDED YET','LEVEL UP / NEW ACHIEVEMENT','TOTAL XP','NEW PLAYER REGISTERED','PLAYER','MEMBER'),
 'es': ('RANGO / IDENTIDAD','NIVEL','MENSAJES','TOP 10 / EXPERIENCIA','TOP 10 / MENSAJES','SIN ACTIVIDAD TODAVÍA','SUBIDA DE NIVEL / LOGRO','XP TOTALES','NUEVO JUGADOR REGISTRADO','JUGADOR','MIEMBRO'),
 'pt': ('RANK / IDENTIDADE','NÍVEL','MENSAGENS','TOP 10 / EXPERIÊNCIA','TOP 10 / MENSAGENS','SEM ATIVIDADE AINDA','SUBIU DE NÍVEL / CONQUISTA','XP TOTAL','NOVO JOGADOR REGISTRADO','JOGADOR','MEMBRO'),
 'fr': ('RANG / IDENTITÉ','NIVEAU','MESSAGES','TOP 10 / EXPÉRIENCE','TOP 10 / MESSAGES','AUCUNE ACTIVITÉ','NIVEAU SUPÉRIEUR / SUCCÈS','XP TOTAL','NOUVEAU JOUEUR INSCRIT','JOUEUR','MEMBRE'),
 'de': ('RANG / IDENTITÄT','LEVEL','NACHRICHTEN','TOP 10 / ERFAHRUNG','TOP 10 / NACHRICHTEN','NOCH KEINE AKTIVITÄT','LEVELAUFSTIEG / ERFOLG','GESAMT-XP','NEUER SPIELER REGISTRIERT','SPIELER','MITGLIED'),
 'it': ('RANGO / IDENTITÀ','LIVELLO','MESSAGGI','TOP 10 / ESPERIENZA','TOP 10 / MESSAGGI','NESSUNA ATTIVITÀ','NUOVO LIVELLO / TRAGUARDO','XP TOTALI','NUOVO GIOCATORE REGISTRATO','GIOCATORE','MEMBRO'),
}

def preferred_language(user_id: int, locale=None) -> str:
    try:
        with sqlite3.connect(DB_PATH, timeout=15) as db:
            row = db.execute('SELECT language FROM user_languages WHERE user_id=?', (user_id,)).fetchone()
        if row and row[0] in LANGUAGES:
            return row[0]
    except sqlite3.Error:
        logging.exception('Could not read user language')
    return LOCALE_TO_LANGUAGE.get(str(locale or 'en').split('-')[0].lower(), 'en')

def tr(user_id, key, locale=None, **values):
    lang = preferred_language(user_id, locale)
    return TRANSLATIONS[lang].get(key, TRANSLATIONS['en'].get(key, key)).format(**values)

@bot.tree.command(name='language', description='Set your personal bot language / Configura tu idioma')
@app_commands.describe(language='Choose one of the six available languages')
@app_commands.choices(language=[app_commands.Choice(name=name, value=code) for code, name in LANGUAGES.items()])
async def language(interaction: discord.Interaction, language: app_commands.Choice[str]):
    with sqlite3.connect(DB_PATH, timeout=15) as db:
        db.execute('INSERT INTO user_languages (user_id, language) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET language=excluded.language', (interaction.user.id, language.value))
        db.commit()
    await interaction.response.send_message(tr(interaction.user.id, 'saved', interaction.locale, language=LANGUAGES[language.value]), ephemeral=True)

@bot.tree.command(name='my_language', description='Show your selected bot language')
async def my_language(interaction: discord.Interaction):
    code = preferred_language(interaction.user.id, interaction.locale)
    await interaction.response.send_message(tr(interaction.user.id, 'current', interaction.locale, language=LANGUAGES[code]), ephemeral=True)


class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Verify', emoji='✅', style=discord.ButtonStyle.success, custom_id='locked_legacy:verify:v1')
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(tr(interaction.user.id, 'server_only', interaction.locale), ephemeral=True)
            return
        role = discord.utils.get(interaction.guild.roles, name=VERIFIED_ROLE)
        if role is None:
            await interaction.response.send_message(tr(interaction.user.id, 'verify_missing', interaction.locale), ephemeral=True)
            return
        if role in interaction.user.roles:
            await interaction.response.send_message(tr(interaction.user.id, 'already_verified', interaction.locale), ephemeral=True)
            return
        try:
            await interaction.user.add_roles(role, reason='LOCKED LEGACY verification')
            await interaction.response.send_message(tr(interaction.user.id, 'verified', interaction.locale), ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(tr(interaction.user.id, 'verify_forbidden', interaction.locale), ephemeral=True)
        except discord.HTTPException:
            await interaction.response.send_message(tr(interaction.user.id, 'verify_error', interaction.locale), ephemeral=True)

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
            await interaction.response.send_message(tr(interaction.user.id, 'tickets_server', interaction.locale), ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY)
        if category is None:
            await interaction.followup.send(tr(interaction.user.id, 'ticket_missing', interaction.locale), ephemeral=True)
            return
        existing = next((c for c in category.text_channels if ticket_owner_id(c) == member.id), None)
        if existing:
            await interaction.followup.send(tr(interaction.user.id, 'ticket_existing', interaction.locale, channel=existing.mention), ephemeral=True)
            return
        if len(category.channels) >= 45:
            await interaction.followup.send(tr(interaction.user.id, 'ticket_full', interaction.locale), ephemeral=True)
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
                description=tr(member.id, 'ticket_greeting', interaction.locale, member=member.mention),
                colour=discord.Colour.from_rgb(145, 79, 230))
            await channel.send(embed=embed, view=TicketCloseView(),
                               allowed_mentions=discord.AllowedMentions(users=True))
            await interaction.followup.send(tr(interaction.user.id, 'ticket_created', interaction.locale, channel=channel.mention), ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(tr(interaction.user.id, 'ticket_forbidden', interaction.locale), ephemeral=True)
        except discord.HTTPException:
            logging.exception('Could not open ticket')
            await interaction.followup.send(tr(interaction.user.id, 'ticket_error', interaction.locale), ephemeral=True)


class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Close Ticket', emoji='🔒', style=discord.ButtonStyle.danger,
                       custom_id='locked_legacy:ticket_close:v1')
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        member = interaction.user
        if not isinstance(channel, discord.TextChannel) or not isinstance(member, discord.Member):
            await interaction.response.send_message(tr(interaction.user.id, 'ticket_only', interaction.locale), ephemeral=True)
            return
        owner_id = ticket_owner_id(channel)
        if owner_id is None or (member.id != owner_id and not is_ticket_staff(member)):
            await interaction.response.send_message(tr(interaction.user.id, 'ticket_not_owner', interaction.locale), ephemeral=True)
            return
        await interaction.response.send_message(tr(interaction.user.id, 'ticket_closing', interaction.locale), ephemeral=True)
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


def _welcome_card(avatar_bytes: bytes, player_name: str, member_number: int, lang: str = "en") -> io.BytesIO:
    """Generate a personalized, animated 8-frame Player ID GIF in a worker thread."""
    import math
    w, h = 900, 360
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert('RGB')
    avatar = ImageOps.fit(avatar, (208, 208), method=Image.Resampling.LANCZOS)
    mask = Image.new('L', (208, 208), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 207, 207), radius=28, fill=255)
    # Truncate based on rendered width, not only character count.
    safe_name = player_name.replace('\n', ' ').replace('\r', ' ')
    name_font = _font(30, True)
    while safe_name and ImageDraw.Draw(Image.new('RGB', (1, 1))).textbbox((0, 0), safe_name, font=name_font)[2] > 500:
        safe_name = safe_name[:-1]
    frames = []
    for frame_index in range(8):
        phase = frame_index / 8 * math.tau
        glow = int(35 + 25 * (1 + math.sin(phase)))
        im = Image.new('RGB', (w, h), (10, 8, 19))
        d = ImageDraw.Draw(im)
        # Background: manga-inspired geometry and violet neon stripes.
        d.polygon([(0, 0), (340, 0), (240, h), (0, h)], fill=(25, 15, 43))
        d.polygon([(780, 0), (w, 0), (w, h), (680, h)], fill=(35, 15, 58))
        for x in range(-100, w + 100, 65):
            d.line([(x, 0), (x - 170, h)], fill=(35, 21, 58), width=2)
        for y in range(12, h, 22):
            d.line((5, y, 45, y), fill=(110, 54, 168), width=2)
        d.rounded_rectangle((10, 10, w - 11, h - 11), radius=18,
                            outline=(135 + glow // 3, 55 + glow // 2, 190 + glow // 3), width=3)
        # Animated scanning beam traverses the card.
        scan_x = 30 + int(frame_index * (w - 60) / 7)
        for offset in range(-12, 13, 3):
            intensity = max(0, 70 - abs(offset) * 5)
            d.line((scan_x + offset, 16, scan_x + offset - 55, h - 17),
                   fill=(40 + intensity // 2, 20 + intensity // 3, 65 + intensity), width=2)
        # Avatar frame.
        d.rounded_rectangle((45, 70, 283, 309), radius=34, fill=(54, 28, 89),
                            outline=(165 + glow // 2, 75 + glow // 2, 230), width=5)
        im.paste(avatar, (60, 85), mask)
        d.text((47, 29), 'LOCKED', font=_font(24, True), fill=(255, 255, 255))
        d.text((167, 29), 'LEGACY', font=_font(24, True), fill=(188, 107, 255))
        d.text((318, 42), 'PLAYER ID  /  NEW RECRUIT', font=_font(18, True), fill=(191, 133, 255))
        d.text((315, 83), 'NEW PLAYER REGISTERED', font=_font(29, True), fill=(248, 243, 255))
        d.line((318, 130, 840, 130), fill=(137, 66, 208), width=3)
        d.text((318, 152), CARD_LABELS.get(lang, CARD_LABELS['en'])[9], font=_font(16, True), fill=(163, 140, 191))
        d.text((318, 177), safe_name or 'Player', font=name_font, fill=(255, 255, 255))
        d.text((318, 235), f"{CARD_LABELS.get(lang, CARD_LABELS['en'])[10]}  #{member_number:04d}", font=_font(22, True), fill=(200, 135, 255))
        d.text((318, 292), 'YOUR EGO. YOUR LEGACY. YOUR GAME.', font=_font(18, True), fill=(220, 207, 237))
        # Animated small progress indicator.
        for i in range(8):
            x = 650 + i * 24
            d.rounded_rectangle((x, 32, x + 17, 39), radius=3,
                                fill=(205, 126, 255) if i == frame_index else (67, 39, 99))
        frames.append(im)
    out = io.BytesIO()
    frames[0].save(out, format='GIF', save_all=True, append_images=frames[1:],
                   duration=160, loop=0, optimize=True, disposal=2)
    out.seek(0)
    return out


async def send_legacy_welcome(member: discord.Member, channel: discord.TextChannel):
    try:
        avatar_bytes = await member.display_avatar.replace(size=256,format='png').read()
        card = await asyncio.to_thread(_welcome_card, avatar_bytes, member.display_name, member.guild.member_count or 0, preferred_language(member.id, member.guild.preferred_locale))
        embed = discord.Embed(
            description=tr(member.id, 'welcome', member.guild.preferred_locale, member=member.mention, channel=VERIFY_CHANNEL),
            colour=discord.Colour.from_rgb(145, 79, 230)
        )
        embed.set_image(url='attachment://legacy_welcome.gif')
        embed.set_footer(text='LOCKED LEGACY • Official Community')
        await channel.send(embed=embed, file=discord.File(card,filename='legacy_welcome.gif'),
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
        await interaction.followup.send(tr(interaction.user.id, 'welcome_missing', interaction.locale), ephemeral=True)
        return
    await send_legacy_welcome(interaction.user, channel)
    await interaction.followup.send(tr(interaction.user.id, 'welcome_sent', interaction.locale, channel=channel.mention), ephemeral=True)


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
        await interaction.followup.send(tr(interaction.user.id, 'verify_ready', interaction.locale, channel=channel.mention), ephemeral=True)
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


# V5: explicit, conservative role permissions; never grant Administrator or Manage Roles.
ROLE_PERMISSIONS = {
    '🔨 Moderator': dict(manage_messages=True, moderate_members=True, kick_members=True, view_audit_log=True),
    '🏆 Tournament Host': dict(manage_events=True),
}
STAFF_NAMES = {'👑 Owner', '💻 Developer', '🛡️ Administrator', '🔨 Moderator'}
PUBLIC_CHANNELS = {'📜・rules', VERIFY_CHANNEL, WELCOME_CHANNEL}
READ_ONLY_CHANNELS = {'📜・rules', VERIFY_CHANNEL, WELCOME_CHANNEL,
                      '📢・announcements', '📰・updates', '🎁・codes', '🔗・links',
                      '📋・comp-rules', '📊・rankings', '📅・match-schedule', TICKET_CHANNEL}


def category_overwrites(guild, category_name):
    default = guild.default_role
    verified = discord.utils.get(guild.roles, name=VERIFIED_ROLE)
    rules = {default: discord.PermissionOverwrite(view_channel=False)}
    if category_name == '🔒 STAFF ONLY':
        for role in guild.roles:
            if role.name in STAFF_NAMES:
                rules[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True,
                    read_message_history=True)
    elif verified:
        rules[verified] = discord.PermissionOverwrite(view_channel=True,
            read_message_history=True, send_messages=True, connect=True, speak=True)
    return rules


def channel_overwrites(guild, category_name, channel_name):
    rules = category_overwrites(guild, category_name)
    default = guild.default_role
    verified = discord.utils.get(guild.roles, name=VERIFIED_ROLE)
    if channel_name in PUBLIC_CHANNELS:
        rules[default] = discord.PermissionOverwrite(view_channel=True,
            send_messages=False, read_message_history=True)
    if channel_name in READ_ONLY_CHANNELS and verified:
        rules[verified] = discord.PermissionOverwrite(view_channel=True,
            send_messages=False, read_message_history=True)
    # Moderators can post in announcements; non-staff verified users cannot.
    if channel_name in READ_ONLY_CHANNELS and channel_name not in PUBLIC_CHANNELS:
        for role in guild.roles:
            if role.name in STAFF_NAMES:
                rules[role] = discord.PermissionOverwrite(view_channel=True,
                    send_messages=True, read_message_history=True)
    return rules


async def apply_role_permissions(guild):
    updated = []
    for name, flags in ROLE_PERMISSIONS.items():
        role = discord.utils.get(guild.roles, name=name)
        if role and role < guild.me.top_role:
            perms = role.permissions
            changed = False
            for key, value in flags.items():
                if getattr(perms, key) != value:
                    setattr(perms, key, value)
                    changed = True
            if changed:
                await role.edit(permissions=perms, reason='LOCKED LEGACY V5 role permissions')
                updated.append(name)
    return updated


async def apply_channel_permissions(guild):
    categories_updated = channels_updated = 0
    for category_name, names in CATEGORIES.items():
        category = discord.utils.get(guild.categories, name=category_name)
        if category is None:
            category = await guild.create_category(category_name, reason='LOCKED V5 setup')
        await category.edit(overwrites=category_overwrites(guild, category_name),
                            reason='LOCKED LEGACY V5 permissions')
        categories_updated += 1
        for name in names:
            channel = discord.utils.get(category.text_channels, name=name)
            if channel is None:
                # Reuse a same-named channel already created by an older version.
                channel = discord.utils.get(guild.text_channels, name=name)
            if channel is None:
                channel = await guild.create_text_channel(name, category=category,
                    reason='LOCKED V5 setup')
            # Do not move existing channels between categories automatically.
            if channel.category_id == category.id:
                await channel.edit(overwrites=channel_overwrites(guild, category_name, name),
                    reason='LOCKED LEGACY V5 permissions')
                channels_updated += 1
    voice_category = discord.utils.get(guild.categories, name='🔊 VOICE CHANNELS')
    if voice_category is None:
        voice_category = await guild.create_category('🔊 VOICE CHANNELS', reason='LOCKED V5 setup')
    await voice_category.edit(overwrites=category_overwrites(guild, '🔊 VOICE CHANNELS'),
        reason='LOCKED V5 voice permissions')
    for name in VOICE:
        channel = discord.utils.get(voice_category.voice_channels, name=name)
        if channel is None:
            channel = discord.utils.get(guild.voice_channels, name=name)
        if channel is None:
            await guild.create_voice_channel(name, category=voice_category,
                reason='LOCKED V5 setup')
        elif channel.category_id == voice_category.id:
            await channel.edit(sync_permissions=True, reason='LOCKED V5 voice permissions')
    # Active tickets are intentionally untouched to preserve per-user privacy.
    return categories_updated + 1, channels_updated


@bot.tree.command(name='permissions_fix', description='Repair LOCKED LEGACY role and channel permissions')
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def permissions_fix(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)
    guild = interaction.guild
    if guild is None:
        await interaction.followup.send(tr(interaction.user.id, 'server_only', interaction.locale), ephemeral=True)
        return
    try:
        await ensure_legacy_roles(guild)
        updated = await apply_role_permissions(guild)
        categories, channels = await apply_channel_permissions(guild)
        await interaction.followup.send(
            f'✅ V5 permissions repaired: {categories} categories, {channels} text channels, '
            f'{len(updated)} staff roles updated. Active tickets were not modified. '
            'Check bot role hierarchy and test with a non-staff account.', ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send('❌ Bot needs Manage Channels and Manage Roles; its role must be above Moderator.', ephemeral=True)
    except discord.HTTPException as exc:
        logging.exception('Permissions fix failed')
        await interaction.followup.send(f'❌ Discord error: {exc}', ephemeral=True)


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


@bot.tree.command(name='setup', description='Create and configure LOCKED LEGACY channels and permissions')
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    await permissions_fix.callback(interaction)


# V8: Custom visual player ranks, top-ten and animated level-up cards.
def _card_base(width, height, heading, subtitle):
    im = Image.new('RGB', (width, height), (12, 9, 24))
    d = ImageDraw.Draw(im)
    d.polygon([(0, 0), (width // 2, 0), (width // 3, height), (0, height)], fill=(27, 15, 49))
    for x in range(0, width + height, 72):
        d.line((x, 0, x - height // 2, height), fill=(48, 26, 76), width=2)
    d.rounded_rectangle((13, 13, width - 14, height - 14), radius=22, outline=(163, 91, 236), width=3)
    d.text((42, 35), 'LOCKED', font=_font(31, True), fill='white')
    d.text((192, 35), 'LEGACY', font=_font(31, True), fill=(191, 126, 255))
    d.text((42, 91), heading, font=_font(26, True), fill=(229, 213, 255))
    d.text((42, height - 51), subtitle, font=_font(16), fill=(178, 150, 206))
    return im, d

def _short_text(draw, value, font, max_width):
    value = str(value).replace('\n', ' ').replace('\r', ' ')
    while value and draw.textbbox((0, 0), value, font=font)[2] > max_width:
        value = value[:-1]
    return value

def _paste_avatar(im, avatar_bytes, x, y, size):
    avatar = ImageOps.fit(Image.open(io.BytesIO(avatar_bytes)).convert('RGB'), (size, size))
    mask = Image.new('L', (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    im.paste(avatar, (x, y), mask)
    ImageDraw.Draw(im).ellipse((x - 3, y - 3, x + size + 2, y + size + 2), outline=(179, 103, 245), width=4)

def _rank_card(avatar_bytes, name, level, xp, messages, lang="en"):
    labels = CARD_LABELS.get(lang, CARD_LABELS['en'])
    im, d = _card_base(900, 365, labels[0], 'YOUR EGO. YOUR LEGACY. YOUR GAME.')
    _paste_avatar(im, avatar_bytes, 55, 144, 150)
    font = _font(32, True)
    d.text((245, 142), _short_text(d, name, font, 610), font=font, fill='white')
    d.text((245, 195), f'{labels[1]}  {level:03d}  /  100', font=_font(27, True), fill=(197, 129, 255))
    d.text((245, 241), f'{xp:,} XP    |    {messages:,} {labels[2]}', font=_font(20), fill=(226, 216, 239))
    if level < 100:
        low, high = 100 * level * level, 100 * (level + 1) ** 2
        progress = max(0, min(1, (xp - low) / (high - low)))
    else:
        progress = 1
    d.rounded_rectangle((245, 287, 836, 302), radius=7, fill=(53, 38, 72))
    if progress > 0:
        d.rounded_rectangle((245, 287, 245 + max(14, int(591 * progress)), 302), radius=7, fill=(168, 89, 240))
    out = io.BytesIO(); im.save(out, 'PNG'); out.seek(0); return out

def _top_card(entries, sort_by, lang="en"):
    labels = CARD_LABELS.get(lang, CARD_LABELS['en'])
    im, d = _card_base(900, 830, labels[3] if sort_by == 'xp' else labels[4], 'LOCKED LEGACY')
    for i, (name, xp, messages) in enumerate(entries):
        y = 140 + i * 62
        d.rounded_rectangle((40, y, 860, y + 55), radius=12, fill=(42, 26, 66) if i % 2 == 0 else (29, 21, 47))
        rank_color = [(255, 208, 102), (206, 210, 223), (218, 154, 113)][i] if i < 3 else (186, 132, 240)
        d.text((59, y + 12), f'#{i + 1:02}', font=_font(23, True), fill=rank_color)
        font = _font(21, True)
        d.text((146, y + 13), _short_text(d, name, font, 390), font=font, fill='white')
        stat = f'{xp:,} XP  ·  LV {level_from_xp(xp)}' if sort_by == 'xp' else f'{messages:,} MSG'
        d.text((590, y + 15), stat, font=_font(18, True), fill=(197, 139, 255))
    if not entries:
        d.text((90, 250), labels[5], font=_font(26, True), fill='white')
    out = io.BytesIO(); im.save(out, 'PNG'); out.seek(0); return out

def _levelup_card(avatar_bytes, name, level, xp, lang="en"):
    frames = []
    for i in range(8):
        labels = CARD_LABELS.get(lang, CARD_LABELS['en'])
        im, d = _card_base(900, 350, labels[6], 'LOCKED LEGACY')
        _paste_avatar(im, avatar_bytes, 56, 137, 146)
        font = _font(29, True)
        d.text((250, 144), _short_text(d, name, font, 590), font=font, fill='white')
        d.text((250, 204), f'{labels[1]} {level:03d}  /  100', font=_font(38, True), fill=(195 + i * 5, 105 + i * 8, 255))
        d.text((250, 262), f'{xp:,} {labels[7]}', font=_font(21), fill=(215, 197, 236))
        scan_x = 40 + i * 110
        d.line((scan_x, 16, scan_x - 65, 330), fill=(115, 61, 180), width=3)
        frames.append(im)
    out = io.BytesIO()
    frames[0].save(out, 'GIF', save_all=True, append_images=frames[1:], duration=160, loop=0, optimize=True)
    out.seek(0); return out


# --- LOCKED LEGACY V6: persistent XP and message leaderboard ---
# Railway: mount a persistent Volume at /data and set LEVELS_DB_PATH=/data/locked_levels.sqlite.
DB_PATH = os.getenv('LEVELS_DB_PATH', 'locked_levels.sqlite')
XP_COOLDOWN_SECONDS = 60
MAX_LEVEL = 100
LEVELS_LOCK = asyncio.Lock()

def init_levels_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH, timeout=15) as db:
        db.execute('''CREATE TABLE IF NOT EXISTS levels (
            guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
            xp INTEGER NOT NULL DEFAULT 0,
            messages INTEGER NOT NULL DEFAULT 0,
            last_xp_at REAL NOT NULL DEFAULT 0,
            PRIMARY KEY (guild_id, user_id))''')
        db.execute('''CREATE TABLE IF NOT EXISTS user_languages (user_id INTEGER PRIMARY KEY, language TEXT NOT NULL)''')
        db.commit()

def level_from_xp(xp: int) -> int:
    # Level 1 at 100 XP, level 2 at 400 XP, level 3 at 900 XP...
    return min(MAX_LEVEL, math.isqrt(max(0, xp) // 100))

@bot.event
async def on_message(message: discord.Message):
    if message.guild is None or message.author.bot or message.webhook_id is not None:
        return
    # No content inspection, so no privileged Message Content intent is needed.
    # Exclude staff-only channels, ticket channels and welcome/verification panels.
    if isinstance(message.channel, discord.TextChannel):
        if message.channel.category and message.channel.category.name in {'🔒 STAFF ONLY', TICKET_CATEGORY}:
            return
        if message.channel.name in {WELCOME_CHANNEL, VERIFY_CHANNEL, TICKET_CHANNEL}:
            return
    now = time.time()
    async with LEVELS_LOCK:
        try:
            with sqlite3.connect(DB_PATH, timeout=15) as db:
                db.execute('INSERT OR IGNORE INTO levels (guild_id, user_id) VALUES (?, ?)',
                           (message.guild.id, message.author.id))
                old_xp, old_count, last_xp_at = db.execute(
                    'SELECT xp, messages, last_xp_at FROM levels WHERE guild_id=? AND user_id=?',
                    (message.guild.id, message.author.id)).fetchone()
                gain = random.randint(15, 25) if now - last_xp_at >= XP_COOLDOWN_SECONDS else 0
                db.execute('UPDATE levels SET xp=?, messages=?, last_xp_at=? WHERE guild_id=? AND user_id=?',
                           (old_xp + gain, old_count + 1, now if gain else last_xp_at,
                            message.guild.id, message.author.id))
                db.commit()
        except sqlite3.Error:
            logging.exception('Failed to save leveling progress')
            return
    old_level, new_level = level_from_xp(old_xp), level_from_xp(old_xp + gain)
    if new_level > old_level:
        try:
            avatar_bytes = await message.author.display_avatar.replace(size=128, format='png').read()
            card = await asyncio.to_thread(_levelup_card, avatar_bytes, message.author.display_name, new_level, old_xp + gain, preferred_language(message.author.id, message.guild.preferred_locale))
            await message.channel.send(
                content=tr(message.author.id, 'levelup', message.guild.preferred_locale, member=message.author.mention, level=new_level),
                file=discord.File(card, filename='legacy_levelup.gif'),
                allowed_mentions=discord.AllowedMentions(users=True))
        except (discord.HTTPException, OSError, ValueError):
            logging.exception('Cannot post level-up card')
    await bot.process_commands(message)

@bot.tree.command(name='rank', description='See your LOCKED LEGACY level, XP and message count')
@app_commands.describe(member='Optional member to inspect')
async def rank(interaction: discord.Interaction, member: discord.Member | None = None):
    if interaction.guild is None:
        await interaction.response.send_message(tr(interaction.user.id, 'server_only', interaction.locale), ephemeral=True)
        return
    target = member or interaction.user
    try:
        with sqlite3.connect(DB_PATH, timeout=15) as db:
            result = db.execute('SELECT xp, messages FROM levels WHERE guild_id=? AND user_id=?',
                                (interaction.guild.id, target.id)).fetchone()
    except sqlite3.Error:
        await interaction.response.send_message(tr(interaction.user.id, 'db_error', interaction.locale), ephemeral=True)
        return
    xp, messages = result if result else (0, 0)
    level = level_from_xp(xp)
    needed = 100 * (level + 1) ** 2 if level < MAX_LEVEL else None
    await interaction.response.defer(thinking=True)
    try:
        avatar_bytes = await target.display_avatar.replace(size=128, format='png').read()
        card = await asyncio.to_thread(_rank_card, avatar_bytes, target.display_name, level, xp, messages, preferred_language(interaction.user.id, interaction.locale))
        await interaction.followup.send(file=discord.File(card, filename='legacy_rank.png'))
    except (discord.HTTPException, OSError, ValueError):
        logging.exception('Rank card failed')
        await interaction.followup.send(tr(interaction.user.id, 'rank_fallback', interaction.locale, member=target.mention, level=level, xp=xp, messages=messages))

async def _show_top(interaction: discord.Interaction, sort_by: str):
    if interaction.guild is None:
        await interaction.response.send_message(tr(interaction.user.id, 'server_only', interaction.locale), ephemeral=True)
        return
    # Sort field is internal, never user-controlled.
    sort_col = 'xp' if sort_by == 'xp' else 'messages'
    try:
        with sqlite3.connect(DB_PATH, timeout=15) as db:
            rows = db.execute(
                f'SELECT user_id, xp, messages FROM levels WHERE guild_id=? ORDER BY {sort_col} DESC, xp DESC LIMIT 100',
                (interaction.guild.id,)).fetchall()
    except sqlite3.Error:
        await interaction.response.send_message(tr(interaction.user.id, 'db_error', interaction.locale), ephemeral=True)
        return
    await interaction.response.defer(thinking=True)
    # Display stored members even when member cache is incomplete.
    current = rows[:10]
    entries = []
    for uid, xp, msgs in current:
        member = interaction.guild.get_member(uid)
        name = member.display_name if member else f'Player {str(uid)[-6:]}'
        entries.append((name, xp, msgs))
    try:
        card = await asyncio.to_thread(_top_card, entries, sort_by, preferred_language(interaction.user.id, interaction.locale))
        await interaction.followup.send(file=discord.File(card, filename='legacy_top10.png'))
    except (discord.HTTPException, OSError, ValueError):
        logging.exception('Top card failed')
        await interaction.followup.send(tr(interaction.user.id, 'top_error', interaction.locale))

@bot.tree.command(name='leaderboard', description='Top 10 LOCKED LEGACY players by XP')
async def leaderboard(interaction: discord.Interaction):
    await _show_top(interaction, 'xp')

@bot.tree.command(name='top_messages', description='Top 10 members by messages sent')
async def top_messages(interaction: discord.Interaction):
    await _show_top(interaction, 'messages')

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        message = tr(interaction.user.id, 'admin_only', interaction.locale)
    else:
        logging.error('Slash command failed: %r', error)
        message = tr(interaction.user.id, 'unexpected', interaction.locale)
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
