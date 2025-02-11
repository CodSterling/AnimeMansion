import discord
import asyncio
from discord.ext import commands
import random
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TOKEN')
ESCAPE_CHANNEL_ID = int(os.getenv('ESCAPE_CHANNEL_ID'))
AUDIO_PATH = os.getenv('AUDIO_PATH', './audio/')  # Default to local folder if not set
IMG_PATH = os.getenv('IMG_PATH', './img/')  # Default to local folder if not set
FFMPEG_PATH = os.getenv('FFMPEG_PATH', '/app/vendor/ffmpeg/ffmpeg')  # Default for Heroku buildpack
# FFMPEG_PATH = os.getenv('./audio/', 'ffmpeg')  # Uses system FFmpeg by default


intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.guild_messages = True
intents.voice_states = True
intents.message_content = True
intents.members = True
intents.reactions = True


bot = commands.Bot(command_prefix='.', intents=intents)

# Store active games
active_games = {}

# Define artifacts, weapons, shields, and special items
artifacts = {"Mansion Key": "Opens secret rooms", "Love Potion": "Causes a charming effect, can alter interactions"}
weapons = {"Elegant Fan": "Effective against Playful Maid", "Silver Dagger": "Effective against Mysterious Lady", "Moonlit Katana": "Effective against Shadow Princess"}
shields = {"Silk Scarf": "Blocks Playful Maid's charm", "Golden Bracelet": "Blocks Mysterious Lady's hex", "Enchanted Cloak": "Blocks Shadow Princess's dark magic"}
secret_items = {"Lock of Silver Hair": "A rare relic of a mysterious resident", "Ancient Diary": "Contains forgotten mansion secrets", "Porcelain Doll": "A mystical charm with unknown powers"}

# Track the currently playing audio
current_audio_task = None

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')


async def play_audio(ctx, filename):
    game_data = active_games.get(ctx.author.id)
    if not game_data:
        await ctx.send("You're not in a game session!")
        return

    voice_client = game_data.get('voice_client')

    if voice_client and voice_client.is_connected():
        if voice_client.is_playing():
            voice_client.stop()  # Stop current audio before playing a new one

        source = discord.FFmpegPCMAudio(os.path.join(AUDIO_PATH, filename), executable=FFMPEG_PATH)

        voice_client.play(source)
    else:
        await ctx.send("Bot is not connected to a voice channel.")


async def send_embed(ctx, title, description, image):
    embed = discord.Embed(title=title, description=description, color=discord.Color.gold())
    embed.set_image(url=f"attachment://{image}")
    file = discord.File(os.path.join(IMG_PATH, image), filename=image)
    await ctx.send(embed=embed, file=file)


@bot.command(name="start")
async def start(ctx):
    guild = ctx.guild
    category = discord.utils.get(guild.categories, name="Anime Mansion")
    if not category:
        category = await guild.create_category("Anime Mansion")

    voice_channel = await guild.create_voice_channel(f"{ctx.author.name}", category=category)
    text_channel = await guild.create_text_channel(f"{ctx.author.name}", category=category)

    active_games[ctx.author.id] = {
        'voice_channel': voice_channel,
        'text_channel': text_channel,
        'health': 100,
        'coins': 0,
        'inventory': []
    }

    voice_client = await voice_channel.connect()
    active_games[ctx.author.id]['voice_client'] = voice_client

    await send_embed(ctx, "Welcome to the Mansion!\n\n"
                          "Collect 100 coins and use `.door` to leave the MANSION!\n\n"
                          "There are nice and mean ANIME GIRLS so be prepared to fight!",
                            "Use `.move` to start exploring!\n\n"
                            "Use `.menu` for the GAME MENU", "mansion.jpg")
    await ctx.send(
        f"{ctx.author.mention}, your game has started! Join {voice_channel.mention} and use {text_channel.mention} to play.")
    await play_audio(ctx, "start.mp3")


