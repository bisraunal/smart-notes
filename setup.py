from setuptools import setup, find_packages

setup(
    name="smartnotes",
    version="1.0.0",
    description="Akıllı Not & Bilgi Yöneticisi — Etiketle, ara, bağlantıla.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="you@example.com",
    url="https://github.com/yourusername/smart-notes",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0",
        "rich>=13.0",
    ],
    entry_points={
        "console_scripts": [
            "smartnotes=smartnotes.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Office/Business :: Groupware",
    ],
)
