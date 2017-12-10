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

        # await self.add_command(message)
        # await self.remove_command(message)
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

metis = Metis()
metis.run(os.environ['M_BOT_TOKEN'])