async def decrement_item_uses(ctx, item):
    game_data = active_games[ctx.author.id]
    if 'item_uses' not in game_data:
        game_data['item_uses'] = {}

    if item in game_data['inventory']:
        game_data['item_uses'][item] = game_data['item_uses'].get(item, 2) - 1
        if game_data['item_uses'][item] <= 0:
            game_data['inventory'].remove(item)
            del game_data['item_uses'][item]
            await ctx.send(f"Your **{item}** has broken and is removed from your inventory!")


@bot.command()
async def move(ctx):
    if ctx.author.id not in active_games:
        await ctx.send("You're not in a game! Use `!start` first.")
        return

    paths = ["left", "right", "forward"]
    encounter_options = [
        ("anime_girl", 15),
        ("random_girl", 25),
        ("treasure", 10),
        ("health", 10),
        ("artifact", 8),
        ("weapon", 5),
        ("shield", 5),
        ("hallway", 9),
        ("room", 9),
        ("corridor", 9),
        ("darkpath", 9)
    ]
    encounters, weights = zip(*encounter_options)
    encounter = random.choices(encounters, weights)[0]

    game_data = active_games[ctx.author.id]
    voice_client = game_data.get('voice_client')

    if encounter == "anime_girl":
        anime_girls = ["Playful Maid", "Mysterious Lady", "Shadow Princess"]
        chosen_girl = random.choice(anime_girls)
        power_level = {"Playful Maid": "Charming", "Mysterious Lady": "Cunning", "Shadow Princess": "Dangerous"}
        audio_file = \
        {"Playful Maid": "maid.mp3", "Mysterious Lady": "mystery.mp3", "Shadow Princess": "shadow.mp3"}[
            chosen_girl]
        image_file = \
        {"Playful Maid": "maid2.jpg", "Mysterious Lady": "mystery2.jpg", "Shadow Princess": "shadow2.jpg"}[
            chosen_girl]
        game_data['current_enemy'] = chosen_girl

        await send_embed(ctx, f"Encounter! {chosen_girl}", f"Power Level: {power_level[chosen_girl]}",
                         image_file)
        await play_audio(ctx, audio_file)

        await asyncio.sleep(2)  # Wait for 2 seconds before battle sequence

        girl_weakness = {"Playful Maid": "Elegant Fan", "Mysterious Lady": "Silver Dagger",
                         "Shadow Princess": "Moonlit Katana"}
        girl_defense = {"Playful Maid": "Silk Scarf", "Mysterious Lady": "Golden Bracelet",
                        "Shadow Princess": "Enchanted Cloak"}

        took_damage = True  # Assume the player takes damage by default
        for item in [girl_weakness.get(chosen_girl), girl_defense.get(chosen_girl)]:
            if item in game_data['inventory']:
                await decrement_item_uses(ctx, item)
                took_damage = False  # Player is protected
                break

        if took_damage:
            damage_taken = random.randint(10, 25)
            game_data['health'] -= damage_taken
            await send_embed(ctx, f"Battle Result! {chosen_girl}",
                             f"You lack the right gear and take {damage_taken} damage!", "defeat.jpg")
        else:
            await send_embed(ctx, f"Battle Result! {chosen_girl}", "You are well-equipped and take no damage!",
                             "sword.jpg")


    elif encounter == "hallway":
        await send_embed(ctx, "You found a hallway!", "A long corridor stretches ahead.", "hallway2.jpg")
        await play_audio(ctx, "hallway.mp3")
    elif encounter == "room":
        await send_embed(ctx, "You discovered a room!", "A mysterious chamber filled with unknown relics.", "room2.jpg")
        await play_audio(ctx, "room.mp3")
    elif encounter == "corridor":
        await send_embed(ctx, "You entered a corridor!", "The path twists and turns, leading into darkness.",
                         "corridor2.jpg")
        await play_audio(ctx, "corridor.mp3")
    elif encounter == "darkpath":
        await send_embed(ctx, "You found a dark path!", "The air grows cold as shadows loom ahead.", "darkpath2.jpg")
        await play_audio(ctx, "darkpath.mp3")
    elif encounter == "treasure":
        coins_found = random.randint(5, 15)
        game_data['coins'] += coins_found
        await send_embed(ctx, "You found coins!", f"You found {coins_found} coins!", "coin2.jpg")
        await play_audio(ctx, "coin.mp3")
    elif encounter == "health":
        health_gained = random.randint(10, 20)
        game_data['health'] += health_gained
        await send_embed(ctx, "Health Potion Found!", f"(+{health_gained} HP)", "health2.jpg")
        await play_audio(ctx, "health.mp3")
    elif encounter == "artifact":
        artifact = random.choice(list(artifacts.keys()))
        if artifact not in game_data['inventory']:
            game_data['inventory'].append(artifact)
            image_file = "mushroom.jpg" if artifact == "Mystic Mushroom" else "artifact.jpg"
            await send_embed(ctx, "Artifact Found!", f"You found an **{artifact}**! {artifacts[artifact]}", image_file)
            await play_audio(ctx, "mushroom.mp3" if artifact == "Mystic Mushroom" else "artifact.mp3")
    elif encounter == "weapon":
        weapon = random.choice(list(weapons.keys()))
        if weapon not in game_data['inventory']:
            game_data['inventory'].append(weapon)
            await send_embed(ctx, "Weapon Found!", f"You found a **{weapon}**! {weapons[weapon]}", "sword.jpg")
            await play_audio(ctx, "sword.mp3")
    elif encounter == "shield":
        shield = random.choice(list(shields.keys()))
        if shield not in game_data['inventory']:
            game_data['inventory'].append(shield)
            await send_embed(ctx, "Shield Found!", f"You found a **{shield}**! {shields[shield]}", "shield.jpg")
            await play_audio(ctx, "shield.mp3")

    elif encounter == "random_girl":
        random_girls = ["Yukari Hoshino", "Akane Fujimura", "Mitsuki Aoyama", "Rin Tsukishiro", "Sayaka Kisaragi"]
        chosen_girl = random.choice(random_girls)
        power_level = {"Yukari Hoshino": "Elegant and mysterious", "Akane Fujimura": "Fiery and strong-willed",
                       "Mitsuki Aoyama": "Cool and calculating",
                       "Rin Tsukishiro": "Playful yet deceptive", "Sayaka Kisaragi": "Charming but unpredictable"}
        audio_file = \
        {"Yukari Hoshino": "girl1.mp3", "Akane Fujimura": "girl2.mp3",
                       "Mitsuki Aoyama": "girl3.mp3",
                       "Rin Tsukishiro": "girl4.mp3", "Sayaka Kisaragi": "girl5.mp3"}[
            chosen_girl]
        image_file = \
        {"Yukari Hoshino": "girl1.jpg", "Akane Fujimura": "girl2.jpg",
                       "Mitsuki Aoyama": "girl3.jpg",
                       "Rin Tsukishiro": "girl4.jpg", "Sayaka Kisaragi": "girl5.jpg"}[
            chosen_girl]
        game_data['current_enemy'] = chosen_girl

        await send_embed(ctx, f"Encounter! {chosen_girl}", f"Power Level: {power_level[chosen_girl]}",
                         image_file)
        await play_audio(ctx, audio_file)
    else:
        await ctx.send(f"The path is empty. Choose another move.")


