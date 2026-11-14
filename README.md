# LOCKED LEGACY BOT

Python Discord bot for the LOCKED: LEGACY community.

## Railway
- Set `DISCORD_TOKEN` (secret) and `DISCORD_GUILD_ID` (server ID) in Variables.
- Start command: `python bot.py`
- Enable **Server Members Intent** in Discord Developer Portal > Bot.
- Bot needs Manage Roles, Manage Channels, View Channels, Send Messages, Read Message History, Embed Links. Place bot role above `✅ Verified`.
- Deploy and run `/setup` then `/verification_setup` in your Discord server.
- Do not commit the token to GitHub.

**Note:** `/setup` creates roles and channels, and changes channel permissions. Test in a spare server first. For existing channels it may change access. It does not delete channels.
