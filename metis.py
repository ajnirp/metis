from PIL import Image
import discord
import os
import random
import sqlite3 as sq
import sys
import util

BOT_OWNER_ID = '150919851710480384'

class Metis(discord.Client):
    def __init__(self):
        super().__init__()
        self.ignored_users = set()
        self.emojis = {}
        self.db_conns = {}
        self.keys = set([
            'logchan',
            'rolechan',
            'logging',
            'roleassign',
            'joinannounce',
            'leaveannounce',
            ''])

    async def on_ready(self):
        print('Logged in:', self.user.name)
        self.refresh_emojis()

    def refresh_emojis(self):
        '''Initalize all emojis'''
        self.emojis = {}
        for emoji in self.get_all_emojis():
            emoji_str = '<:{}:{}>'.format(emoji.name, emoji.id)
            self.emojis[emoji.name] = emoji_str

    def is_mod(self, user, server):
        '''Does the user `user` have at least one role that has moderator
        status on the server `server`?'''
        return user.id == BOT_OWNER_ID # TODO: make this use the mod role table

    async def on_message(self, message):
        if message.author.id == self.user.id: return
        if len(message.content) == 0: return
        if message.content[0] not in '.-': return

        if message.author.id in self.ignored_users: return

        ## All server members

        # await self.assign_role(message)
        # await self.command(message)
        await self.color_patch(message)
        await self.post_command(message)
        await self.choose(message)
        await self.server_info(message)
        await self.user_info(message)
        await self.display_avatar(message)

        ## Moderators only

        # await self.kick(message)
        # await self.ban(message)

        # await self.make_empty_role(message)

        # await self.toggle_join_announcement(message)
        # await self.toggle_leave_announcement(message)

        # await self.set_join_message(message)
        # await self.set_leave_message(message)

        # await self.add_preban(message)
        # await self.remove_preban(message)
        # await self.search_preban(message)
        # await self.show_prebans(message)

        # await self.ignore_for_logging(message)
        # await self.ignore_for_gallery(message)

        await self.add_command(message)
        await self.remove_command(message)
        await self.delete_messages_(message)
        # await self.edit_command(message)
        # await self.rename_command(message)

        # await self.add_multi_command(message)
        # await self.remove_multi_command(message) # one at a time

        ## Bot owner only

        await self.add_moderator_role(message)
        await self.remove_moderator_role(message)
        await self.list_moderator_roles(message)
        await self.list_all_roles(message)

        await self.setup_server_db(message)

        await self.ignore_user(message)
        await self.unignore_user(message)
        await self.list_ignored_users(message)

        await self.refresh_emojis_request(message)

        await self.add_self_assignable_role(message)
        await self.remove_self_assignable_role(message)
        await self.list_self_assignable_roles(message)
        await self.set_role_channel(message)
        await self.list_role_channel(message)
        await self.set_log_channel(message)
        await self.list_log_channel(message)
        # await self.ignore_channel(message)

        # These are all self-assignable roles only
        # await self.add_role_alternate_name(message)
        # await self.remove_role_alternate_name(message)
        # await self.add_role(message)
        # await self.remove_role(message)

    async def delete_messages_(self, message):
        '''Delete the last n number of messages. The final underscore in the name
        is because we want to avoid overwriting the delete_message() method in discord.Client'''
        if not self.is_mod(message.author, message.server): return
        if not message.content.startswith('-d'): return
        num_messages = message.content[2:]
        try:
            num_messages = 1 + int(num_messages)
            await self.purge_from(message.channel, limit=num_messages)
            # await self.send_message(message.channel, 'deleted {} messages'.format(num_messages))
        except AttributeError as e:
            print('delete_messages: {}'.format(e), file=sys.stderr)
            return

    async def setup_server_db(self, message):
        if message.author.id != BOT_OWNER_ID: return
        if message.content != '-ssdb': return

        db_name = 'db/{}.db'.format(message.server.id)
        if os.path.exists(db_name):
            report = '{} Server database already exists'.format(self.emojis['blobstop'])
            await self.send_message(message.channel, report)
            return
        conn = sq.connect(db_name)
        c = conn.cursor()

        c.execute('CREATE TABLE moderator_roles (id text);')
        c.execute('CREATE TABLE do_not_log (type integer, id text);')
        # type is 0 for users, 1 for channels
        c.execute('CREATE TABLE dont_copy_to_gallery (type integer, id text);')
        # type is 0 for users, 1 for channels
        c.execute('CREATE TABLE prebans (id text, reason text, ban_date date);')
        c.execute('CREATE TABLE commands (command text, response text);')
        c.execute('CREATE TABLE multi_commands (command text, responses text);')
        c.execute('CREATE TABLE role_alternate_names (canonical_name text, alternate_name text);')
        c.execute('CREATE TABLE role_ids (canonical_name text, id text);')
        c.execute('CREATE TABLE ignored_users (id text);')
        c.execute('CREATE TABLE self_assignable_roles (id text);')
        c.execute('CREATE TABLE server_config (key text, value text);')

        conn.commit()
        conn.close()
        report = '{} Done setting up database'.format(self.emojis['blobgo'])
        await self.send_message(message.channel, report)

    async def add_moderator_role(self, message):
        '''Add a role to the moderator group'''
        if message.author.id != BOT_OWNER_ID: return
        if message.content[0] != '-': return

        prefix = 'amr'
        if message.content[1:1+len(prefix)] != prefix: return

        if not util.check_db_exists(message):
            report = '{} Server database does not exist. Please set it up first: `-ssdb`'.format(self.emojis['angerycry'])
            await self.send_message(message.channel, report)
            return

        split = message.content.strip().split()
        if len(split) != 2: return

        # ensure role exists
        role_id = split[1]
        role = discord.utils.find(lambda r: r.id == role_id, message.server.roles)
        if role is None:
            report = '{} Couldn\'t find role with ID: {}'.format(self.emojis['blobwaitwhat'], role_id)
            await self.send_message(message.channel, report)
            return

        conn = sq.connect('db/{}.db'.format(message.server.id))
        c = conn.cursor()
        c.execute("INSERT INTO moderator_roles VALUES (?)", (role_id,))
        conn.commit()
        conn.close()

        report = '{} This role now has moderator status: {} / {}'.format(self.emojis['blobgo'], role.name, role.id)
        await self.send_message(message.channel, report)

    async def remove_moderator_role(self, message):
        '''Remove a role from the moderator group'''
        if message.author.id != BOT_OWNER_ID: return
        if message.content[0] != '-': return

        prefix = 'rmr'
        if message.content[1:1+len(prefix)] != prefix: return

        if not util.check_db_exists(message):
            report = '{} Server database does not exist. Please set it up first: `-ssdb`'.format(self.emojis['angerycry'])
            await self.send_message(message.channel, report)
            return

        split = message.content.strip().split()
        if len(split) != 2: return

        # ensure role exists
        role_id = split[1]
        role = discord.utils.find(lambda r: r.id == role_id, message.server.roles)
        if role is None:
            report = '{} Couldn\'t find role with ID: {}'.format(self.emojis['blobwaitwhat'], role_id)
            await self.send_message(message.channel, report)
            return

        conn = sq.connect('db/{}.db'.format(message.server.id))
        c = conn.cursor()
        c.execute("DELETE FROM moderator_roles WHERE id=?", (role_id,))
        conn.commit()
        conn.close()

        report = '{} This role no longer has moderator status: {} / {}'.format(self.emojis['blobgo'], role.name, role.id)
        await self.send_message(message.channel, report)

    async def list_moderator_roles(self, message):
        '''Show all the moderator roles on the server'''
        if not self.is_mod(message.author, message.server): return
        if message.content != '-lmr': return

        if not util.check_db_exists(message):
            report = '{} Server database does not exist. Please set it up first: `-ssdb`'.format(self.emojis['angerycry'])
            await self.send_message(message.channel, report)
            return

        conn = sq.connect('db/{}.db'.format(message.server.id))
        c = conn.cursor()
        role_id_list = [row[0] for row in c.execute("SELECT * FROM moderator_roles")]
        conn.commit()
        conn.close()

        role_list = []
        for role_id in role_id_list:
            role = discord.utils.find(lambda r: r.id == role_id, message.server.roles)
            role_list.append(role)

        await self.show_roles_helper(role_list, message.channel)

    async def list_all_roles(self, message):
        '''Show all roles in the server'''
        # TODO: make this mod-only, not owner-only
        if message.author.id != BOT_OWNER_ID: return
        if message.content != '-lar': return

        role_list = sorted(message.server.roles, key=lambda r: r.position, reverse=True)
        await self.show_roles_helper(role_list, message.channel)

    async def show_roles_helper(self, role_list, dest):
        '''A helper function for list_moderator_roles and list_all_roles'''
        MESSAGE_LIMIT = 2000
        chunks = []

        for role in role_list:
            if role.name == '@everyone': continue
            c = role.color
            message_chunk = '{} / {} / {}\n'.format(role.name, hex(c.value), role.id)
            chunks.append(message_chunk)

        if len(chunks) == 0:
            await self.send_message(dest, ':confused: No roles found')
            return

        cumulative_len, start, idx = 0, 0, 0
        for chunk in chunks:
            cumulative_len += len(chunk)
            if cumulative_len > MESSAGE_LIMIT:
                report = ''.join(chunks[start:idx])
                await self.send_message(dest, report)
                start = idx
                cumulative_len = 0
            idx += 1
        report = ''.join(chunks[start:idx])
        await self.send_message(dest, report)

    async def color_patch(self, message):
        '''Display a color patch'''
        async def show_usage(message):
            report = 'Usage: `.color <RGB hex code>` e.g.\n`.color #abc123`\n`.color 142 79 105`'
            await self.send_message(message.channel, report)

        def hex_code_to_rgb(h):
            return tuple(int(channel, 16) for channel in [h[:2], h[2:4], h[4:]])

        def rgb_to_hex_code(r, g, b):
            def two_digit_hex(n):
                return hex(int(n))[2:].rjust(2, '0')
            return ''.join(map(two_digit_hex, [r, g, b]))

        async def send_color_patch_pic(color):
            data = [color for i in range(64 * 64)]
            img = Image.new('RGB', (64, 64))
            img.putdata(data)
            filename = form_filename(color)
            img.save(filename)
            await self.send_file(message.channel, filename)
            os.remove(filename)

        def form_filename(color):
            hex_code = rgb_to_hex_code(*color)
            filename = '{}.png'.format(hex_code)
            return filename

        if message.content[0] != '.': return

        prefixes = ['color', 'colour']
        if not any(message.content[1:1+len(prefix)] == prefix for prefix in prefixes):
            return

        split = message.content.split()

        if len(split) == 2:
            color = split[1]
            if color.startswith('#'): color = color[1:]
            elif color.startswith('0x'): color = color[2:]
            color = hex_code_to_rgb(color)
            await send_color_patch_pic(color)

        elif len(split) == 4:
            color = tuple(int(s) for s in split[1:])
            await send_color_patch_pic(color)

        else:
            await show_usage(message)
            return

    async def add_command(self, message):
        '''Create a new command-response pair'''
        if not self.is_mod(message.author, message.server): return
        if message.content[0] != '-': return

        prefix = 'add'
        content = message.content.strip()
        if content[1:1+len(prefix)] != prefix: return

        if not util.check_db_exists(message):
            report = '{} Server database does not exist. Please set it up first: `-ssdb`'.format(self.emojis['angerycry'])
            await self.send_message(message.channel, report)
            return

        split = content.split('|')
        if len(split) != 2: return

        command = split[0].split()[1].strip()

        db_name = 'db/{}.db'.format(message.server.id)
        conn = sq.connect(db_name)
        c = conn.cursor()

        c.execute('SELECT response from commands WHERE command=?', (command,))
        result = c.fetchone()

        if result is not None:
            response = result[0]
            report = ':no_entry_sign: Command **{}** already exists (response: <{}>)'.format(command, response)
            await self.send_message(message.channel, report)
            return

        response = split[1].strip()
        c.execute('INSERT INTO commands VALUES (?, ?)', (command, response))
        conn.commit()
        conn.close()

        report = ':white_check_mark: Created command **{}** (response: <{}>)'.format(command, response)
        await self.send_message(message.channel, report)

    async def post_command(self, message):
        '''Post a response to a command'''
        # The message should be of the form '.command'
        if message.content[0] != '.': return

        # Note: in this case, we do not display an error message if the server DB does not exist
        if not util.check_db_exists(message):
            return

        split = message.content.strip().split()
        if len(split) != 1: return

        command = message.content.strip()[1:]

        db_name = 'db/{}.db'.format(message.server.id)
        conn = sq.connect(db_name)
        c = conn.cursor()

        c.execute('SELECT response from commands WHERE command=?', (command,))
        result = c.fetchone()

        if result is None: return

        report = result[0]
        await self.send_message(message.channel, report)

        conn.close()

    async def remove_command(self, message):
        '''Remove an existing command'''
        if not self.is_mod(message.author, message.server): return
        if message.content[0] != '-': return

        prefix = 'remove'
        content = message.content.strip()
        if content[1:1+len(prefix)] != prefix: return

        if not util.check_db_exists(message):
            report = '{} Server database does not exist. Please set it up first: `-ssdb`'.format(self.emojis['angerycry'])
            await self.send_message(message.channel, report)
            return

        split = content.split()
        if len(split) != 2: return

        command = split[1].strip()

        db_name = 'db/{}.db'.format(message.server.id)
        conn = sq.connect(db_name)
        c = conn.cursor()

        c.execute('SELECT response from commands WHERE command=?', (command,))
        result = c.fetchone()

        if result is None:
            report = ':confused: The command **{}** does not exist. Would you like to add it?'.format(command)
            await self.send_message(message.channel, report)
            return

        response = result[0]

        c.execute('DELETE FROM commands WHERE command=?', (command,))
        conn.commit()
        conn.close()

        report = ':white_check_mark: Deleted command **{}** (response was: <{}>)'.format(command, response)
        await self.send_message(message.channel, report)

    async def ignore_user(self, message):
        '''Sart ignoring all commands from a user'''
        if message.author.id != BOT_OWNER_ID: return
        if message.content[0] != '-': return

        prefix = 'iu'
        if message.content[1:1+len(prefix)] != prefix: return

        if not util.check_db_exists(message):
            report = '{} Server database does not exist. Please set it up first: `-ssdb`'.format(self.emojis['angerycry'])
            await self.send_message(message.channel, report)
            return

        if len(message.mentions) < 1: return

        db_name = 'db/{}.db'.format(message.server.id)
        conn = sq.connect(db_name)
        c = conn.cursor()

        for target in message.mentions:
            if target.id == BOT_OWNER_ID: continue
            c.execute('SELECT * from ignored_users WHERE id=?', (target.id,))
            result = c.fetchone()
            if result is None:
                c.execute('INSERT INTO ignored_users VALUES (?)', (target.id,))
                report = '{} Now ignoring user: **{}** / {}'.format(self.emojis['angerycry'], target.display_name, target.id)
                await self.send_message(message.channel, report)
            else:
                report = '{} Already ignoring this user: **{}** / {}'.format(self.emojis['blobstop'], target.display_name, target.id)
                await self.send_message(message.channel, report)

        # Update local list
        for row in c.execute('SELECT * from ignored_users'):
            self.ignored_users.add(row[0])

        conn.commit()
        conn.close()

    async def unignore_user(self, message):
        '''Stop ignoring all messages from a user'''
        if message.author.id != BOT_OWNER_ID: return
        if message.content[0] != '-': return

        prefix = 'uiu'
        if message.content[1:1+len(prefix)] != prefix: return

        if not util.check_db_exists(message):
            report = '{} Server database does not exist. Please set it up first: `-ssdb`'.format(self.emojis['angerycry'])
            await self.send_message(message.channel, report)
            return

        if len(message.mentions) < 1: return

        db_name = 'db/{}.db'.format(message.server.id)
        conn = sq.connect(db_name)
        c = conn.cursor()

        for target in message.mentions:
            c.execute('SELECT * from ignored_users WHERE id=?', (target.id,))
            result = c.fetchone()
            if result is None:
                report = '{} This user was not in the ignored list: **{}** / {}'.format(self.emojis['blobwaitwhat'], target.display_name, target.id)
                await self.send_message(message.channel, report)
            else:
                c.execute('DELETE FROM ignored_users WHERE id=?', (target.id,))
                report = '{} No longer ignoring user: **{}** / {}'.format(self.emojis['blobthumbsup'], target.display_name, target.id)
                await self.send_message(message.channel, report)

        # Update local list
        self.ignored_users = set()
        for row in c.execute('SELECT * from ignored_users'):
            self.ignored_users.add(row[0])

        conn.commit()
        conn.close()

    async def list_ignored_users(self, message):
        '''List all users that the bot is ignoring'''
        if message.author.id != BOT_OWNER_ID: return
        if message.content != '-liu': return

        if not util.check_db_exists(message):
            report = '{} Server database does not exist. Please set it up first: `-ssdb`'.format(self.emojis['angerycry'])
            await self.send_message(message.channel, report)
            return

        db_name = 'db/{}.db'.format(message.server.id)
        conn = sq.connect(db_name)
        c = conn.cursor()

        # Update local copy of the ignored_users table
        for row in c.execute('SELECT * from ignored_users'):
            self.ignored_users.add(row[0])

        conn.close()

        MESSAGE_LIMIT = 2000
        chunks = []

        for user_id in self.ignored_users:
            member = discord.utils.find(lambda m: m.id == user_id, message.server.members)
            message_chunk = '{}#{} / {}\n'.format(member.name, str(member.discriminator), member.id)
            chunks.append(message_chunk)

        if len(chunks) == 0:
            report = '{} Not ignoring any users'.format(self.emojis['blobblush'])
            await self.send_message(message.channel, report)
            return
        else:
            report = '{} Ignoring the following users:'.format(self.emojis['blobunamused'])
            await self.send_message(message.channel, report)

        cumulative_len, start, idx = 0, 0, 0
        for chunk in chunks:
            cumulative_len += len(chunk)
            if cumulative_len > MESSAGE_LIMIT:
                report = ''.join(chunks[start:idx])
                await self.send_message(dest, report)
                start = idx
                cumulative_len = 0
            idx += 1
        report = ''.join(chunks[start:idx])
        await self.send_message(message.channel, report)

    async def refresh_emojis_request(self, message):
        '''Refresh all the emojis the bot can see'''
        if message.author.id != BOT_OWNER_ID: return
        if message.content != '-re': return
        self.refresh_emojis()
        report = '{} Refreshed emojis'.format(self.emojis['blobokhand'])
        await self.send_message(message.channel, report)

    async def choose(self, message):
        '''The Dice Man, but for Discord'''
        async def show_usage(message):
            report = 'Usage: `.choose <choice1> | <choice2> | <choice3> | ...`' + \
                     '\ne.g. `.choose go to sleep | post on discord`'
            await self.send_message(message.channel, report)

        if message.content[0] not in '.!': return

        prefix = 'choose'
        if message.content[1:1+len(prefix)] != prefix: return

        split = message.content.split()
        if len(split) < 2:
            await show_usage(message)
            return

        choices = message.content.strip()[2+len(prefix):].strip()
        choices = choices.split('|')
        chosen = random.choice(choices)
        report = '{0.mention} I choose: **{1}**!'.format(message.author, chosen.strip())
        await self.send_message(message.channel, report)

    async def server_info(self, message):
        '''Display the server info'''
        if message.content != '.s': return

        embed = discord.Embed(
            title='Server info',
            type='rich',
            description=message.server.name,
            url=discord.Embed.Empty,
            footer=discord.Embed.Empty,
            colour=discord.Color(0xeaa82e))

        roles = ' / '.join(r.name for r in message.server.role_hierarchy)

        embed.set_thumbnail(url=message.server.icon_url) \
             .add_field(name='Server created', value=util.ts(message.server.created_at)) \
             .add_field(name='Members', value=message.server.member_count) \
             .add_field(name='ID', value=message.server.id) \
             .add_field(name='Owner', value=message.server.owner.name) \
             .add_field(name='Roles', value=roles)

        await self.send_message(message.channel, content=None, tts=False, embed=embed)

    async def user_info(self, message):
        '''Handle the .u message'''
        if message.content[:2] != '.u': return

        if len(message.mentions) == 0:
            await self.display_user_info(message.author, message.channel)
            return

        for member in message.mentions:
            await self.display_user_info(member, message.channel)

    async def display_user_info(self, member, channel):
        '''Send a message to channel 'channel' containing an Embed object
        that has information about the server member 'member'.'''
        account_created = discord.utils.snowflake_time(member.id)

        role_names = 'None'
        if len(member.roles) > 1:
            role_names = ' / '.join(r.name for r in sorted(member.roles[1:], key=lambda r: r.position, reverse=True))

        embed = discord.Embed(
            title='User info',
            type='rich',
            description=member.name,
            url=discord.Embed.Empty,
            timestamp=discord.Embed.Empty,
            footer=discord.Embed.Empty,
            colour=member.top_role.colour)

        embed.set_thumbnail(url=member.avatar_url) \
             .add_field(name='Account made', value=util.ts(account_created)) \
             .add_field(name='Here since', value=util.ts(member.joined_at)) \
             .add_field(name='ID', value=member.id) \
             .add_field(name='Nickname', value=member.nick) \
             .add_field(name='Status', value=str(member.status).title()) \
             .add_field(name='Roles', value=role_names)

        await self.send_message(channel, content=None, tts=False, embed=embed)

    async def display_avatar(self, message):
        '''Post the avatar of a user'''
        if message.content != '.a' and message.content[:3] != '.a ': return
        targets = [message.author]
        if len(message.mentions) > 0:
            targets = message.mentions
        for member in targets:
            report = '{} User has no avatar'.format(self.emojis['sayWhat'])
            if member.avatar_url != '':
                report = '{}\'s avatar: {}'.format(member.name, member.avatar_url)
            await self.send_message(message.channel, report)

    async def add_self_assignable_role(self, message):
        '''Add a self-assignable role'''
        if not self.is_mod(message.author, message.server): return
        if message.content[0] != '-': return

        prefix = 'asar'
        if message.content[1:1+len(prefix)] != prefix: return

        if not util.check_db_exists(message):
            report = '{} Server database does not exist. Please set it up first: `-ssdb`'.format(self.emojis['angerycry'])
            await self.send_message(message.channel, report)
            return

        split = message.content.strip().split()
        if len(split) != 2: return

        # ensure role exists
        role_id = split[1]
        role = discord.utils.find(lambda r: r.id == role_id, message.server.roles)
        if role is None:
            report = '{} Couldn\'t find role with ID: {}'.format(self.emojis['blobwaitwhat'], role_id)
            await self.send_message(message.channel, report)
            return

        conn = sq.connect('db/{}.db'.format(message.server.id))
        c = conn.cursor()
        c.execute("INSERT INTO self_assignable_roles VALUES (?)", (role_id,))
        conn.commit()
        conn.close()

        report = '{} This role is now self-assignable: {} / {}'.format(self.emojis['blobthumbsup'], role.name, role.id)
        await self.send_message(message.channel, report)


    async def remove_self_assignable_role(self, message):
        '''Remove a role from being self-assignable'''
        if not self.is_mod(message.author, message.server): return
        if message.content[0] != '-': return

        prefix = 'rsar'
        if message.content[1:1+len(prefix)] != prefix: return

        if not util.check_db_exists(message):
            report = '{} Server database does not exist. Please set it up first: `-ssdb`'.format(self.emojis['angerycry'])
            await self.send_message(message.channel, report)
            return

        split = message.content.strip().split()
        if len(split) != 2: return

        # ensure role exists
        role_id = split[1]
        role = discord.utils.find(lambda r: r.id == role_id, message.server.roles)
        if role is None:
            report = '{} Couldn\'t find role with ID: {}'.format(self.emojis['blobwaitwhat'], role_id)
            await self.send_message(message.channel, report)
            return

        conn = sq.connect('db/{}.db'.format(message.server.id))
        c = conn.cursor()
        c.execute("DELETE FROM self_assignable_roles WHERE id=?", (role_id,))
        conn.commit()
        conn.close()

        report = '{} This role is no longer self-assignable: {} / {}'.format(self.emojis['blobthumbsup'], role.name, role.id)
        await self.send_message(message.channel, report)

    async def list_self_assignable_roles(self, message):
        '''List all self-assignable roles on the server'''
        if not self.is_mod(message.author, message.server): return
        if message.content != '-lsar': return

        if not util.check_db_exists(message):
            report = '{} Server database does not exist. Please set it up first: `-ssdb`'.format(self.emojis['angerycry'])
            await self.send_message(message.channel, report)
            return

        conn = sq.connect('db/{}.db'.format(message.server.id))
        c = conn.cursor()
        role_id_list = [row[0] for row in c.execute("SELECT * FROM self_assignable_roles")]
        conn.commit()
        conn.close()

        role_list = []
        for role_id in role_id_list:
            role = discord.utils.find(lambda r: r.id == role_id, message.server.roles)
            role_list.append(role)

        await self.show_roles_helper(role_list, message.channel)

    async def set_role_channel(self, message):
        '''Set the channel in which users can self-assign roles'''
        if not self.is_mod(message.author, message.server): return
        if message.content[0] != '-': return

        prefix = 'src'
        if message.content[1:1+len(prefix)] != prefix: return

        if not util.check_db_exists(message):
            report = '{} Server database does not exist. Please set it up first: `-ssdb`'.format(self.emojis['angerycry'])
            await self.send_message(message.channel, report)
            return

        if len(message.channel_mentions) != 1:
            report = 'Usage: `-src #channel`'
            await self.send_message(message.channel, report)
            return

        channel = message.channel_mentions[0]

        conn = sq.connect('db/{}.db'.format(message.server.id))
        c = conn.cursor()

        # check that the server doesn't already have a role channel
        c.execute('SELECT value FROM server_config WHERE key=? LIMIT 1', ("Role Channel",))
        result = c.fetchone()
        if result is not None:
            c.execute('UPDATE server_config SET value=? WHERE key=?', (channel.id, "Role Channel"))
        else:
            c.execute("INSERT INTO server_config VALUES (?, ?)", ("Role Channel", channel.id))

        conn.commit()
        conn.close()

        report = '{0} The role channel has been set to: {1.mention} / {2}'.format(self.emojis['blobthumbsup'], channel, channel.id)
        await self.send_message(message.channel, report)

    async def list_role_channel(self, message):
        '''List the role channel'''
        if not self.is_mod(message.author, message.server): return
        if message.content != '-lrc': return

        if not util.check_db_exists(message):
            report = '{} Server database does not exist. Please set it up first: `-ssdb`'.format(self.emojis['angerycry'])
            await self.send_message(message.channel, report)
            return

        conn = sq.connect('db/{}.db'.format(message.server.id))
        c = conn.cursor()
        c.execute("SELECT value FROM server_config where key=?", ("Role Channel",))
        result = c.fetchone()

        if result is None:
            report = '{} This server doesn\'t have a role channel'.format(self.emojis['angerycry'])
            await self.send_message(message.channel, report)
            return

        conn.close()
        result = result[0]

        channel = discord.utils.find(lambda c: c.id == result, message.server.channels)
        if channel is None:
            report = '{} Possible config error: the listed role channel does not exist on this server'.format(self.emojis['blobwaitwhat'])
            await self.send_message(message.channel, report)
            return


        report = '{0} The role channel is: {1.mention} / {2}'.format(self.emojis['blobgo'], channel, channel.id)
        await self.send_message(message.channel, report)

    async def set_log_channel(self, message):
        '''Set the log channel'''
        if not self.is_mod(message.author, message.server): return
        if message.content[0] != '-': return

        prefix = 'slc'
        if message.content[1:1+len(prefix)] != prefix: return

        if not util.check_db_exists(message):
            report = '{} Server database does not exist. Please set it up first: `-ssdb`'.format(self.emojis['angerycry'])
            await self.send_message(message.channel, report)
            return

        if len(message.channel_mentions) != 1:
            report = 'Usage: `-slc #channel`'
            await self.send_message(message.channel, report)
            return

        channel = message.channel_mentions[0]

        conn = sq.connect('db/{}.db'.format(message.server.id))
        c = conn.cursor()

        # check that the server doesn't already have a log channel
        c.execute('SELECT value FROM server_config WHERE key=? LIMIT 1', ("Log Channel",))
        result = c.fetchone()
        if result is not None:
            c.execute('UPDATE server_config SET value=? WHERE key=?', (channel.id, "Log Channel"))
        else:
            c.execute("INSERT INTO server_config VALUES (?, ?)", ("Log Channel", channel.id))

        conn.commit()
        conn.close()

        report = '{0} The log channel has been set to: {1.mention} / {2}'.format(self.emojis['blobthumbsup'], channel, channel.id)
        await self.send_message(message.channel, report)

    async def list_log_channel(self, message):
        '''List the log channel'''
        if not self.is_mod(message.author, message.server): return
        if message.content != '-llc': return

        if not util.check_db_exists(message):
            report = '{} Server database does not exist. Please set it up first: `-ssdb`'.format(self.emojis['angerycry'])
            await self.send_message(message.channel, report)
            return

        conn = sq.connect('db/{}.db'.format(message.server.id))
        c = conn.cursor()
        c.execute("SELECT value FROM server_config where key=?", ("Log Channel",))
        result = c.fetchone()

        if result is None:
            report = '{} This server doesn\'t have a log channel'.format(self.emojis['angerycry'])
            await self.send_message(message.channel, report)
            return

        conn.close()
        result = result[0]

        channel = discord.utils.find(lambda c: c.id == result, message.server.channels)
        if channel is None:
            report = '{} Possible config error: the listed log channel does not exist on this server'.format(self.emojis['blobwaitwhat'])
            await self.send_message(message.channel, report)
            return


        report = '{0} The log channel is: {1.mention} / {2}'.format(self.emojis['blobgo'], channel, channel.id)
        await self.send_message(message.channel, report)

    async def set_key(self, message):
        '''Set the channel in which users can self-assign roles'''
        if not self.is_mod(message.author, message.server): return
        if message.content[0] != '-': return

        prefix = 'set'
        if message.content[1:1+len(prefix)] != prefix: return

        if not util.check_db_exists(message):
            report = '{} Server database does not exist. Please set it up first: `-ssdb`'.format(self.emojis['angerycry'])
            await self.send_message(message.channel, report)
            return

        split = message.content.split()
        if len(split) < 3:
            report = 'Usage: `-set key value`'
            await self.send_message(message.channel, report)
            return

        key = split[1]
        value_start_idx = 1 + len(prefix) + 1 + len(key) + 1
        value = message.content[value_start_idx:]

        conn = sq.connect('db/{}.db'.format(message.server.id))
        c = conn.cursor()

        # check that the server doesn't already have a role channel
        c.execute('SELECT value FROM server_config WHERE key=? LIMIT 1', ("Role Channel",))
        result = c.fetchone()
        if result is not None:
            c.execute('UPDATE server_config SET value=? WHERE key=?', (channel.id, "Role Channel"))
        else:
            c.execute("INSERT INTO server_config VALUES (?, ?)", ("Role Channel", channel.id))

        conn.commit()
        conn.close()

        report = '{0} The role channel has been set to: {1.mention} / {2}'.format(self.emojis['blobthumbsup'], channel, channel.id)
        await self.send_message(message.channel, report)

    async def toggle_logging(self, message):
        pass

    async def set_join_leave_announcement_channel(self, message):
        pass

    async def toggle_join_announcement(self, message):
        pass

    async def toggle_leave_announcement(self, message):
        pass

    async def add_preban(self, message):
        pass

    async def remove_preban(self, message):
        pass

    async def search_preban(self, message):
        pass

    async def show_prebans(self, message):
        pass


metis = Metis()
metis.run(os.environ['M_BOT_TOKEN'])