@bot.command()
async def door(ctx):
    if ctx.author.id not in active_games:
        await ctx.send("You're not in a game! Use `.start` first.")
        return

    game_data = active_games[ctx.author.id]
    if game_data['coins'] >= 100:
        escape_channel = bot.get_channel(ESCAPE_CHANNEL_ID)
        if escape_channel:
            await send_embed(ctx, "ESCAPED!", "You have found the exit and escaped the Mansion!", "mansion.jpg")
            voice_client = game_data.get('voice_client')
            if voice_client and voice_client.is_connected():
                await play_audio(ctx, "escaped.mp3")
            await escape_channel.send(f"{ctx.author.mention} has successfully escaped the Minotaur Maze!")
        else:
            await ctx.send("Escape channel is not set. Please provide the correct channel ID.")
    else:
        await ctx.send(
            f"You need 100 coins to escape. You currently have {game_data['coins']} coins.")


@bot.command()
async def health(ctx):
    if ctx.author.id not in active_games:
        await ctx.send("You're not in a game! Use `!start` first.")
        return

    health_value = active_games[ctx.author.id]['health']
    await send_embed(ctx, "Health Status", f"Your current health is: {health_value} HP", "health2.jpg")


@bot.command(name="unlock")
async def secret_room(ctx):
    if ctx.author.id not in active_games:
        await ctx.send("You're not in a game! Use `!start` first.")
        return

    if "Mansion Key" in active_games[ctx.author.id]['inventory']:
        secret_item = random.choice(list(secret_items.keys()))
        active_games[ctx.author.id]['inventory'].append(secret_item)
        await send_embed(ctx, "Secret Room Discovered!",
                         f"You have unlocked a secret room and found a **{secret_item}**! {secret_items[secret_item]}",
                         "unlock.jpg")
        await play_audio(ctx, "unlock.mp3")
    else:
        await ctx.send("You need the Mansion Key to access the secret room!")


