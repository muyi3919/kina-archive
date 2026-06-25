from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="kina-archive",
    version="1.1.1",
    author="kina漫记",
    author_email="shuzhishaoju@gmail.com",
    description="网页时光机 - 截图对比追踪工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/muyi3919/kina-archive",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "Pillow>=9.0.0",
        "requests>=2.25.0",
    ],
    entry_points={
        "console_scripts": [
            "kina-archive=kina_archive.cli:main",
        ],
    },
)