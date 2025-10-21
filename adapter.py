import json
from pathlib import Path
import sys
import time
import inflection


project_root = Path(__file__).parent / "StarRailCopilot"
sys.path.insert(0, str(project_root))

from StarRailCopilot.module.base.decorator import del_cached_property  # noqa: E402
from StarRailCopilot.module.config.deep import deep_get, deep_set  # noqa: E402
from StarRailCopilot.installer import run_install, run_set  # noqa: E402
from StarRailCopilot.module.notify import handle_notify  # noqa: E402
from StarRailCopilot.module.logger import logger  # noqa: E402
from StarRailCopilot.module.base.resource import release_resources  # noqa: E402
from StarRailCopilot.src import StarRailCopilot  # noqa: E402
from gen_template import gen_i18n, gen_template  # noqa: E402

logger.handlers = logger.handlers[:2]


class Adapter(StarRailCopilot):
    def check_update(self):
        record_file = Path(__file__).parent / "last_update.txt"
        if record_file.exists():
            last_update = record_file.read_text(encoding="utf-8").strip()
            if time.time() - float(last_update) < 1800:
                logger.info("No need to update, last update within 30 minutes.")
                return False

        python_exec = Path(sys.executable)
        if (
            python_exec.parent / "Lib/site-packages/adbutils/binaries/adb.exe"
        ).exists():
            adb_path = (
                python_exec.parent / "Lib/site-packages/adbutils/binaries/adb.exe"
            )
        elif (
            python_exec.parent.parent / "Lib/site-packages/adbutils/binaries/adb.exe"
        ).exists():
            adb_path = (
                python_exec.parent.parent
                / "Lib/site-packages/adbutils/binaries/adb.exe"
            )
        else:
            adb_path = None

        if adb_path:
            # 使用自定义adb
            run_set(
                [
                    "Repository=cn",
                    "PypiMirror=https://pypi.tuna.tsinghua.edu.cn/simple",
                    f"AdbExecutable={adb_path.as_posix()}",
                    "ReplaceAdb=true",
                    "AutoConnect=true",
                ]
            )
        else:
            # 使用模拟器自带adb，缺点是不能在模拟器未打开的状态下运行，且不同模拟器adb可能冲突
            run_set(
                [
                    "Repository=cn",
                    "PypiMirror=https://pypi.tuna.tsinghua.edu.cn/simple",
                    "ReplaceAdb=false",
                    "AutoConnect=false",
                ]
            )
        run_install()
        gen_template()
        gen_i18n()
        record_file.write_text(str(time.time()), encoding="utf-8")
        return True

    def backward_sync(self, src_ist, dacapo_ist, template):
        """将SRC中的stored/state类型数据同步回DaCapo"""
        for menu_name, menu_content in dacapo_ist.items():
            if menu_name == "Project":
                if "General" in menu_content:
                    # General任务对应SRC中的Alas
                    if "Alas" in src_ist:
                        self._sync_stored_group(
                            src_ist["Alas"],
                            dacapo_ist["Project"]["General"],
                            template["Project"]["General"],
                        )
                        # 处理特殊的auto配置项
                        self._sync_auto_configs(
                            src_ist["Alas"],
                            dacapo_ist["Project"]["General"],
                        )
            else:
                # 处理其他菜单的任务
                for task_name, _ in menu_content.items():
                    if task_name in src_ist:
                        self._sync_stored_group(
                            src_ist[task_name],
                            dacapo_ist[menu_name][task_name],
                            template[menu_name][task_name],
                        )

    def _sync_auto_configs(self, src_alas, dacapo_general):
        """同步auto配置项"""
        # 处理Emulator组的特殊配置项
        if "Emulator" in dacapo_general and "Emulator" in src_alas:
            emulator_auto_items = ["Serial", "PackageName", "GameLanguage"]
            for item in emulator_auto_items:
                if item in dacapo_general["Emulator"] and item in src_alas["Emulator"]:
                    # 如果DaCapo中是"auto"，从SRC同步真实值
                    if dacapo_general["Emulator"][item] == "auto":
                        dacapo_general["Emulator"][item] = src_alas["Emulator"][item]

        # 处理EmulatorInfo组
        if (
            "EmulatorInfo" in dacapo_general
            and "EmulatorInfo" in src_alas
            and "Emulator" in dacapo_general["EmulatorInfo"]
        ):
            # 如果DaCapo中Emulator为"auto"，同步整个EmulatorInfo组
            if dacapo_general["EmulatorInfo"]["Emulator"] == "auto":
                emulator_info_items = ["Emulator", "name", "path"]
                for item in emulator_info_items:
                    if (
                        item in dacapo_general["EmulatorInfo"]
                        and item in src_alas["EmulatorInfo"]
                    ):
                        dacapo_general["EmulatorInfo"][item] = src_alas["EmulatorInfo"][
                            item
                        ]

    def _sync_stored_group(self, src_task, dacapo_task, template_task):
        """同步单个任务组的stored数据"""
        for group_name, group_content in dacapo_task.items():
            if group_name in src_task and group_name in template_task:
                for item_name, _ in group_content.items():
                    if (
                        item_name in src_task[group_name]
                        and item_name in template_task[group_name]
                    ):
                        item_type = template_task[group_name][item_name].get("type")
                        if item_type in ["stored", "state"]:
                            src_value = src_task[group_name][item_name]

                            if isinstance(src_value, dict):
                                if "total" in src_value:
                                    dacapo_task[group_name][item_name] = (
                                        f"{src_value['value']}/{src_value['total']}"
                                    )
                                elif "value" in src_value:
                                    dacapo_task[group_name][item_name] = str(
                                        src_value["value"]
                                    )
                                else:
                                    dacapo_task[group_name][item_name] = (
                                        str(src_value) if src_value else ""
                                    )
                            else:
                                dacapo_task[group_name][item_name] = src_value

    def forward_sync(self, dacapo_ist, src_ist, template):
        """将DaCapo中的用户设置同步到SRC（跳过stored/state类型）"""
        for menu_name, menu_content in dacapo_ist.items():
            if menu_name == "Project":
                if "General" in menu_content and "Alas" in src_ist:
                    self._sync_user_group(
                        menu_content["General"],
                        src_ist["Alas"],
                        template["Project"]["General"],
                    )
            else:
                for task_name, task_content in menu_content.items():
                    if (
                        task_name in src_ist
                        and menu_name in template
                        and task_name in template[menu_name]
                    ):
                        self._sync_user_group(
                            task_content,
                            src_ist[task_name],
                            template[menu_name][task_name],
                        )

    def _sync_user_group(self, dacapo_task, src_task, template_task):
        """同步单个任务组的用户设置"""
        for group_name, group_content in dacapo_task.items():
            if group_name == "Scheduler" or group_name not in src_task:
                continue

            if group_name in template_task:
                for item_name, item_value in group_content.items():
                    if (
                        item_name in src_task[group_name]
                        and item_name in template_task[group_name]
                    ):
                        item_type = template_task[group_name][item_name].get("type")
                        if item_type not in ["stored", "state"]:
                            if not isinstance(src_task[group_name][item_name], dict):
                                src_task[group_name][item_name] = item_value

    def sync_config(self):
        src_ist_path = project_root / f"config/{self.config_name}.json"
        if not src_ist_path.exists():
            src_template_path = src_ist_path.with_stem("template")
            src_ist_path.write_text(
                src_template_path.read_text(encoding="utf-8"), encoding="utf-8"
            )
        dacapo_ist_path = Path(__file__).parent / f"{self.config_name}.json"
        template_path = Path(__file__).parent / "template/template.json"

        dacapo_ist = json.loads(dacapo_ist_path.read_text(encoding="utf-8"))
        src_ist = json.loads(src_ist_path.read_text(encoding="utf-8"))
        template = json.loads(template_path.read_text(encoding="utf-8"))

        # 1. 将SRC中的"stored", "state"类型只读数据同步回DaCapo
        self.backward_sync(src_ist, dacapo_ist, template)

        # 2. 将DaCapo中的其他类型设置项同步到SRC
        self.forward_sync(dacapo_ist, src_ist, template)

        dacapo_ist_path.write_text(
            json.dumps(dacapo_ist, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        src_ist_path.write_text(
            json.dumps(src_ist, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def done(self):
        method = self.config.Optimization_WhenTaskQueueEmpty
        if method == 'close_game':
            logger.info('Close game during wait')
            self.run('stop')
            release_resources()
            self.device.release_during_wait()
        elif method == 'goto_main':
            logger.info('Goto main page during wait')
            self.run('goto_main')
            release_resources()
            self.device.release_during_wait()
        elif method == 'stay_there':
            logger.info('Stay there during wait')
            release_resources()
            self.device.release_during_wait()
        elif method == 'close_emulator':
            logger.info('Close emulator during wait')
            self.run('close_emulator')
            release_resources()
            self.device.release_during_wait()
        else:
            logger.warning(f'Invalid Optimization_WhenTaskQueueEmpty: {method}, fallback to stay_there')
            release_resources()
            self.device.release_during_wait()

    def dacapo_task(self, task_name):
        logger.set_file_logger(self.config_name)
        self.sync_config()
        self.check_update()
        task = task_name

        while True:
            # Init device and change server
            _ = self.device
            self.device.config = self.config

            # Run
            logger.info(f"Scheduler: Start task `{task}`")
            self.device.stuck_record_clear()
            self.device.click_record_clear()
            logger.hr(task, level=0)
            self.config.bind(task)
            success = self.run(inflection.underscore(task))
            logger.info(f"Scheduler: End task `{task}`")

            # Check failures
            failed = deep_get(self.failure_record, keys=task, default=0)
            failed = 0 if success else failed + 1
            deep_set(self.failure_record, keys=task, value=failed)
            if failed >= 3:
                logger.critical(f"Task `{task}` failed 3 or more times.")
                logger.critical(
                    "Possible reason #1: You haven't used it correctly. "
                    "Please read the help text of the options."
                )
                logger.critical(
                    "Possible reason #2: There is a problem with this task. "
                    "Please contact developers or try to fix it yourself."
                )
                logger.critical("Request human takeover")
                handle_notify(
                    self.config.Error_OnePushConfig,
                    title=f"Src <{self.config_name}> crashed",
                    content=f"<{self.config_name}> RequestHumanTakeover\nTask `{task}` failed 3 or more times.",
                )
                exit(1)

            if success:
                del_cached_property(self, "config")
                if task == "Restart":
                    task = task_name
                    continue
                else:
                    break
            else:
                del_cached_property(self, "config")
                self.checker.check_now()
                if task == task_name:
                    task = "Restart"
                continue
