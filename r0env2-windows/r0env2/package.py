"""Build a portable source ZIP, excluding local environments and user data."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


def main():
    root = Path(__file__).resolve().parent
    output = root.parent / 'r0env2-windows.zip'
    skip = {'.git', '.venv', '__pycache__', '.pytest_cache', 'build', 'dist', '.codebase-memory', 'acceptance-results'}
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob('*')):
            relative = path.relative_to(root)
            if not path.is_file() or any(part in skip or part.endswith('.egg-info') for part in relative.parts):
                continue
            if path.suffix in {'.pyc', '.log', '.zip', '.json', '.etl', '.pcap', '.pcapng'}:
                continue
            archive.write(path, Path('r0env2') / relative)
    print(output)


if __name__ == '__main__':
    main()
