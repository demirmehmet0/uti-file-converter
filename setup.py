import setuptools

setuptools.setup(
    name="FileConverter",
    version="0.0.1",
    author="DigiNova",
    author_email='info@diginova.com.tr',
    description="Document/image format conversion component for NovaVision",
    url='https://github.com/novavision-ai/com-fileconverter',
    license='MIT',
    install_requires=[
        'sdk',
        'Pillow',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=[
        'components.FileConverter',
        'components.FileConverter.configs',
        'components.FileConverter.executors',
        'components.FileConverter.models',
        'components.FileConverter.utils'
    ],
    package_dir={'components.FileConverter': 'src'},
    python_requires=">=3.8"
)
