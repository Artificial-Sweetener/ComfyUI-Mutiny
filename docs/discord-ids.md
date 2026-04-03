# Discord Developer Mode, Guild ID, and Channel ID

Mutiny needs two Discord identifiers:

- **Guild ID**: the ID of the Discord server where you use the Midjourney bot
- **Channel ID**: the ID of the channel Mutiny should use inside that server

In other words, you want the server and channel where the **Midjourney bot is actually available to you and allowed to operate**.

To copy those, you first need to enable **Developer Mode** in Discord.

## 1. Turn on Developer Mode

In Discord, open **User Settings** by clicking the gear icon near the bottom left.

![Screenshot: Discord settings gear](./images/discord_1.webp)

Then go to:

- **Advanced**
- Turn **Developer Mode** on

![Screenshot: Discord Advanced menu item](./images/discord_2.webp)

![Screenshot: Discord Developer Mode toggle](./images/discord_3.webp)

## 2. Copy the Guild ID

Go to the Discord server you want Mutiny to use.

Right-click the server icon or server name and click **Copy Server ID**.

That value is your **Guild ID**.

![Screenshot: Right-click server -> Copy Server ID](./images/discord_4.webp)

## 3. Copy the Channel ID

Open the channel you want Mutiny to use inside that server.

Right-click the channel name and click **Copy Channel ID**.

That value is your **Channel ID**.

![Screenshot: Right-click channel -> Copy Channel ID](./images/discord_5.webp)

## Notes

- The Guild ID and Channel ID are safe to copy into Mutiny's settings.
- Your **Discord token** is different. It is sensitive account access material and should be handled much more carefully.
- If you choose to use Mutiny, you are responsible for figuring out how to obtain your own Discord token. Do not ask the maintainers for instructions or support on that.
- This guide only covers Developer Mode, Guild ID, and Channel ID.
