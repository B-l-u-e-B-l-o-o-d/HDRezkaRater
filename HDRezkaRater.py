import asyncio
from argparse import ArgumentParser
from rezka_rater import Rater


def parse_arguments():
    parser = ArgumentParser(prog='HDRezkaRater', description='Инструмент для массовой накрутки оценки на HDRezka')
    parser.add_argument('--url', '-u', type=str, required=True, help='URL фильма/сериала')
    parser.add_argument('--rate', '-r', type=int, required=True, help='Оценка фильму/сериалу')
    parser.add_argument('--proxies-path', '-p', type=str, required=True, help='Путь к файлу прокси')
    parser.add_argument('--threads', '-t', type=int, required=True, help='Кол-во потоков')

    return parser.parse_args()


def parse_proxies(proxies_path):
    proxies = []

    with open(proxies_path, 'r', encoding='utf-8') as proxies_file:
        for proxy in proxies_file:
            proxy = proxy.strip()
            if len(proxy) > 5:
                proxies.append(proxy)

    return proxies


async def main():
    args = parse_arguments()

    url = args.url
    rate_num = args.rate
    proxies_path = args.proxies_path
    threads_count = args.threads

    proxies = parse_proxies(proxies_path)

    rater = Rater(threads_count)
    tasks = [rater.rate(url, rate_num, proxy) for proxy in proxies]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    errors_count = results.count(False)
    success_count = results.count(True)

    print('DONE\n'
          f'Errors: {errors_count}\n'
          f'Success: {success_count}')

    await rater.close()

if __name__ == "__main__":
    asyncio.run(main())
