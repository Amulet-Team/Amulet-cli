from __future__ import annotations

from typing import Tuple

VERSION_PY_CONTENT = """
VERSION_NUMBER = ({ver_major}, {ver_minor}, {ver_patch})
VERSION_INT = {ver_int}
VERSION_STAGE = "{ver_stage}"
VERSION_STRING = f"{{'.'.join((str(n) for n in VERSION_NUMBER))}}-{{VERSION_STAGE}}"

if __debug__:
    VERSION_STRING += "-source"
"""


def generate_version_py(
    version_number: Tuple[int, int, int] = None,
    version_int: int = -1,
    version_stage: str = "DEV",
    save_path: str = "version_test.py",
):
    if not version_number:
        version_number = (0, 0, 0)

    version_major, version_minor, version_patch = version_number

    fp = open(save_path, "w")
    fp.write(
        VERSION_PY_CONTENT.format(
            ver_major=version_major,
            ver_minor=version_minor,
            ver_patch=version_patch,
            ver_int=version_int,
            ver_stage=version_stage,
        )
    )
    fp.close()


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="Generate a version.py file for an Amulet release"
    )
    parser.add_argument(
        "-i",
        "--int",
        default=-1,
        action="store",
        help="The internal version integer to generate",
    )
    parser.add_argument(
        "-s",
        "--stage",
        choices=["DEV", "ALPHA", "BETA", "RC", "RELEASE"],
        default="DEV",
        action="store",
        help="The version stage to generate",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="store",
        type=int,
        nargs=3,
        metavar=("MAJOR", "MINOR", "PATCH"),
        required=True,
    )
    parser.add_argument(
        "-o",
        "--output",
        action="store",
        default="version_test.py",
        help="The file to write version information to",
    )

    args = parser.parse_args()

    generate_version_py(args.version, args.int, args.stage, args.output)
