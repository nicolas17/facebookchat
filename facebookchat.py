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
import re

import time
import random

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
        self.dtsg = None

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
            self.dtsg = self._fetchDtsg()
            return True
        else:
            # unexpected code
            raise RuntimeError("Got unexpected code %d" % login_req.status_code)

    def isLoggedIn(self):
        return self.user_id is not None

    def _fetchDtsg(self):
        print("Requesting DTSG")
        resp = requests.get(root, cookies = self._cookies())
        m = re.search('<input type="hidden" name="fb_dtsg" value="([^"]+)" autocomplete="off" />', resp.text)
        return m.group(1)

    def fetchBuddyList(self):
        print("Requesting buddy_list")
        resp = requests.get(
            root + "ajax/chat/buddy_list.php",
            cookies = self._cookies(),
            params = {"__a": "1", "user": str(self.user_id)}
        )
        resp_json = parse_json(resp.text)['payload']

        return resp_json["buddy_list"]["nowAvailableList"]

    def notifyTyping(self, userid, typing):
        print("Notifying user %d that we're %s" % (userid, "typing" if typing else "not typing"))

        resp = requests.post(
            root + "ajax/messaging/typ.php",
            cookies = self._cookies(),
            data = {
                "__a": "1",
                "to": str(userid),
                "thread": str(userid),
                "typ": "1" if typing else "0",
                "fb_dtsg": self.dtsg
            }
        )
        assert resp.status_code == requests.codes.ok
        resp_json = parse_json(resp.text)['payload']

        return resp_json

    def sendMessage(self, recipient, message):
        print("Sending message to user %d" % recipient)

        timestamp = int(time.time() * 1000)
        rnd = random.randint(1, 2**32)

        resp = requests.post(
            root + "ajax/mercury/send_messages.php",
            cookies = self._cookies(),
            data = {
                "message_batch[0][action_type]": "ma-type:user-generated-message",
                "message_batch[0][author]": "fbid:%d" % self.user_id,
                "message_batch[0][timestamp]": "%d" % timestamp,
                "message_batch[0][source]": "source:chat:web",
                "message_batch[0][body]": message,
                "message_batch[0][specific_to_list][0]": "fbid:%d" % recipient,
                "message_batch[0][specific_to_list][1]": "fbid:%d" % self.user_id,
                "message_batch[0][message_id]": "<%d:%d@mail.projektitan.com>" % (timestamp, rnd),
                "message_batch[0][client_thread_id]": "user:%d" % recipient,
                "__a": "1",
                "fb_dtsg": self.dtsg
            }
        )
        assert resp.status_code == requests.codes.ok
        resp_json = parse_json(resp.text)['payload']

        return resp_json


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

    def check_login(self):
        if not chat.isLoggedIn():
            print("Not logged in")
            return False
        return True

    def do_get_buddies(self, line):
        "Gets a list of online users"
        if not self.check_login(): return

        for id, info in chat.fetchBuddyList().items():
            print("User %s is %s" % (id, info["p"]["status"]))

    def do_typing(self, line):
        "typing <userid>: notifies the user that you are typing a message."
        if not self.check_login(): return
        userid = int(line)
        chat.notifyTyping(userid, True)

    def do_not_typing(self, line):
        "not_typing <userid>: notifies the user that you are no longer typing a message."
        if not self.check_login(): return
        userid = int(line)
        chat.notifyTyping(userid, False)

    def do_send(self, line):
        "send <userid> <message>: sends a chat message."
        if not self.check_login(): return
        userstr, message = line.split(" ", 1)
        userid = int(userstr)
        chat.sendMessage(userid, message)

    def do_exit(self, _):
        """Exits this script."""
        return True

Commands().cmdloop()

