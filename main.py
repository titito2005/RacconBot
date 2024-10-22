import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import asyncio
import secrets
from openai import OpenAI
import random

intents = discord.Intents.default()
intents.message_content = True

client = OpenAI(
    api_key=secrets.OPENAI,
)

bot = commands.Bot(command_prefix='$', intents = intents)

alarms = []
infoChannel = []
messages = []

@bot.event
async def on_ready():
    print(f"Ready! {bot.user}")
    check_alarms.start()
    check_voice_channels.start()

@bot.command(name='ping', help="Command to check bot status.")
async def ping(ctx):
    await ctx.send(f"Pong!")

@bot.command(name='say_hello', help="The bot says hello!")
async def say_hello(ctx):
    user = ctx.author
    await ctx.send(f"Hi {user.name}!")

@bot.command(name='config', help="Set the bot to the established channel.")
async def config(ctx):
    guild = ctx.guild
    channel = ctx.channel
    await channel.send(f'Configured! {guild} {channel}')
    infoChannel.append((guild, channel))

@bot.command(name='set_alarm', help="Create an alarm. Parameters: [channel: str, time: str(HH:MM), daily: bool, message: str].")
async def set_alarm(ctx, channel: str, time: str, daily: bool, *, message: str):
    try:
        user = ctx.author
        alarm_time = datetime.strptime(time, '%H:%M')
        now = datetime.now()
        alarm_time = alarm_time.replace(year=now.year, month=now.month, day=now.day)

        if alarm_time < now:
            alarm_time += timedelta(days=1)

        alarms.append((user, alarm_time, channel, daily, message))
        await ctx.send(f'Alarm set to {time} on the channel {channel}.')
    except ValueError:
        await ctx.send('Incorrect time format. Use HH:MM in 24 hour format.')

# Loop to verify alarms
@tasks.loop(seconds=30)
async def check_alarms():
    now = datetime.now()
    for alarm in alarms:
        user, alarm_time, channel_name, daily, message = alarm
        if now >= alarm_time:
            channel = discord.utils.get(bot.guilds[0].channels, name=channel_name)
            if channel and isinstance(channel, discord.TextChannel):
                await channel.send(f'{user.mention}! {message}')
            if not daily:
                alarms.remove(alarm)

# Loop to send message if there is a person connected
@tasks.loop(seconds=900)
async def check_voice_channels():
    for guild in bot.guilds:
        for pair in infoChannel:
            if guild == pair[0]:
                for voice_channel in guild.voice_channels:
                    if len(voice_channel.members) == 1:
                        member = voice_channel.members[0]
                        channel = discord.utils.get(guild.channels, name=pair[1].name)
                        if channel and isinstance(channel, discord.TextChannel):
                            if channel.guild.me.guild_permissions.mention_everyone:
                                await channel.send(f'@everyone {member.mention} is waiting for you!')

# Event to know if a person enters or leaves a voice chat
@bot.event
async def on_voice_state_update(member, before, after):
    guild = member.guild
    for pair in infoChannel:
        if guild == pair[0]:
            if before.channel is None and after.channel is not None:
                channel = after.channel
                await channel.send(f'¡Hi {member.mention}! You have entered the voice channel {channel.name}!')

            elif before.channel is not None and after.channel is None:
                channel = before.channel
                await channel.send(f'¡Bye {member.mention}! You have left the voice channel {channel.name}!')

@bot.command(name='joke', help='Send a joke. Parameters: [topic: str].')
async def joke(ctx, *, topic: str):
    try:
        messages.append({"role": "user", "content": f'Chiste sobre {topic}. Corto.'})

        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7
        )
        answer = completion.choices[0].message.content 
        messages.append({"role": "assistant", "content": answer})

        await ctx.send(answer)
    except Exception as e:
        await ctx.send(f'An error occurred: {e}')

@bot.command(name='purge_ai', help='Delete all AI context.')
async def purge_ai(ctx):
    messages.clear()
    await ctx.send(f'Deleted message history!')

@bot.command(name='purge', help='Delete all channel messages.')
@commands.has_permissions(manage_messages=True)
async def purge(ctx):
    try:
        while True:
            deleted = await ctx.channel.purge(limit=5)
            if len(deleted) == 0:
                break
            await asyncio.sleep(5)
    except discord.HTTPException as e:
        print(f"An error occurred: {e}")

class MyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.choices = ["rock", "paper", "scissors"]

    def play(self, player_choice):
        bot_choice = random.choice(self.choices)
        if player_choice == bot_choice:
            return f"Both chose **{player_choice}**. It's a tie!"
        
        if (player_choice == "rock" and bot_choice == "scissors") or \
           (player_choice == "scissors" and bot_choice == "paper") or \
           (player_choice == "paper" and bot_choice == "rock"):
            return f"You choose **{player_choice}** and the bot chooses **{bot_choice}**. You won!"
        else:
            return f"You choose **{player_choice}** and the bot chooses **{bot_choice}**. You lost!"
        
    @discord.ui.button(label="rock", style=discord.ButtonStyle.primary)
    async def rockButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.channel.send(self.play('rock'))
            await interaction.response.edit_message(content="Thanks for playing!", view=None)
            self.stop()
        except discord.HTTPException as e:
            await interaction.channel.send(f"It seems there was a problem with this interaction. I'm sorry! Try again later.")

    @discord.ui.button(label="paper", style=discord.ButtonStyle.secondary)
    async def paperButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.channel.send(self.play('paper'))
            await interaction.response.edit_message(content="Thanks for playing!", view=None)
            self.stop()
        except discord.HTTPException as e:
            await interaction.channel.send(f"It seems there was a problem with this interaction. I'm sorry! Try again later.")


    @discord.ui.button(label="scissors", style=discord.ButtonStyle.success)
    async def scissorsButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.channel.send(self.play('scissors'))
            await interaction.response.edit_message(content="Thanks for playing!", view=None)
            self.stop()
        except discord.HTTPException as e:
            await interaction.channel.send(f"It seems there was a problem with this interaction. I'm sorry! Try again later.")
        
@bot.command(name='play', help='Play Rock, Paper or Scissors!')
async def play(ctx: commands.Context):
    view = MyView()
    await ctx.send("Rock, Paper or Scissors!", view=view)

@bot.command(name='commands', help='Lists all available commands.')
async def commands(ctx):
    command_list = "Available commands:\n"
    for command in bot.commands:
        command_list += f"${command.name}: {command.help or 'No description'}\n"
    await ctx.send(command_list)

bot.run(secrets.TOKEN)