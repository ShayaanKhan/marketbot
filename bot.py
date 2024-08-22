import discord
import requests
from dotenv import load_dotenv
import os
import json
import urllib.parse
import webserver

# Load the bot token from the .env file
load_dotenv()
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("No token provided. Please set the DISCORD_BOT_TOKEN environment variable.")

# File to store the channel IDs for each server
CHANNELS_FILE = 'allowed_channels.json'

# Set up intents
intents = discord.Intents.default()
intents.message_content = True  # This allows the bot to read message content

client = discord.Client(intents=intents)

# Load allowed channels from file
if os.path.exists(CHANNELS_FILE):
    with open(CHANNELS_FILE, 'r') as f:
        allowed_channels = json.load(f)
else:
    allowed_channels = {}

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    guild_id = str(message.guild.id)

    # Command to set the allowed channel
    if message.content.startswith('-setchannel'):
        if message.author.guild_permissions.administrator:
            allowed_channels[guild_id] = message.channel.id
            with open(CHANNELS_FILE, 'w') as f:
                json.dump(allowed_channels, f)
            await message.channel.send(f'Channel {message.channel.name} has been set for bot commands.')
        else:
            await message.channel.send('You do not have permission to set the channel.')

    # Check if the message is in the allowed channel
    if guild_id in allowed_channels and message.channel.id != allowed_channels[guild_id]:
        return  # Ignore the message if it's not in the designated channel

    # Command to display help information
    if message.content.startswith('-help'):
        help_text = (
            "Welcome to the Warframe Market Bot! Here are the commands you can use:\n\n"
            "**-setchannel**\n"
            "  - Sets the channel for bot commands in this server.\n\n"
            "**-price <item_name>**\n"
            "  - Queries the price of an item on the Warframe market.\n"
            "  - **item_name** is the name of the item (e.g., `Rhino Prime Set`, `Soma Prime`, `Primed Bane of Grineer`).\n\n"
            "Examples:\n"
            "  - `-price Rhino Prime Set`\n"
            "  - `-price Soma Prime`\n"
            "  - `-price Primed Bane of Grineer`\n"
        )
        await message.channel.send(help_text)

    # Handle price inquiries
    if message.content.startswith('-price'):
        item_name = message.content[len('-price '):].strip().lower()

        if not item_name:
            await message.channel.send('Please specify the item name.')
            return

        # Construct the API request URL
        item_name_encoded = urllib.parse.quote(item_name.replace(" ", "_"))
        api_url = f'https://api.warframe.market/v1/items/{item_name_encoded}/orders'

        try:
            response = requests.get(api_url)
            response.raise_for_status()  # Raises an error for bad HTTP status codes

            data = response.json()
            orders = data['payload']['orders']
            wtb_orders = [order for order in orders if order['order_type'] == 'buy']
            wts_orders = [order for order in orders if order['order_type'] == 'sell']

            wtb_price = wtb_orders[0]['platinum'] if wtb_orders else 'No buy orders found'
            wts_price = wts_orders[0]['platinum'] if wts_orders else 'No sell orders found'

            await message.channel.send(f'{item_name.replace("_", " ").title()} WTB: {wtb_price}p, WTS: {wts_price}p')

        except requests.exceptions.RequestException as e:
            await message.channel.send(f'Error fetching data for {item_name.replace("_", " ").title()}: {str(e)}')

        except KeyError:
            await message.channel.send(f'Item {item_name.replace("_", " ").title()} not found.')

webserver.keep_alive()
client.run(TOKEN)
