import os
from typing import List
import math
import datetime
import requests
from github import Github, InputFileContent

MENU_PAGE_BLOCK_ID = "b261c537-bf9a-4fa7-9a94-c3b8a79fa573"
HOST_URL = "https://beforeitmelts.notion.site"
BLOCKS = dict()
GITHUB_TOKEN = os.environ.get("GH_TOKEN")
GIST_ID = os.environ.get("GIST_ID")


def gist_rest_day_formatter(contents: List[str]) -> str:
    return "\n".join(contents)


def gist_formatter(contents: List[str]) -> str:
    footer = f"💡 [ {contents[3]} ]"
    menu_list = contents[4:-2]
    size = math.ceil(len(menu_list) / 4)

    formatted_result = []

    while menu_list:
        formatted_result.append(" | ".join(menu_list[:size]))
        menu_list = menu_list[size:]

    formatted_result.append(footer)

    return "\n".join(formatted_result)


def update_gist(github_token: str, gist_id: str, content: str):
    github_client = Github(github_token)
    gist = github_client.get_gist(gist_id)
    gist.edit(
        "『녹기 전에』 오늘의 메뉴 😀",
        files={
            "before-it-melts": InputFileContent(content)
        }
    )


def get_page():
    url = f"{HOST_URL}/api/v3/syncRecordValues"

    payload = {
        "requests": [{"pointer": {"table": "block", "id": "b261c537-bf9a-4fa7-9a94-c3b8a79fa573"}, "version": -1}]}
    headers = {
        "cookie": "notion_browser_id=186eb47e-b3c7-4b78-b229-ae415df2ae75",
        "Content-Type": "application/json"
    }

    response = requests.request("POST", url, json=payload, headers=headers)

    return response.json()["recordMap"]["block"][MENU_PAGE_BLOCK_ID]


def get_cached_blocks():
    url = f"{HOST_URL}/api/v3/loadCachedPageChunk"
    payload = {
        "page": {"id": MENU_PAGE_BLOCK_ID},
        "limit": 100,
        "cursor": {"stack": []},
        "chunkNumber": 0,
        "verticalColumns": False
    }

    headers = {
        "cookie": "notion_browser_id=fd74425f-1482-4bd8-a4c1-71ee082148e8",
        "Content-Type": "application/json"
    }

    response = requests.request("POST", url, json=payload, headers=headers)

    block = response.json()["recordMap"]["block"]
    BLOCKS.update(block)


class TextStyleHelper:
    def __init__(self, _list):
        self._list = _list

    @property
    def is_bold_style(self):
        return self._list == ['b']

    @property
    def is_italic_style(self):
        return self._list == ['i']

    @property
    def is_highlight_style(self):
        return len(self._list) == 2 and self._list[0] == "h"

    @property
    def is_a_tag_style(self):
        return len(self._list) == 2 and self._list[0] == "a"

    @property
    def is_under_style(self):
        return self._list == ["_"]

    @property
    def is_date_format(self):
        return len(self._list) == 2 and self._list[0] == "d" and self._list[1]["type"] == "date"

    def parse_date(self):
        date_format = self._list[1]["date_format"]
        date_format = date_format.replace("YYYY", "%Y").replace("YY", "%y").replace("MM", "%m").replace("DD", "%d")
        date_object = datetime.datetime.strptime(self._list[1]["start_date"], "%Y-%m-%d")
        return date_object.strftime(date_format)


def get_text_from_block(block):
    text_list = []

    def __get_title(_list):
        text_style_helper = TextStyleHelper(_list)
        if text_style_helper.is_bold_style:
            return
        elif text_style_helper.is_highlight_style:
            return
        elif text_style_helper.is_italic_style:
            return
        elif text_style_helper.is_under_style:
            return
        elif text_style_helper.is_a_tag_style:
            return
        elif text_style_helper.is_date_format:
            text_list.append(text_style_helper.parse_date())
            return

        if isinstance(_list, list):
            for __list in _list:
                __get_title(__list)
        elif isinstance(_list, (str, bytes)):
            _title = _list.strip()
            text_list.append(_title)
        else:
            pass

    try:
        __get_title(block["value"]["properties"]["title"])
        return " ".join(text_list)
    except KeyError:
        return ""


def get_block_color_from_block(block):
    try:
        return block["value"]["format"]["block_color"]
    except KeyError:
        return ""


def get_ice_cream_type_from_color(block_color):
    #  🟦: Milk  🟥: No Milk  ⑲ : Alcohol
    if not block_color:
        return ""
    ice_cream_type = ""
    if block_color == "blue_background":
        ice_cream_type = u"🟦 "
    elif block_color == "red_background":
        ice_cream_type = u"🟥 "
    elif block_color == "brown_background":
        ice_cream_type = u"🟫"
    elif block_color == "yellow_background":
        ice_cream_type = ""
    elif block_color == "orange_background":
        ice_cream_type = u"🟧"
    elif block_color == "gray_background":
        ice_cream_type = ""
    return ice_cream_type


def get_menu_list():
    content_list = []

    now = datetime.datetime.now()
    if now.weekday() == 1:
        content_list.append("오늘은 쉬는날! \n아이스크림 얼리는 중... 🥶🥶🥶")
        return content_list, True

    get_cached_blocks()
    page = get_page()
    title = get_text_from_block(page)
    emoji = page["value"]["format"]["page_icon"]
    cover = page["value"]["format"]["page_cover"]
    contents = page["value"]["content"]

    header_content = f"{title} {emoji}"

    content_list.append(header_content)

    for block_id in contents:
        if block_id == "020728e2-407c-4602-aa71-ea145219ad69":
            break

        block = BLOCKS.get(block_id)

        title = get_text_from_block(block)
        block_color = get_block_color_from_block(block)
        ice_cream_type_icon = get_ice_cream_type_from_color(block_color)
        content = f"{ice_cream_type_icon}{title}"

        content_list.append(content)

    return content_list, False


def main():
    content_list, is_rest = get_menu_list()
    for content in content_list:
        print(content)

    if GITHUB_TOKEN and GIST_ID:
        if is_rest:
            gist_content = gist_rest_day_formatter(content_list)
        else:
            gist_content = gist_formatter(content_list)
        update_gist(GITHUB_TOKEN, GIST_ID, gist_content)


if __name__ == "__main__":
    main()
