"""Storage backends: root / shizuku / direct."""

from __future__ import annotations

import logging
import shlex
from abc import ABC, abstractmethod
from pathlib import Path

from ..errors import NoStorageAccessError, ShizukuNotRunningError
from ..fs_utils import android_sdk_int, has_root, has_shizuku, is_android, python_unzip, run_shell

LOG = logging.getLogger(__name__)


class StorageBackend(ABC):
    name: str = "base"

    @abstractmethod
    def can_write(self, path: str) -> bool: ...

    @abstractmethod
    def unzip_replace(self, zip_path: str, target_dir: str) -> bool: ...

    @abstractmethod
    def copy_file(self, src: str, dst: str) -> bool: ...

    @abstractmethod
    def copy_tree(self, src: str, dst: str) -> bool: ...

    @abstractmethod
    def delete(self, path: str) -> bool: ...

    @abstractmethod
    def exists(self, path: str) -> bool: ...

    @abstractmethod
    def mkdir(self, path: str) -> bool: ...

    def _shell_ok(self, output: str) -> bool:
        return "true" in output.lower()


class RootBackend(StorageBackend):
    name = "root"

    def _su(self, inner: str) -> tuple[int, str, str]:
        q = shlex.quote(inner)
        for cmd in (f"su -c {q}", f"su 0 sh -c {q}"):
            code, out, err = run_shell(cmd)
            if code == 0 or out or err:
                return code, out, err
        return -1, "", "su failed"

    def can_write(self, path: str) -> bool:
        code, out, _ = self._su(f"test -w {shlex.quote(path)} && echo true || echo false")
        return code == 0 and self._shell_ok(out)

    def unzip_replace(self, zip_path: str, target_dir: str) -> bool:
        self.mkdir(target_dir)
        inner = (
            f'if unzip -o {shlex.quote(zip_path)} -d {shlex.quote(target_dir)}; '
            f"then echo true; else echo false; fi"
        )
        code, out, err = self._su(inner)
        LOG.info("root unzip: code=%s out=%s err=%s", code, out.strip(), err.strip())
        return self._shell_ok(out + err)

    def copy_file(self, src: str, dst: str) -> bool:
        inner = (
            f"mkdir -p $(dirname {shlex.quote(dst)}) && "
            f"cp -f {shlex.quote(src)} {shlex.quote(dst)} && echo true || echo false"
        )
        _, out, err = self._su(inner)
        return self._shell_ok(out + err)

    def copy_tree(self, src: str, dst: str) -> bool:
        inner = (
            f"mkdir -p {shlex.quote(dst)} && "
            f"cp -rf {shlex.quote(src)}/. {shlex.quote(dst)}/ && echo true || echo false"
        )
        _, out, err = self._su(inner)
        return self._shell_ok(out + err)

    def delete(self, path: str) -> bool:
        inner = f"rm -rf {shlex.quote(path)} && echo true || echo false"
        _, out, err = self._su(inner)
        return self._shell_ok(out + err)

    def exists(self, path: str) -> bool:
        _, out, _ = self._su(f"test -e {shlex.quote(path)} && echo true || echo false")
        return self._shell_ok(out)

    def mkdir(self, path: str) -> bool:
        _, out, err = self._su(f"mkdir -p {shlex.quote(path)} && echo true || echo false")
        return self._shell_ok(out + err)


