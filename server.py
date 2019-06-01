import asyncio
import argparse
from functools import partial
import logging
import os

from aiohttp import web
import aiofiles


async def get_archive_process(path_source_dir):
    cmd = ['zip', '-jr', '-', path_source_dir]
    archive_process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    return archive_process


async def archivate(request, storage_dir, delay_send, chunk_size_bytes=8192):
    archive_dir = request.match_info['archive_hash']
    path_source_dir = os.path.join(storage_dir, archive_dir)

    if not os.path.exists(path_source_dir):
        raise web.HTTPNotFound(
            text='Archive does not exist or has been deleted.'
        )

    archive_process = await get_archive_process(path_source_dir)

    resp = web.StreamResponse()
    resp.headers['Content-Type'] = 'application/zip'
    resp.headers['Content-Disposition'] = 'attachment; filename="archive.zip"'

    await resp.prepare(request)

    try:
        while True:
            archive_chunk = await archive_process.stdout.read(chunk_size_bytes)
            logging.debug('Sending archive chunk ...')
            if not archive_chunk:
                break
            await resp.write(archive_chunk)
            await asyncio.sleep(delay_send)
    except asyncio.CancelledError:
        raise
    finally:
        archive_process.kill()
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
        '-P', '--port', default=8080, help='TCP/IP port for HTTP server.'
    )
    parser.add_argument(
        '-D', '--dir', default=f'{os.getcwd()}/test_photos',
        help='File storage directory.'
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
