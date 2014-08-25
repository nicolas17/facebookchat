# Facebook chat protocol test
# Copyright (C) 2014 Nicolás Alvarez <nicolas.alvarez@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import requests
import sys
import json
import cmd

root = "https://www.facebook.com/"

def removefrombeginning(haystack, needle):
    if haystack.startswith(needle):
        return haystack[len(needle):]

def parse_json(string):
    return json.loads(removefrombeginning(string, "for (;;);"))

class FacebookChat:
    def __init__(self):
        self.user_id = None
        self.session_id = None

    def _cookies(self):
        return {'c_user': str(self.user_id), 'xs': self.session_id}

    def login(self, email, password):
        print("Requesting homepage")
        home_req = requests.get(root)
        assert home_req.status_code == 200

        print("Logging in")
        login_req = requests.post(
            root+"login.php",
            data = {'email': email, 'pass': password},
            cookies = {'datr': home_req.cookies['datr']},
            allow_redirects=False
        )

        if login_req.status_code == 200:
            # we're being served the login page again
            # TODO parse the error message
            return False
        elif login_req.status_code == 302:
            # we got redirected to the main facebook website
            self.user_id = int(login_req.cookies['c_user'])
            self.session_id = login_req.cookies['xs']
            return True
        else:
            # unexpected code
            raise RuntimeError("Got unexpected code %d" % login_req.status_code)

    def isLoggedIn(self):
        return self.user_id is not None

    def fetchBuddyList(self):
        print("Requesting buddy_list")
        resp = requests.get(
            root + "ajax/chat/buddy_list.php",
            cookies = self._cookies(),
            params = {"__a": "1", "user": str(self.user_id)}
        )
        resp_json = parse_json(resp.text)['payload']

        return resp_json["buddy_list"]["nowAvailableList"]

chat = FacebookChat()

class Commands(cmd.Cmd):
    def do_login(self, line):
        "login [email [password]]: Logs into facebook."
        credentials = line.split(" ", 1)
        if credentials[0] == '':
            assert sys.version_info.major == 3
            email = input("Email address: ")
        else:
            email = credentials[0]
        if len(credentials) == 1:
            import getpass
            password = getpass.getpass("Password: ")
        else:
            password = credentials[1]

        if chat.login(email, password):
            print("Logged in successfully")
        else:
            print("Login error")

    def do_get_buddies(self, line):
        "Gets a list of online users"
        if not chat.isLoggedIn():
            print("Not logged in")
            return

        for id, info in chat.fetchBuddyList().items():
            print("User %s is %s" % (id, info["p"]["status"]))

    def do_exit(self, _):
        """Exits this script."""
        return True

Commands().cmdloop()