@bot.command()
async def inventory(ctx):
    if ctx.author.id not in active_games:
        await ctx.send("You're not in a game! Use `!start` first.")
        return

    game_data = active_games[ctx.author.id]
    health = game_data['health']
    coins = game_data['coins']
    inventory_items = game_data['inventory']

    inventory_details = "\n".join(
        f"**{item}** - {artifacts.get(item, weapons.get(item, shields.get(item, secret_items.get(item, 'No description available'))))}"
        for item in inventory_items
    ) if inventory_items else "No items"

    embed = discord.Embed(title="Inventory Check",
                          description=f"**Health:** {health} HP\n**Coins:** {coins}\n\n**Items:**\n{inventory_details}",
                          color=discord.Color.green())
    await ctx.send(embed=embed)


@bot.command()
async def menu(ctx):
    embed = discord.Embed(title="Mansion Commands", description="Here are the available commands:", color=discord.Color.blue())
    embed.add_field(name=".start", value="Starts a new game session.", inline=False)
    embed.add_field(name=".move", value="Move in the maze and encounter events.", inline=False)
    embed.add_field(name=".health", value="Check your current health level.", inline=False)
    embed.add_field(name=".inventory", value="Check your current inventory.", inline=False)
    embed.add_field(name=".door", value="Check if you have 100 coins to escape.", inline=False)
    embed.add_field(name=".unlock", value="Opens a SPECIAL ROOM!", inline=False)
    embed.add_field(name=".end", value="End your session and delete the game channels.", inline=False)
    embed.set_footer(text="Good luck navigating the Mansion!")
    await ctx.send(embed=embed)


@bot.command()
async def collect(ctx):
    if ctx.author.id not in active_games:
        await ctx.send("You're not in a game! Use `!start` first.")
        return

    game_data = active_games[ctx.author.id]
    game_data['coins'] += 100
    if "Mansion Key" not in game_data['inventory']:
        game_data['inventory'].append("Mansion Key")

    await ctx.send("You have collected 100 coins and received a Mansion Key!")


@bot.command()
async def end(ctx):
    if ctx.author.id not in active_games:
        await ctx.send("You're not in a game!")
        return

    game_data = active_games.pop(ctx.author.id)
    await send_embed(ctx, "Game Over!", "Your adventure has ended.", "mansion.jpg")

    for channel in ctx.guild.channels:
        if channel.name.endswith(f"{ctx.author.name}") or channel.name.startswith(f"{ctx.author.name}"):
            await channel.delete()

    vc = discord.utils.get(ctx.guild.voice_channels, name=f"{ctx.author.name}'s Mansion")
    if vc:
        await play_audio(vc, "escaped.mp3")

bot.run(TOKEN)

