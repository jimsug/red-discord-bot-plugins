import json, os, asyncio, requests, re, time
import urllib.parse, urllib.request
import discord
from discord.ext import commands
from cogs.utils import checks
from cogs.utils.dataIO import dataIO

configpath = "data/roles/roles.conf"

class Roles:
    """Manage roles on this server"""
    
    def __init__(self, bot):
        self.bot = bot
        global config
        config = dataIO.load_json(configpath)
    
    @commands.command(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(administrator=True)
    async def roleslist(self, context):
        """Admin-only: list roles and role IDs
        
        roleslist"""
        
        if context.subcommand_passed:
            await self.bot.say(get_role_channels(context.subcommand_passed))
            return
        
        try:
            roles = config["roles"]
            roles = []
        except KeyError:
            config["roles"] = {}
            dataIO.save_json(configpath, config)
            roles = []
            
        for role in context.message.server.roles:
            try:
                roles.append(role.name + ": " + ((", ".join(config["roles"][role.name]) or "None yet.")))
            except KeyError:
                config["roles"][role.name] = []
                roles.append(role.name + ": No subroles added to this role yet")
        
        dataIO.save_json(configpath, config)
        await self.bot.say('\n'.join(roles))
    @commands.command(no_pm=True, pass_context=True)
    async def describerole(self, context, *text):
        """Manage role descriptions"""
        if text[0]:
            return
    
    @commands.command(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(administrator=True)
    async def role(self, context, *text):
        """Manage role access to channels
        
        role <rolename> <subrole> [subrole [subrole]]..."""
        
        if text[0] in config["roles"].keys():
            subrole = " ".join(text[1:])
            if subrole in config["roles"].keys():
                await self.bot.say(toggle_role_subrole(text[0], subrole))
        else:
            await self.bot.say("One or more of the roles you used is not yet configured or does not exist.")

    @commands.command(no_pm=True, pass_context=True)
    async def roles(self, context, *text):
        """Manage your channels on this server
        
        channels list - list the roles (and channels) you can access
        channels add [rolename] - add the role (so you can access the corresponding channels)
        channels remove [rolename] - remove the role (and remove access to the corresponding channels)
        channels toggle [rolename] - add/remove the role (and access to the corresponding channels)
        """
        
        try:
            command = text[0]
        except IndexError:
            command = "list"
        
        if command == "add" or command == "remove":
            pass
        elif command == "join":
            command = "add"
        elif command == "leave":
            command = "remove"
        
        if command == "list":
            resultmsg = await self.bot.say("{0.mention} Channels you can add or remove are:\n".format(context.message.author) + "\n".join(get_valid_user_channels(context.message.author)) or "None.")
        elif len(text) > 1 and (command in ["add", "remove", "toggle"]):
            result = False
            # try:
            result = await manage_user_roles(self, context, " ".join(text[1:]), command)
            # except:
            #     result = False
            
            if result:
                resultmsg = await self.bot.say(result)
                await cleanup(self.bot, [resultmsg, context.message], 3)
            else: await self.bot.say("Something went wrong.")
        else:
            await self.bot.say("Tell me what to do :)")
    
    @commands.command(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(administrator=True)
    async def testdcheck(self, context):
        user = getUserByDiscordId(context.message.author.id)
        await self.bot.say("Agent name: {}\nGoogle name: {}\nAgent level: {}\nAccess level: {}\nPlay areas: {}".format(user["agent_name"], user["google_name"], user["agent_level"], user["agent_role"], user["agent_playarea"]))
        
async def promoteUser(bot, level, member):
    verified = ""
    for role in member.server.roles:
        if role.name == level:
            verified = role
    await bot.add_roles(member, verified)
    return True

def getUserByDiscordId(discordid):
    url = "http://128.199.166.173/api/discord_lookup.php?api_key={}".format(apikey)
    post_data = {
        "discordid":discordid
    }
    try:
        response = urllib.request.urlopen(url, urllib.parse.urlencode(post_data).encode('utf8'))
        data = json.loads(response.read().decode("utf-8"))
    except Exception as inst:
        print(inst.args)
        raise
    if data["result"]:
        return data["agent"]
        
    return False

async def cleanup(bot, messages:list, delay:int=0):
    if delay:
        time.sleep(delay)

    for msg in messages:
        await bot.delete_message(msg)

def toggle_role_subrole(rolename, subrole):
    if subrole in config["roles"][rolename]:
        config["roles"][rolename].remove(subrole)
        result = "removed from"
    else:
        config["roles"][rolename].append(subrole)
        result = "added to"

    dataIO.save_json(configpath, config)
    return "{} added to authorised subroles for role **{}**".format(subrole, rolename)

async def approve_user(self, username):
    pass

async def verify_user(self, username):
    pass

async def manage_user_roles(self, context, rolename, force=None):
    usersubroles = []
    usercurrentroles = []
    modified_role = ""
    for role in context.message.server.roles:
        if role.name.lower() == rolename.lower():
            modified_role = role
    for role in context.message.author.roles:
        try:
            usersubroles += [urole.lower() for urole in config["roles"][role.name]]
        except KeyError:
            config["roles"][role.name] = []
            dataIO.save_json(configpath, config)
        usercurrentroles.append(role.name.lower())
    if not modified_role:
        return "Role not found."
    if not modified_role.name.lower() in usersubroles:
        return "Looks like you can't add this role."
    if force == "add":
        await self.bot.add_roles(context.message.author, modified_role)
        return "Done."
    elif force == "remove":
        await self.bot.remove_roles(context.message.author, modified_role)
        return "Done."
    elif not force or force == "toggle":
        if rolename.lower() in usercurrentroles:
            await self.bot.remove_roles(context.message.author, modified_role)
            return "Done."
        else:
            await self.bot.add_roles(context.message.author, modified_role)
            return "Done."
    return False
    
def get_role_channels(rolename):
    return config["roles"][rolename] or None

def get_valid_user_channels(author):
    subroles = []
    for role in author.roles:
        try:
            subroles += config["roles"][role.name]
        except KeyError:
            pass
        
    return subroles

def check_config_setup():
    paths = ["data", "data/roles"]
    for path in paths:
        if not os.path.exists(path):
            print("Creating folder {}".format(path))
            os.makedirs(path)

    if not os.path.isfile(configpath):
        print("Creating empty config at {}".format(configpath))
        dataIO.save_json(configpath, {})

def setup(bot):
    check_config_setup()
    bot.add_cog(Roles(bot))