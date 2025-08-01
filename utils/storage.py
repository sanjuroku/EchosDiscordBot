import os
import json
import logging

class StorageManager:
    def __init__(self, filename):
        self.filename = filename
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"⚠️ 加载 {self.filename} 失败：{e}")
        return self.default_data()

    def save(self):
        directory = os.path.dirname(self.filename)
        if directory:
            os.makedirs(directory, exist_ok=True)

        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def default_data(self):
        raise NotImplementedError("请使用子类，如 DictStorageManager 或 ListStorageManager")


class DictStorageManager(StorageManager):
    def default_data(self):
        return {}

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def delete(self, key):
        if key in self.data:
            del self.data[key]
            self.save()


class ListStorageManager(StorageManager):
    def default_data(self):
        return []

    def append(self, value):
        if value not in self.data:
            self.data.append(value)
            self.save()

    def remove(self, value):
        if value in self.data:
            self.data.remove(value)
            self.save()

    def clear(self):
        self.data.clear()
        self.save()

# ============================== #
# 全局变量与常量定义
# ============================== #
CONFIG_DIR = "config"
SAVEDATA_DIR = "savedata"

# 使用StorageManager封装
history_storage = DictStorageManager(os.path.join(SAVEDATA_DIR, "histories.json"))
summary_storage = DictStorageManager(os.path.join(SAVEDATA_DIR, "summaries.json"))
role_storage = DictStorageManager(os.path.join(CONFIG_DIR, "roles.json"))
trigger_storage = ListStorageManager(os.path.join(CONFIG_DIR, "disabled_triggers.json"))
guild_list_storage = DictStorageManager(os.path.join(CONFIG_DIR, "guilds.json"))
status_storage = DictStorageManager(os.path.join(CONFIG_DIR, "status_config.json"))
reddit_cache_storage = DictStorageManager(os.path.join(SAVEDATA_DIR, "reddit_cache.json"))
reddit_sent_cache_storage = DictStorageManager(os.path.join(SAVEDATA_DIR, "reddit_sent_cache.json"))

user_histories = history_storage.data  # 存储用户对话历史
user_summaries = summary_storage.data  # 存储用户对话摘要
user_roles = role_storage.data  # 存储用户角色设定