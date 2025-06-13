from setuptools import setup, find_packages

setup(
    name='yt2spotify',
    version='0.1.0',
    description='Sync YouTube playlists to Spotify playlists',
    author='Your Name',
    packages=find_packages(),
    install_requires=[
        'spotipy',
        'yt-dlp',
        'python-dotenv',
        'tqdm',
        'aiohttp',
        'pytest',
        'pytest-cov',
        'rapidfuzz',
    ],
    entry_points={
        'console_scripts': [
            'yt2spotify=yt2spotify.cli:main',
        ],
    },
    python_requires='>=3.8',
)
