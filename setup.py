"""Backwards-compatible setup.py for clipforge."""

from setuptools import setup, find_packages

setup(
    name="clipforge",
    version="0.1.0",
    description=(
        "AI-powered short-form video generator. Create viral YouTube Shorts "
        "& TikTok videos with AI-generated visuals, natural voices, and "
        "cinematic effects."
    ),
    author="DarkPancakes",
    url="https://github.com/DarkPancakes/clipforge",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "edge-tts>=6.1.0",
        "fal-client>=0.4.0",
        "requests>=2.28.0",
        "click>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "clipforge=clipforge.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Multimedia :: Video",
    ],
)
