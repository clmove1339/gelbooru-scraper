import aiohttp
import asyncio
import aiofiles
import os
from datetime import datetime

class ImageDownloader:
    BASE_LINK = 'https://gelbooru.com/'

    def __init__(self, tags: str, num_images: int):
        self.tags = tags
        self.num_images = num_images
        # Get the current date in YYYY-MM-DD format
        date_str = datetime.now().strftime('%Y-%m-%d')
        # Append the date to the folder name
        self.folder_name = f"{tags.replace(':', ' ')}_{date_str}"
        self.pid = 0
        self.images_downloaded = 0
        self.images_required = 0
        self.semaphore = asyncio.Semaphore(10)

        if not os.path.exists(self.folder_name):
            os.makedirs(self.folder_name)

    def build_url(self, pid: int = 0) -> str:
        return f'{self.BASE_LINK}/index.php?page=dapi&json=1&s=post&q=index&limit=100&tags={self.tags}&pid={pid}'

    async def fetch_json(self, session: aiohttp.ClientSession, url: str) -> dict:
        async with session.get(url) as response:
            return await response.json()

    async def download_image(self, session: aiohttp.ClientSession, url: str, filename: str, hash: str):
        async with self.semaphore, session.get(url) as response:
            if response.status == 200:
                async with aiofiles.open(filename, mode='wb') as f:
                    await f.write(await response.read())
                    self.images_downloaded += 1
                    print(f'[{self.images_downloaded}/{self.num_images}] {hash} downloaded successfully.')
                return True
                
        self.images_downloaded += 1
        print(f'[{self.images_downloaded}/{self.num_images}] {hash} download failed.')
        return False

    async def run(self):
        async with aiohttp.ClientSession() as session:
            tasks = []
            results = []

            while self.images_required < self.num_images:
                json_response = await self.fetch_json(session, self.build_url(self.pid))

                total_images = int(json_response.get('@attributes', {}).get('count', 0))
                if total_images < self.num_images:
                    self.num_images = total_images
                    print(f'Only found {total_images} images.')

                posts = json_response.get('post', [])
                if not posts:
                    print('No more posts to process.')
                    break

                for post in posts:
                    if self.images_required >= self.num_images:
                        break  # Break the loop if the desired number of images has been reached.

                    file_url = post['file_url']
                    filename = os.path.join(self.folder_name, post['image'].replace('.webm', '.mp4'))
                    task = asyncio.create_task(self.download_image(session, file_url, filename, post['md5']))
                    tasks.append(task)
                    self.images_required += 1  # Increment the counter after creating each task.

                # Wait for all tasks to complete before continuing to the next page.
                results = await asyncio.gather(*tasks)
                tasks = []  # Clear the list of tasks for the next iteration.
                self.pid += 1

            successful_downloads = sum(result for result in results if result)
            print(f'Successfully downloaded {successful_downloads} images.')

if __name__ == '__main__':
    num_images = int(input('Введите количество изображений для загрузки: '))
    tag_images = input('Введите теги: ')

    downloader = ImageDownloader(tag_images, num_images)
    asyncio.run(downloader.run())
