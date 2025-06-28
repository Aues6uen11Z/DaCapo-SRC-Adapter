import json
from pathlib import Path

src_path = Path(__file__).parent / "StarRailCopilot"
menu_path = src_path / "module/config/argument/menu.json"
args_path = src_path / "module/config/argument/args.json"
i18n_dir = src_path / "module/config/i18n"
template_path = Path(__file__).parent / "template/template.json"
trans_dir = Path(__file__).parent / "template/i18n"


def gen_template():
    menu = json.loads(menu_path.read_text(encoding="utf-8"))
    args = json.load(args_path.open(encoding="utf-8"))

    # 通用设置
    template = {
        "Project": {
            "General": {
                "_Base": {
                    "language": {
                        "value": "zh-CN",
                    },
                    "work_dir": {
                        "value": "./repos/DaCapo-SRC-Adapter",
                        "disabled": True,
                    },
                    "background": {
                        "value": True,
                        "disabled": True,
                    },
                    "config_path": {
                        "value": "./repos/DaCapo-SRC-Adapter/src.json",
                    },
                    "log_path": {
                        "value": "./repos/DaCapo-SRC-Adapter/StarRailCopilot/log",
                        "disabled": True,
                    },
                }
            },
            "Update": {
                "_Base": {
                    "env_name": {
                        "value": "src",
                    },
                    "python_version": {
                        "value": "3.10",
                    },
                }
            },
        }
    }
    for group_name, group_content in args["Alas"].items():
        template["Project"]["General"][group_name] = {}
        for item_name, item_content in group_content.items():
            if "display" in item_content.keys() and item_content["display"] == "hide":
                continue

            item_config = {
                "type": item_content["type"],
                "value": item_content["value"],
                "option": item_content.get("option", []),
            }
            template["Project"]["General"][group_name][item_name] = item_config

    # 任务设置
    for menu_name, menu_content in menu.items():
        if menu_name == "Alas":
            continue

        template[menu_name] = {}
        for task_name in menu_content["tasks"]:
            template[menu_name][task_name] = {
                "_Base": {
                    "active": {
                        "value": True if menu_name == "Daily" else False,
                    },
                    "priority": {
                        "value": 6,
                    },
                    "command": {
                        "value": f"py main.py src {task_name}",
                    },
                }
            }
            for group_name, group_content in args[task_name].items():
                if group_name == "Scheduler":
                    continue

                template[menu_name][task_name][group_name] = {}
                for item_name, item_content in group_content.items():
                    if (
                        "display" in item_content.keys()
                        and item_content["display"] == "hide"
                        or item_content["type"] == "planner"
                    ):
                        continue

                    item_config = {
                        "type": "checkbox"
                        if item_content["type"] == "state"
                        else item_content["type"],
                        "value": ""
                        if item_content["value"] == {}
                        else item_content["value"],
                        "option": item_content.get("option", []),
                        "disabled": True
                        if item_content["type"] in ["stored", "state"]
                        else False,
                    }
                    template[menu_name][task_name][group_name][item_name] = item_config

    # 手动加一个结束任务
    template["Daily"]["Done"] = {
        "_Base": {
            "active": {
                "value": True,
            },
            "priority": {
                "value": 0,
            },
            "command": {
                "value": "py main.py src Done",
            },
        }
    }

    template_path.write_text(
        json.dumps(template, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def gen_i18n():
    for i18n_path in i18n_dir.glob("*.json"):
        trans_path = trans_dir / i18n_path.name
        orig_trans = json.loads(i18n_path.read_text(encoding="utf-8"))

        new_trans = {"Project": {"tasks": {"General": {"groups": {}}}}}
        template = json.loads(template_path.read_text(encoding="utf-8"))

        for menu_name, menu_config in template.items():
            if menu_name == "Project":
                if "General" in menu_config.keys():
                    group_trans = new_trans["Project"]["tasks"]["General"]["groups"]
                    for group_name, group_config in menu_config["General"].items():
                        if group_name == "_Base":
                            continue
                        group_trans[group_name] = {
                            "name": orig_trans[group_name]["_info"]["name"],
                            "help": orig_trans[group_name]["_info"]["help"],
                            "items": {},
                        }

                        item_trans = group_trans[group_name]["items"]
                        for item_name, item_config in group_config.items():
                            if item_name == "_help":
                                continue
                            item_trans[item_name] = {
                                "name": orig_trans[group_name][item_name]["name"],
                                "help": orig_trans[group_name][item_name]["help"],
                            }
                            for option_name in item_config.get("option", []):
                                item_trans[item_name].setdefault("options", {})[
                                    option_name
                                ] = orig_trans[group_name][item_name][option_name]
            else:
                new_trans[menu_name] = {
                    "name": orig_trans["Menu"][menu_name]["name"],
                    "tasks": {},
                }

                task_trans = new_trans[menu_name]["tasks"]
                for task_name, task_config in menu_config.items():
                    if task_name == "Done":
                        task_trans["Done"] = {
                            "name": "结束任务" if i18n_path.name == "zh-CN.json" else "Done",
                            "groups": {},
                        }
                        continue
                    
                    task_trans[task_name] = {
                        "name": orig_trans["Task"][task_name]["name"],
                        "groups": {},
                    }

                    group_trans = task_trans[task_name]["groups"]
                    for group_name, group_config in task_config.items():
                        if group_name == "_Base":
                            continue
                        group_trans[group_name] = {
                            "name": orig_trans[group_name]["_info"]["name"],
                            "help": orig_trans[group_name]["_info"]["help"],
                            "items": {},
                        }

                        item_trans = group_trans[group_name]["items"]
                        for item_name, item_config in group_config.items():
                            if item_name == "_help":
                                continue
                            item_trans[item_name] = {
                                "name": orig_trans[group_name][item_name]["name"],
                                "help": orig_trans[group_name][item_name]["help"],
                            }
                            for option_name in item_config.get("option", []):
                                item_trans[item_name].setdefault("options", {})[
                                    option_name
                                ] = orig_trans[group_name][item_name][str(option_name)]

        trans_path.write_text(
            json.dumps(new_trans, indent=2, ensure_ascii=False), encoding="utf-8"
        )


if __name__ == "__main__":
    gen_template()
    gen_i18n()
