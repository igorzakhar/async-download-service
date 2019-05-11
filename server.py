import asyncio

from aiohttp import web
import aiofiles


async def archivate(request):
    target_dir = request.match_info['archive_hash']
    cmd = f'zip -r - . -i test_photos/{target_dir}/* -j'
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    resp = web.StreamResponse()
    resp.headers['Content-Type'] = 'application/zip'
    resp.headers['Content-Disposition'] = 'attachment; filename="archive.zip"'

    await resp.prepare(request)

    chunk_size_bytes = 1
    while True:
        archive_chunk = await process.stdout.read(chunk_size_bytes)
        if not archive_chunk:
            break
        await resp.write(archive_chunk)

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
