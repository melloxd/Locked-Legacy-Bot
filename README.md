# LOCKED LEGACY BOT — Purple Welcome, Roles & Tickets

## Install
1. Upload `bot.py` and `requirements.txt` to the root of your GitHub repository.
2. In Railway set `DISCORD_TOKEN` and `DISCORD_GUILD_ID` (never commit the token).
3. Set the Railway start command to `python bot.py`.
4. In Discord Developer Portal > Bot enable **Server Members Intent**.
5. Grant the bot Manage Channels, Manage Roles, Send Messages, View Channels and Read Message History. Put its role above `✅ Verified`.
6. Deploy on Railway. Check logs for synchronized slash commands.

## Commands (administrator only)
- `/setup`: Create categories, channels and decorative roles.
- `/roles_setup`: Create missing roles without privileged permissions.
- `/verification_setup`: Post persistent verification button.
- `/welcome_test`: Preview the purple welcome card.
- `/tickets_setup`: Post a persistent ticket panel in `🎟️・open-ticket`.

## Tickets
Verified users can click **Open Ticket**. A private `ticket-USER_ID` channel is created under `🎫 ACTIVE TICKETS`. The opener and staff with roles `👑 Owner`, `🛡️ Administrator`, or `🔨 Moderator` can read it. Only the ticket owner or those staff can press **Close Ticket**, which **permanently deletes** the channel. There is no transcript or ticket database. Each user can have one open ticket at a time; category limit 45 channels. Staff roles must be assigned manually. Do not use this system for sensitive information.

**Important:** `/setup` modifies channel permissions; test on a test server before using it on a populated community. `/tickets_setup` only changes the ticket panel channel permissions and creates the ticket category if absent.
