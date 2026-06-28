from setuptools import setup, find_packages

setup(
    name="newton-x",
    version="2.0.0",
    description="AI Cognitive Boundary System — external brain for AI agents",
    author="DanDingBenShao",
    packages=find_packages(),
    install_requires=["rich>=13.0.0"],
    entry_points={
        "console_scripts": [
            "newton=core.cli:main",
        ],
    },
    python_requires=">=3.10",
)
