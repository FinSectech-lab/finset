"""Explicit public-source allowlist: never ship runtime data or credentials."""
import hashlib
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT_FILES = {'README.md', 'COMPARISON.md', 'MACOS_TEST.md', 'LICENSE', 'pyproject.toml', 'install.sh', 'uninstall.sh', 'r0env.sh', 'package.py', '.gitignore'}


def main():
    root = Path(__file__).resolve().parent
    output = root.parent / 'r0env3-macos.zip'
    sources = [p for p in root.rglob('*') if p.is_file() and (
        p.relative_to(root).as_posix() in ROOT_FILES or
        (p.relative_to(root).parts[0] in {'r0env', 'tests'} and p.suffix == '.py') or
        p.relative_to(root).as_posix() == '.github/workflows/macos.yml')]
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for path in sorted(sources):
            archive.write(path, Path('r0env3') / path.relative_to(root))
    with ZipFile(output) as archive:
        assert archive.testzip() is None
        for path in sources:
            assert archive.read(str(Path('r0env3') / path.relative_to(root))) == path.read_bytes()
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.zip.sha256').write_text(f'{digest}  {output.name}\n')
    print(f'{output}\n{len(sources)} files; CRC/source verification passed\nSHA256 {digest}')


if __name__ == '__main__':
    main()
