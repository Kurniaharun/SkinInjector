"""Custom exceptions for the injector."""


class InjectorError(Exception):
    """Base error."""


class NoMLBBInstalledError(InjectorError):
    """No supported MLBB package found."""


class NoStorageAccessError(InjectorError):
    """Cannot write to Android/data (need root or Shizuku)."""


class DownloadError(InjectorError):
    """Download failed after retries."""


class ZipInvalidError(InjectorError):
    """Downloaded file is not a valid skin ZIP."""


class InjectFailedError(InjectorError):
    """Unzip/copy to game folder failed."""


class BackupNotFoundError(InjectorError):
    """No backup exists for restore."""


class ShizukuNotRunningError(InjectorError):
    """Shizuku is not available."""


class ApiError(InjectorError):
    """Remote API request failed."""


class ConfigError(InjectorError):
    """Invalid or missing configuration."""
