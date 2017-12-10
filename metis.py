from PIL import Image
import discord
import os
import sqlite3 as sq

BOT_OWNER_ID = '150919851710480384'

class Metis(discord.Client):
    def __init__(self):
        super().__init__()
        self.ignored_users = {}
        self.db_conns = {}

    async def on_ready(self):
        print('Logged in:', self.user.name)

    async def on_message(self, message):
        if message.author.id == self.user.id: return
        if len(message.content) == 0: return
        if message.content[0] != '.': return

        ## All server members

        # await self.assign_role(message)
        # await self.command(message)
        await self.display_color(message)
        await self.post_command(message)

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
        # await self.edit_command(message)
        # await self.rename_command(message)

        # await self.add_multi_command(message)
        # await self.remove_multi_command(message) # one at a time

        ## Bot owner only

        await self.add_moderator_role(message)
        await self.remove_moderator_role(message)
        await self.show_moderator_roles(message)
        await self.show_all_roles(message)
        await self.setup_server_db(message)

        # These are all self-assignable roles only
        # await self.add_role_alternate_name(message)
        # await self.remove_role_alternate_name(message)
        # await self.add_role(message)
        # await self.remove_role(message)

    async def setup_server_db(self, message):
        if message.author.id != BOT_OWNER_ID: return
        if message.content != '.ssdb': return

        db_name = 'db/{}.db'.format(message.server.id)
        if os.path.exists(db_name):
            report = ':bangbang: Server database already exists'
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

        conn.commit()
        conn.close()
        report = ':white_check_mark: Done setting up database'
        await self.send_message(message.channel, report)

    async def add_moderator_role(self, message):
        '''Show all the moderator roles on the server'''
        if message.author.id != BOT_OWNER_ID: return

        prefix = 'amr'
        if message.content[1:1+len(prefix)] != prefix: return

        split = message.content.strip().split()
        if len(split) != 2: return

        # ensure role exists
        role_id = split[1]
        role = discord.utils.find(lambda r: r.id == role_id, message.server.roles)
        if role is None:
            report = ':question: Couldn\'t find role with ID: {}'.format(role_id)
            await self.send_message(message.channel, report)
            return

        conn = sq.connect('db/{}.db'.format(message.server.id))
        c = conn.cursor()
        c.execute("INSERT INTO moderator_roles VALUES (?)", (role_id,))
        conn.commit()
        conn.close()

        report = ':white_check_mark: Added moderator role: {} / {}'.format(role.name, role.id)
        await self.send_message(message.channel, report)

    async def remove_moderator_role(self, message):
        if message.author.id != BOT_OWNER_ID: return

        prefix = 'rmr'
        if message.content[1:1+len(prefix)] != prefix: return

        split = message.content.strip().split()
        if len(split) != 2: return

        # ensure role exists
        role_id = split[1]
        role = discord.utils.find(lambda r: r.id == role_id, message.server.roles)
        if role is None:
            report = ':question: Couldn\'t find role with ID: {}'.format(role_id)
            await self.send_message(message.channel, report)
            return

        conn = sq.connect('db/{}.db'.format(message.server.id))
        c = conn.cursor()
        c.execute("DELETE FROM moderator_roles WHERE id=?", (role_id,))
        conn.commit()
        conn.close()

        report = ':white_check_mark: Deleted moderator role: {} / {}'.format(role.name, role.id)
        await self.send_message(message.channel, report)

    async def show_moderator_roles(self, message):
        if message.author.id != BOT_OWNER_ID: return # TODO: this should be moderator check
        if message.content != '.smr': return

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

    async def show_all_roles(self, message):
        '''Show all roles in the server'''
        # TODO: make this mod-only, not owner-only
        if message.author.id != BOT_OWNER_ID: return
        if message.content.strip() != '.roles': return

        role_list = sorted(message.server.roles, key=lambda r: r.position, reverse=True)
        await self.show_roles_helper(role_list, message.channel)

    async def show_roles_helper(self, role_list, dest):
        '''A helper function for show_moderator_roles and show_all_roles'''
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

    async def display_color(self, message):
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

        if message.content[0] not in '.!': return

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
        if message.content[0] != '.': return
        if message.author.id != BOT_OWNER_ID: return # TODO: make this a moderator check

        prefix = 'add'
        content = message.content.strip()
        if content[1:1+len(prefix)] != prefix: return

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
        if message.content[0] != '.': return

        prefix = 'remove'
        content = message.content.strip()
        if content[1:1+len(prefix)] != prefix: return

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


metis = Metis()
metis.run(os.environ['M_BOT_TOKEN'])