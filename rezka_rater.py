import asyncio
import aiohttp
from aiohttp import web
from py_random_useragent import UserAgent
from lxml.html import fromstring
import json
import logging

logging.basicConfig(level=logging.ERROR)


class RateError(Exception):
    pass


class UserHashError(Exception):
    pass


class WrongAnswer(Exception):
    pass


class Rater:
    def __init__(self, threads_limit=10**6):
        self.connector = aiohttp.TCPConnector()
        self.UA = UserAgent()
        self.semaphore = asyncio.Semaphore(threads_limit)

    async def _fetch(self,
                     session,
                     url,
                     headers,
                     proxies):
        async with self.semaphore:
            resp_text = None

            async with session.get(url, headers=headers, timeout=15, proxy=proxies) as resp:
                status = resp.status

                if status == 200:
                    resp_text = await resp.text()

            if resp_text:
                return resp_text

            else:
                raise WrongAnswer(f'Server answer: {status}')

    @staticmethod
    def _get_headers(user_agent, headers_name):
        headers = {
            'user_hash': {
                    'Host': 'hdrezka.inc',
                    'Sec-Ch-Ua': '"Not-A.Brand";v="24", "Chromium";v="146"', 'Sec-Ch-Ua-Mobile': '?0',
                    'Sec-Ch-Ua-Platform': '"Windows"',
                    'Accept-Language': 'ru-RU,ru;q=0.9',
                    'Upgrade-Insecure-Requests': '1',
                    'User-Agent': user_agent,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-User': '?1',
                    'Sec-Fetch-Dest': 'document', 'Accept-Encoding': 'gzip, deflate, br', 'Priority': 'u=0, i'
            },

            'rate':
                {
                    'Host': 'hdrezka.inc',
                    'Sec-Ch-Ua-Platform': '"Windows"',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept-Language': 'ru-RU,ru;q=0.9',
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'Sec-Ch-Ua': '"Not-A.Brand";v="24", "Chromium";v="146"',
                    'User-Agent': user_agent,
                    'Sec-Ch-Ua-Mobile': '?0', 'Sec-Fetch-Site': 'same-origin', 'Sec-Fetch-Mode': 'cors',
                    'Sec-Fetch-Dest': 'empty', 'Accept-Encoding': 'gzip, deflate, br', 'Priority': 'u=1, i'
                 }
        }[headers_name]

        return headers

    async def _fetch_user_hash(self, session, user_agent, proxies, url):
        headers = self._get_headers(user_agent, 'user_hash')

        resp_text = await self._fetch(session, url, headers=headers, proxies=proxies)

        try:
            resp_tree = fromstring(resp_text)

            user_hash = resp_tree.xpath('//*[@name="user_hash"]/@value')[0]

        except Exception as e:
            raise UserHashError(f'Exception: {e}\nResponse: {resp_text}')

        return user_hash

    async def _fetch_rate(self, session, user_agent, proxies, rate_num, news_id, user_hash):
        url = ('https://hdrezka.inc/engine/ajax/controller.php?'
               f'mod=rating&go_rate={rate_num}&news_id={news_id}&skin=rezka&user_hash={user_hash}')
        headers = self._get_headers(user_agent, 'rate')

        resp_text = await self._fetch(session, url, headers=headers, proxies=proxies)

        try:
            resp_json = json.loads(resp_text)

            if ('success' not in resp_json) or (not resp_json['success']):
                raise RateError(f'Not success rate\nResponse: {resp_json}')

            return True

        except Exception as e:
            raise RateError(f'Exception: {e}\nResponse: {resp_text}')

    async def rate(self, url, rate_num, proxies=None):
        try:
            async with aiohttp.ClientSession(connector=self.connector, connector_owner=False) as session:
                user_agent = self.UA.get_ua()

                news_id = url.split('/')[-1].split('-')[0]
                user_hash = await self._fetch_user_hash(session, user_agent, proxies, url)

                await self._fetch_rate(session, user_agent, proxies, rate_num, news_id, user_hash)

                return True

        except Exception as e:
            logging.error(e)

            return False

    async def close(self):
        await self.connector.close()