class ShizukuBackend(StorageBackend):
    name = "shizuku"

    def _run(self, inner: str) -> tuple[int, str, str]:
        q = shlex.quote(inner)
        attempts = []
        if has_shizuku():
            attempts.append(f"shizuku -r {q}")
        attempts.append(f'rish -c {q}')
        for cmd in attempts:
            code, out, err = run_shell(cmd)
            if code == 0 or self._shell_ok(out + err):
                return code, out, err
        return -1, "", "shizuku/rish tidak tersedia"

    def can_write(self, path: str) -> bool:
        if not has_shizuku():
            raise ShizukuNotRunningError("Shizuku tidak terdeteksi. Jalankan Shizuku + pair rish.")
        _, out, _ = self._run(f"test -w {shlex.quote(path)} && echo true || echo false")
        return self._shell_ok(out)

    def unzip_replace(self, zip_path: str, target_dir: str) -> bool:
        if not has_shizuku():
            raise ShizukuNotRunningError("Shizuku tidak jalan")
        self.mkdir(target_dir)
        inner = (
            f'if unzip -o {shlex.quote(zip_path)} -d {shlex.quote(target_dir)}; '
            f"then echo true; else echo false; fi"
        )
        _, out, err = self._run(inner)
        return self._shell_ok(out + err)

    def copy_file(self, src: str, dst: str) -> bool:
        inner = (
            f"mkdir -p $(dirname {shlex.quote(dst)}) && "
            f"cp -f {shlex.quote(src)} {shlex.quote(dst)} && echo true || echo false"
        )
        _, out, err = self._run(inner)
        return self._shell_ok(out + err)

    def copy_tree(self, src: str, dst: str) -> bool:
        inner = (
            f"mkdir -p {shlex.quote(dst)} && "
            f"cp -rf {shlex.quote(src)}/. {shlex.quote(dst)}/ && echo true || echo false"
        )
        _, out, err = self._run(inner)
        return self._shell_ok(out + err)

    def delete(self, path: str) -> bool:
        inner = f"rm -rf {shlex.quote(path)} && echo true || echo false"
        _, out, err = self._run(inner)
        return self._shell_ok(out + err)

    def exists(self, path: str) -> bool:
        _, out, _ = self._run(f"test -e {shlex.quote(path)} && echo true || echo false")
        return self._shell_ok(out)

    def mkdir(self, path: str) -> bool:
        _, out, err = self._run(f"mkdir -p {shlex.quote(path)} && echo true || echo false")
        return self._shell_ok(out + err)


class DirectBackend(StorageBackend):
    """Python zip / shutil — works on Android <=10 or when path is writable."""

    name = "direct"

    def can_write(self, path: str) -> bool:
        p = Path(path)
        try:
            p.mkdir(parents=True, exist_ok=True)
            test = p / ".write_test"
            test.write_text("ok", encoding="utf-8")
            test.unlink(missing_ok=True)
            return True
        except OSError:
            return False

    def unzip_replace(self, zip_path: str, target_dir: str) -> bool:
        return python_unzip(Path(zip_path), Path(target_dir))

    def copy_file(self, src: str, dst: str) -> bool:
        try:
            Path(dst).parent.mkdir(parents=True, exist_ok=True)
            import shutil

            shutil.copy2(src, dst)
            return True
        except OSError as e:
            LOG.error("copy_file: %s", e)
            return False

    def copy_tree(self, src: str, dst: str) -> bool:
        try:
            import shutil

            Path(dst).mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dst, dirs_exist_ok=True)
            return True
        except OSError as e:
            LOG.error("copy_tree: %s", e)
            return False

    def delete(self, path: str) -> bool:
        try:
            p = Path(path)
            if p.is_dir():
                import shutil

                shutil.rmtree(p)
            elif p.exists():
                p.unlink()
            return True
        except OSError as e:
            LOG.error("delete: %s", e)
            return False

    def exists(self, path: str) -> bool:
        return Path(path).exists()

    def mkdir(self, path: str) -> bool:
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            return True
        except OSError:
            return False


def pick_backend(cfg: dict, force_mode: str | None = None) -> StorageBackend:
    access = cfg.get("access", {})
    mode = (force_mode or access.get("mode", "auto")).lower()
    fallback = bool(access.get("fallback", True))
    noroot = access.get("noroot_backend", "shizuku").lower()

    order: list[str] = []
    if mode == "root":
        order = ["root"]
    elif mode == "noroot":
        order = [noroot, "direct"]
    else:
        if has_root():
            order.append("root")
        if noroot == "shizuku" or mode == "auto":
            order.append("shizuku")
        order.append("direct")

    seen: set[str] = set()
    errors: list[str] = []
    for name in order:
        if name in seen:
            continue
        seen.add(name)
        try:
            backend = _make_backend(name)
            if name == "direct" and is_android() and android_sdk_int() >= 30:
                errors.append("direct: Android 11+ tanpa root/Shizuku tidak didukung")
                continue
            return backend
        except NoStorageAccessError as e:
            errors.append(f"{name}: {e}")
            if not fallback:
                raise
    raise NoStorageAccessError(
        "Tidak ada backend akses storage yang tersedia.\n"
        + "\n".join(f"  - {e}" for e in errors)
        + "\nInstall root (su) atau Shizuku + rish untuk Android 11+."
    )


def _make_backend(name: str) -> StorageBackend:
    if name == "root":
        if not has_root():
            raise NoStorageAccessError("su/root tidak tersedia")
        return RootBackend()
    if name == "shizuku":
        if not has_shizuku():
            raise NoStorageAccessError("Shizuku tidak terdeteksi")
        return ShizukuBackend()
    if name == "direct":
        return DirectBackend()
    raise NoStorageAccessError(f"Backend tidak dikenal: {name}")
