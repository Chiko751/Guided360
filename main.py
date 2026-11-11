import asyncio
import datetime
import os

import decky

from guided360 import accounts, power
from guided360.bluetooth import list_devices, read_controllers, set_connected
from guided360.frost.service import FrostService
from guided360.heroic import HeroicLibrary, heroic_cache_dirs
from guided360.home_errors import FILE_NAME, append_log, start_entry
from guided360.kv import KvStore
from guided360.store_lookup import RegistryCache, key_for_appid, store_for_appid

DATA_PATH = os.path.join(decky.DECKY_PLUGIN_SETTINGS_DIR, "data.json")
KV = KvStore(DATA_PATH)
REGISTRY = RegistryCache(
    os.path.join(decky.DECKY_USER_HOME, ".local", "share", "unifideck", "shortcuts_registry.json")
)
HEROIC = HeroicLibrary(heroic_cache_dirs(decky.DECKY_USER_HOME))


class Plugin:
    def _frost_service(self):
        if not getattr(self, "_frost", None):
            self._frost = FrostService(decky.DECKY_USER_HOME, os.path.dirname(os.path.abspath(__file__)))
        return self._frost

    async def frost_prepare(self, request_id: str, frame):
        return await self._frost_service().prepare(request_id, frame)

    async def frost_environment(self):
        return await self._frost_service().environment()

    async def frost_present(self, request_id: str, frame):
        return await self._frost_service().present(request_id, frame)

    async def frost_activate(self, request_id: str, key: str, sequence: int, frame):
        return await self._frost_service().activate(request_id, key, sequence, frame)

    async def frost_update(self, token: str, sequence: int, frame):
        return await self._frost_service().update(token, sequence, frame)

    async def frost_renew(self, token: str):
        return await self._frost_service().renew(token)

    async def frost_release(self, token: str):
        await self._frost_service().release(token)

    async def frost_cancel(self, request_id: str):
        await self._frost_service().cancel(request_id)

    async def kv_get(self, key: str):
        return KV.get(key)

    async def kv_set(self, key: str, value) -> None:
        KV.set(key, value)

    async def kv_delete(self, key: str) -> None:
        KV.delete(key)

    async def kv_delete_prefix(self, prefix: str) -> int:
        return KV.delete_prefix(prefix)

    async def get_store(self, appid: int):
        try:
            return store_for_appid(REGISTRY.get(), int(appid))
        except Exception:
            decky.logger.exception("[guided360] get_store failed")
            return None

    async def get_unifideck_key(self, appid: int):
        try:
            return key_for_appid(REGISTRY.get(), int(appid))
        except Exception:
            decky.logger.exception("[guided360] get_unifideck_key failed")
            return None

    async def get_heroic_description(self, runner: str, app_name: str):
        try:
            return HEROIC.description(str(runner), str(app_name))
        except Exception:
            decky.logger.exception("[guided360] get_heroic_description failed")
            return None

    async def get_controller_batteries(self):
        try:
            return await asyncio.to_thread(read_controllers, log=lambda reason: decky.logger.warning(f"[guided360] controller batteries: {reason}"))
        except Exception:
            decky.logger.exception("[guided360] get_controller_batteries failed")
            return []

    async def list_bluetooth_devices(self, scan: bool = False):
        try:
            return await asyncio.to_thread(list_devices, 6 if scan else 0, log=lambda reason: decky.logger.warning(f"[guided360] bluetooth: {reason}"))
        except Exception:
            decky.logger.exception("[guided360] list_bluetooth_devices failed")
            return []

    async def set_bluetooth_connected(self, mac: str, connect: bool):
        try:
            return await asyncio.to_thread(set_connected, str(mac), bool(connect), log=lambda reason: decky.logger.warning(f"[guided360] bluetooth: {reason}"))
        except Exception:
            decky.logger.exception("[guided360] set_bluetooth_connected failed")
            return False

    async def list_steam_accounts(self):
        # [{"steamId", "account", "persona", "mostRecent"}] from Steam's loginusers.vdf.
        try:
            return await asyncio.to_thread(accounts.list_accounts, decky.DECKY_USER_HOME)
        except Exception:
            decky.logger.exception("[guided360] list_steam_accounts failed")
            return []

    async def switch_steam_account(self, account: str):
        # Shuts Steam down, sets AutoLoginUser once Steam has exited; Steam then starts as that account.
        try:
            return await asyncio.to_thread(accounts.switch_account, decky.DECKY_USER_HOME, getattr(decky, "DECKY_USER", None), str(account))
        except Exception:
            decky.logger.exception("[guided360] switch_steam_account failed")
            return False

    async def power_capabilities(self):
        try:
            return power.capabilities()
        except Exception:
            return ["sleep", "restart", "shutdown"]

    async def power_action(self, action: str):
        try:
            return await asyncio.to_thread(power.run, str(action), lambda reason: decky.logger.warning(f"[guided360] power: {reason}"))
        except Exception:
            decky.logger.exception("[guided360] power_action failed")
            return False

    async def log_home_error(self, entry: str) -> None:
        try:
            append_log(decky.DECKY_PLUGIN_LOG_DIR, f"v{decky.DECKY_PLUGIN_VERSION} {entry}"[:8000])
        except Exception:
            decky.logger.exception("[guided360] log_home_error failed")

    async def _main(self):
        decky.logger.info("[guided360] backend started")
        try:
            now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            path = os.path.join(decky.DECKY_PLUGIN_LOG_DIR, FILE_NAME)
            append_log(decky.DECKY_PLUGIN_LOG_DIR, start_entry(decky.DECKY_PLUGIN_VERSION, now, path))
        except Exception:
            decky.logger.exception("[guided360] start-up log entry failed")

    async def _unload(self):
        if getattr(self, "_frost", None):
            await self._frost.close()
        decky.logger.info("[guided360] backend stopped")
