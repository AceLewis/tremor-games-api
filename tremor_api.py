"""
Tremor Games API

A simple "API" for interacting with TremorGames.com. This can be used for sending, deleting,
and receiving messages, and getting a list containing people that you have refered to the website.

The website has no official API so this is just a simple way to deal the website.
"""

from datetime import datetime
import re
from collections import namedtuple

import requests
from bs4 import BeautifulSoup


class TremorApi():
    "This is the 'API', you could potentially create multiple sessions as the same user"

    def __init__(self, username, password):
        # Header so it looks like it is from a browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36',
            'Referer': 'http://www.tremorgames.com/',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Host': 'www.tremorgames.com',
            'Origin': 'http://www.tremorgames.com',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Accept-Encoding': 'gzip, deflate',
                }
        # Create session
        self.ses = requests.Session()
        # Log into Tremor Games
        self.logged_in = self.log_in(username, password)

    def log_in(self, username, password):
        "Simply log in to Tremor Games, provide the username and password."
        # We need to send a post request to the login form using this payload
        payload = {'loginuser': username, 'loginpassword': password, 'Submit': '', 'saveme': '1'}
        self.ses.get('http://www.tremorgames.com', headers=self.headers)
        # Use a url that requires being logged in, although any url will work
        url = 'http://www.tremorgames.com/index.php?action=sendmessage'
        result = self.ses.post(url, data=payload, headers=self.headers)
        return self.check_if_logged_in(result)

    @staticmethod
    def check_if_logged_in(request):
        "Check to see if request returned shows user is logged in"
        # This does not send an additional request but just checks that the logout button is present
        return '://www.tremorgames.com/Logout.html' in request.text

    def log_out(self):
        "Logs the user out."
        url = 'http://www.tremorgames.com/Logout.html'
        result = self.ses.get(url, headers=self.headers)
        # Check that the user has been logged out
        return not self.check_if_logged_in(result)

    def get_all_messages(self):
        """
        Get all private messages availible (the last 100 messages),
        to get the other older messages the new ones have to be deleted.
        This is a limitation by Tremor Games not by me.
        """
        message_meta = namedtuple('message', ['msg_id', 'is_read', 'msg_from', 'subject', 'date'])
        response = self.ses.get('http://www.tremorgames.com/index.php?action=messages',
                                headers=self.headers)
        # Use beautifulsoup to scrape all the messages in the inbox
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', attrs={'style': 'border:1px solid #E4E4E3;'})
        # Get all rows with messages in, ignoring the header
        message_infos = table.find_all('tr', attrs={'valign': 'top'})[1:]
        re_string = r"https?:\/\/www\.tremorgames\.com\/message\/([0-9]*)\/.*\.html"
        all_message_info = []

        for message_info in message_infos:
            read_td, subject_td, date_td = message_info.find_all('td')[:3]
            msg_id = re.search(re_string, subject_td.find('a')['href']).group(1)
            is_read = read_td.find('img').get('alt') != 'The Message is Unread'
            msg_from = subject_td.find('span', attrs={'class': 'messagefrom'}).text
            subject = subject_td.find('span', attrs={'class': 'messagesubject'}).text
            date = date_td.find('span', attrs={'class': 'messagedate'}).text
            all_message_info.append(message_meta(msg_id, is_read, msg_from, subject, date))

        return all_message_info

    def get_message(self, msg_id):
        "Get information for a single message from it's id"
        message_meta = namedtuple('message', ['msg_from', 'subject', 'body', 'date'])

        url = 'http://www.tremorgames.com/message/{}/message.html'.format(msg_id)
        response = self.ses.get(url, headers=self.headers)
        soup = BeautifulSoup(response.text, "lxml")

        msg_from = soup.find('a', attrs={'title': 'Click to View Profile'}).text
        subject = soup.find('div', attrs={'class': 'main_section_headers'}).find('b').text
        body = soup.find('div', attrs={'class': 'box_round private_message'}).text.strip()
        date = soup.find('div', attrs={'class': 'private_message_main'}).find('b').text

        return message_meta(msg_from, subject, body, date)

    def send_message(self, username, subject, body):
        "Function to send message"
        url = 'http://www.tremorgames.com/index.php?action=sendmessage'
        payload = {'tousername': username,
                   'messagesubject': subject,
                   'messagebody': body}

        response = self.ses.post(url, data=payload, headers=self.headers)
        return self.check_if_logged_in(response) and 'Invalid User' not in response.text

    def delete_message(self, msg_id):
        "Delete a message given the message id"
        url = 'http://www.tremorgames.com/delete-message/{}/message.html'.format(msg_id)
        response = self.ses.get(url, headers=self.headers)
        return self.check_if_logged_in(response)

    def mark_message_read(self, msg_id):
        "Mark a message as read given the message id"
        url = 'http://www.tremorgames.com/message/{}/message.html'.format(msg_id)
        response = self.ses.get(url, headers=self.headers)
        return self.check_if_logged_in(response)

    def get_user_info(self):
        "Get username and user id for the logged in user"
        url = 'http://www.tremorgames.com/index.php?action=tos'
        response = self.ses.get(url, headers=self.headers)

        soup = BeautifulSoup(response.text, 'html.parser')
        user_info = soup.find('div', attrs={'class': 'wbox_topright'}).find('a')

        username = user_info.text
        re_string = r"https?:\/\/www\.tremorgames\.com\/profiles\/([0-9]*)\/.*\.html"
        user_id = re.search(re_string, user_info['href']).group(1)
        return username, user_id

    def get_coins(self):
        "Get the amount of coins the user has"
        url = 'http://www.tremorgames.com/achievements/ajax_getusercoins.php'
        response = self.ses.get(url, headers=self.headers)
        return response.text

    def get_referrals(self):
        "Get the referrals for the logged in user"
        url = 'http://www.tremorgames.com/?action=viewreferrals'
        response = self.ses.get(url, headers=self.headers)

        soup = BeautifulSoup(response.text, 'lxml')
        table_body = soup.find('table', attrs={'id': 'reftable'}).find('tbody')
        all_rows = table_body.find_all('tr')

        user_info = namedtuple('user_info',
                               ['username', 'coins_earned_me', 'date_join', 'date_last_login'])

        users_info = []

        for row in all_rows:
            username, coins, date_join, date_last_login, = row.find_all('td')[1:]
            username_str = username.text
            coins_earned_me = float(coins.text)
            date_join_obj = datetime.strptime(date_join.text, "%b %d %Y")
            # Maybe a user joined but didn't login (didn't confirm email I think)
            if date_last_login.text == '-':
                date_last_login_obj = '-'
            else:
                date_last_login_obj = datetime.strptime(date_last_login.text, "%b %d %Y")

            users_info.append(user_info(username_str, coins_earned_me, date_join_obj,
                                        date_last_login_obj))

        return users_info

    def get_server_time(self):
        "Get the time on the server from the webpage"
        # ToS has a low amount of information in the request, not that it matters
        url = "http://www.tremorgames.com/index.php?action=tos"
        # Send request to webpage
        request = self.ses.get(url, headers=self.headers)
        soup = BeautifulSoup(request.text, "lxml")
        # Find the time div
        server_time = soup.find_all("div")
        # It is the second from last div in all pages
        server_time_str = server_time[-2].text
        server_time_str = server_time_str[server_time_str.find(':')+2:server_time_str.find(',')+6]
        server_time_obj = datetime.strptime(server_time_str, "%B %d, %Y")
        return server_time_obj
