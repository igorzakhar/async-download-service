import asyncio
import logging
import os.path

from aiohttp import web
import aiofiles


logging.basicConfig(level=logging.DEBUG, format='%(message)s')


async def archivate(request):
    base_dir = 'test_photos'
    archive_dir = request.match_info['archive_hash']
    archive_path = os.path.join(base_dir, archive_dir)

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

    response_delay = 0.1
    chunk_size_bytes = 8192
    while True:
        archive_chunk = await process.stdout.read(chunk_size_bytes)
        logging.debug('Sending archive chunk ...')
        if not archive_chunk:
            break
        await resp.write(archive_chunk)
        await asyncio.sleep(response_delay)
    return resp


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archivate),
    ])
    web.run_app(app)
