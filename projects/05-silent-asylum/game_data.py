"""
��死寂疗养院》游戏数据模块
从 game_data.json 加载所有场景、事件、选项、信息碎片、结局数据
"""
import json
import os

_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'game_data.json')

with open(_json_path, 'r', encoding='utf-8') as f:
    _data = json.load(f)

FRAGMENTS = {int(k): v for k, v in _data["fragments"].items()}
EROSION_STATES = _data["erosion_states"]
ENDINGS = _data["endings"]
BAD_ENDINGS = _data["bad_endings"]
SCENES = _data["scenes"]


def get_erosion_state(erosion_value):
    """根据侵蚀度值返回对应的状态信息"""
    for state in EROSION_STATES:
        low, high = state["range"]
        if low <= erosion_value <= high:
            return state
    return EROSION_STATES[-1]


def get_scene(scene_id):
    """根据场景ID获取场景数据"""
    for scene in SCENES:
        if scene["id"] == scene_id:
            return scene
    return None


def get_fragment(fragment_id):
    """根据碎片ID获取碎片数据"""
    return FRAGMENTS.get(int(fragment_id))


def get_ending(ending_id):
    """根据结局ID获取结局数据"""
    return ENDINGS.get(ending_id)


def get_bad_ending(be_name):
    """根据BE名称获取即死结局数据"""
    return BAD_ENDINGS.get(be_name)


def determine_ending(erosion, fragment_count):
    """根据精神侵蚀度和碎片收集数量判定结局"""
    if erosion >= 100:
        return "assimilation"
    elif fragment_count == 18 and erosion < 50:
        return "perfect"
    else:
        return "normal"
