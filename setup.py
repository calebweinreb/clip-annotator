import setuptools
import versioneer

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setuptools.setup(
    name="clip-annotator",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
)
