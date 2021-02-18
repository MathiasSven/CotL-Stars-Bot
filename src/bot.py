import asyncio
import os
import re
import sys

import discord
from discord.ext import commands
from discord.ext.commands import has_permissions
from discord.ext.commands import errors
import configparser

directory = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(1, os.path.dirname(directory))

import tortoise
from src.models import Star, Recipient

config = configparser.ConfigParser()
config.read(f"{os.path.join(directory, os.pardir)}/config.ini")

activity = discord.Activity(name='the Stars', type=discord.ActivityType.watching)


class Bot(commands.Bot):

    def __init__(self):
        super().__init__(command_prefix=config.get("settings", "PREFIX"))
        self.remove_command('help')
        self.loop.run_until_complete(start_database())

    async def on_ready(self):
        await self.change_presence(activity=activity)
        print(f"{self.__class__.__name__} is Ready!")

    def run_bot(self):
        self.run(config.get("settings", "TOKEN"))


class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.COLOUR = int(config.get("settings", "COLOUR"), 16)
        self.ERROR_COLOUR = int(config.get("settings", "ERROR_COLOUR"), 16)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'{__class__.__name__} Cog is loaded')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        async def error_embed(error_message):
            embed_dict = {'color': discord.Colour(self.ERROR_COLOUR).value, 'type': 'rich', 'description': f"**{error_message}**"}
            await ctx.send(embed=discord.Embed.from_dict(embed_dict))

        if isinstance(error, errors.MissingPermissions):
            await error_embed("You must have the `Manage Server` permission to run this command.")
        elif isinstance(error, errors.BadArgument):
            await error_embed("<star_id> must be an integer.")
        else:
            await error_embed(error.original)

    @commands.Cog.listener('on_message')
    async def mention_help(self, message):
        if self.bot.user in message.mentions:
            await self.help(commands.Context(message=message, prefix="", kwargs={"delete": False}))

    @commands.command()
    async def help(self, ctx):
        """
        shows helpful information
        """
        if not bool(ctx.kwargs):
            await asyncio.sleep(0.5)
            await ctx.message.delete()
        else:
            pass
        embed = discord.Embed(title="CotL Stars Commands:",
                              description=f"```ini\n"
                                          f"{self.bot.command_prefix}help - shows helpful information\n"
                                          f"{self.bot.command_prefix}leaderboard - lists members and a count of their stars\n"
                                          f"{self.bot.command_prefix}list <@Member> - lists a member's stars\n"
                                          f"{self.bot.command_prefix}count <@Member> - counts a member's stars\n"
                                          f"{self.bot.command_prefix}add <@Member> <message> - adds a star to a member\n"
                                          f"{self.bot.command_prefix}delete <star_id> - deletes a star, find the star_id via the list command```",
                              colour=discord.Colour(self.COLOUR))
        await ctx.send(embed=embed)

    @commands.command()
    async def leaderboard(self, ctx):
        """
        lists members and a count of their stars
        """
        await asyncio.sleep(0.5)
        await ctx.message.delete()
        stars_count = await Star.all().count()
        recipients = await Recipient.all().order_by("-star_count")
        leaderboard_str = ""
        if stars_count == 0:
            leaderboard_str = "No stars found."
        else:
            for recipient in recipients:
                stars_amount = recipient.star_count
                if stars_amount == 0:
                    continue
                leaderboard_str += f"<@{recipient.id}>: {stars_amount} Star{'s' if stars_amount >= 2 else ''}\n"

        embed = discord.Embed(description=f"**⭐ Star Leaderboard**\n"
                                          f"\n"
                                          f"{leaderboard_str}", colour=discord.Colour(self.COLOUR))
        await ctx.send(embed=embed)

    @commands.command()
    async def list(self, ctx, member=""):
        """
        lists a member's stars
        """
        await asyncio.sleep(0.5)
        await ctx.message.delete()
        regex = re.compile(r'^<@!?(?P<id>\d*)>$')
        regex_match = regex.match(member)
        if regex_match is not None:
            user_id = regex_match.group("id")
            var_ = member
            member = await Recipient.get_or_none(id=user_id)

            if member is None:
                member = type('_', (object,), {'star_count': 0, 'mention': var_})()

            if member.star_count == 0:
                embed = discord.Embed(description=f"**{member.mention} has no stars.**", colour=discord.Colour(self.COLOUR))
                await ctx.send(embed=embed)
                return

            stars_str = ""

            await member.fetch_related('star')
            for star in member.star:
                reason = ""
                if star.reason:
                    reason = f": {star.reason}"
                stars_str += f"(#{star.id}) From <@{star.presenter_id}> on {star.timestamp.date().strftime('%m/%d/%Y')}{reason}\n"

            embed = discord.Embed(description=f"**Showing the Latest {member.star_count} Stars for {member.mention()}**\n"
                                              f"\n"
                                              f"{stars_str}", colour=discord.Colour(self.COLOUR))
            await ctx.send(embed=embed)
        else:
            raise errors.CommandInvokeError(e="Invalid member argument.")

    @commands.command()
    async def count(self, ctx, member):
        """
        counts a member's stars
        """
        await asyncio.sleep(0.5)
        await ctx.message.delete()
        regex = re.compile(r'^<@!?(?P<id>\d*)>$')
        regex_match = regex.match(member)
        if regex_match is not None:
            user_id = regex_match.group("id")
            member = await Recipient.get(id=user_id)
            if member.star_count == 0:
                embed = discord.Embed(description=f"**{member.mention()} has no stars.**", colour=discord.Colour(self.COLOUR))
            else:
                embed = discord.Embed(description=f"**{member.mention()} has {member.star_count} star{'s' if member.star_count >= 2 else ''}.**",
                                      colour=discord.Colour(self.COLOUR))

            await ctx.send(embed=embed)

        else:
            raise errors.CommandInvokeError(e="Invalid member argument.")

    @commands.command()
    @has_permissions(manage_guild=True)
    async def add(self, ctx, member, *, reason=""):
        """
        adds a star to a member
        """
        # await asyncio.sleep(0.5)
        # await ctx.message.delete()
        regex = re.compile(r'^<@!?(?P<id>\d*)>$')
        regex_match = regex.match(member)
        if regex_match is not None:
            user_id = regex_match.group("id")
            if len(reason) > 64:
                raise errors.CommandInvokeError(e="Reason given surpasses 64 characters.")
            recipient, _ = await Recipient.get_or_create(id=user_id)
            await Star.create(recipient=recipient, presenter_id=ctx.message.author.id, reason=reason)
            await ctx.send(f"{ctx.message.author.mention}, star added.")
        else:
            raise errors.CommandInvokeError(e="Invalid member argument.")

    @commands.command()
    @has_permissions(manage_guild=True)
    async def delete(self, ctx, star_id: int):
        """
        deletes a star, find the star_id via the list command
        """
        # await asyncio.sleep(0.5)
        # await ctx.message.delete()
        star = await Star.get_or_none(id=star_id)
        if star is not None:
            await star.delete()
            await ctx.send(f"{ctx.message.author.mention}, star #{star.id} for {await star.recipient.mention} deleted.")
        else:
            raise errors.CommandInvokeError(e=f"Star with id {star_id} does not exits.")


async def start_database():
    await tortoise.Tortoise.init(
        db_url=f"sqlite://db.sqlite3",
        modules={"models": ["src.models"]}
    )
    await tortoise.Tortoise.generate_schemas()


instance = Bot()
instance.add_cog(Commands(instance))
instance.run_bot()
