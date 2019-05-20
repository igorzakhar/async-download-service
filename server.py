import asyncio
import argparse
from functools import partial
import logging
import os.path

from aiohttp import web
import aiofiles


async def archivate(request, storage_dir, delay_send, chunk_size_bytes=8192):
    archive_dir = request.match_info['archive_hash']
    archive_path = os.path.join(storage_dir, archive_dir)

    if not os.path.exists(archive_path):
        raise web.HTTPNotFound(text='Архив не существует или был удален')

    process = await asyncio.create_subprocess_shell(
        f'zip -r - {archive_path} -j',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    resp = web.StreamResponse()
    resp.headers['Content-Type'] = 'application/zip'
    resp.headers['Content-Disposition'] = 'attachment; filename="archive.zip"'

    await resp.prepare(request)

    try:
        while True:
            archive_chunk = await process.stdout.read(chunk_size_bytes)
            logging.debug('Sending archive chunk ...')
            if not archive_chunk:
                break
            await resp.write(archive_chunk)
            await asyncio.sleep(delay_send)
    except asyncio.CancelledError:
        process.kill()
        raise
    finally:
        resp.force_close()

    return resp


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


def process_args():
    parser = argparse.ArgumentParser(
        description='Create archive with user files and download it on demand.'
    )
    parser.add_argument(
        '-H', '--host', default='0.0.0.0', help='TCP/IP host for HTTP server.'
    )
    parser.add_argument(
        '-P', '--port', default=8080, help="TCP/IP port for HTTP server."
    )
    parser.add_argument(
        '-D', '--dir', default='test_photos', help='File storage directory.'
    )
    parser.add_argument(
        '-d', '--delay', default=0.0, type=float,
        help='Delay between sending chunks of an archive file in seconds.'
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='Output detailed sending info'
    )

    return parser.parse_args()


def main():
    args = process_args()

    logging_level = logging.INFO
    if args.verbose:
        logging_level = logging.DEBUG
    logging.basicConfig(level=logging_level, format='%(message)s')

    archive_handler = partial(
        archivate, storage_dir=args.dir, delay_send=args.delay
    )

    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive_handler),
    ])
    web.run_app(app, host=args.host, port=args.port)


if __name__ == '__main__':
    main()
