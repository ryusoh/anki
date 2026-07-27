from __future__ import annotations

import json

import pytest

from auto_itaigi.utils import parse_itaigi_json

_FIXTURE = json.dumps(
    {
        "列表": [
            {
                "外語項目編號": "75162",
                "外語資料": "蕃薯",
                "新詞文本": [
                    {
                        "新詞文本項目編號": "75163",
                        "文本資料": "蕃薯",
                        "音標資料": "han-tsî/han-tsû",
                        "貢獻者": "台文華文線頂辭典",
                        "按呢講好": 34,
                        "按呢無好": 20,
                        "按呢講的外語列表": [
                            {"外語項目編號": 75162, "外語資料": "蕃薯"},
                            {"外語項目編號": 75159, "外語資料": "甘薯"},
                            {"外語項目編號": 9448, "外語資料": "地瓜"},
                        ],
                    },
                    {
                        "新詞文本項目編號": "96764",
                        "文本資料": "金薯",
                        "音標資料": "kim-tsî/kim-tsû",
                        "按呢講的外語列表": [
                            {"外語項目編號": 75162, "外語資料": "蕃薯"}
                        ],
                    },
                ],
            }
        ],
        "其他建議": [
            {"文本資料": "炕窯", "音標資料": "khòng-iô"},
            {"文本資料": "炰蕃薯", "音標資料": "pû-han-tsî/pû-huan-tsû"},
        ],
    },
    ensure_ascii=False,
)


def test_parse_fixture_highest_votes_when_no_exact_match():
    assert parse_itaigi_json(_FIXTURE, "番薯") == (
        "han-tsî/han-tsû",
        ["蕃薯", "甘薯", "地瓜"],
    )


def test_parse_prefers_exact_match_over_higher_votes():
    body = json.dumps(
        {
            "列表": [
                {
                    "新詞文本": [
                        {
                            "文本資料": "番薯",
                            "音標資料": "han-tsî/han-tsû",
                            "按呢講好": 1,
                            "按呢講的外語列表": [{"外語資料": "exact"}],
                        },
                        {
                            "文本資料": "蕃薯",
                            "音標資料": "other",
                            "按呢講好": 99,
                            "按呢講的外語列表": [{"外語資料": "other"}],
                        },
                    ]
                }
            ]
        },
        ensure_ascii=False,
    )
    assert parse_itaigi_json(body, "番薯") == ("han-tsî/han-tsû", ["exact"])


def test_parse_removes_duplicate_mandarin_words():
    body = json.dumps(
        {
            "列表": [
                {
                    "新詞文本": [
                        {
                            "文本資料": "蕃薯",
                            "音標資料": "han-tsî",
                            "按呢講好": 1,
                            "按呢講的外語列表": [
                                {"外語資料": "地瓜"},
                                {"外語資料": "蕃薯"},
                                {"外語資料": "地瓜"},
                                {"外語資料": "甘薯"},
                            ],
                        }
                    ]
                }
            ]
        },
        ensure_ascii=False,
    )
    assert parse_itaigi_json(body, "蕃薯") == (
        "han-tsî",
        ["地瓜", "蕃薯", "甘薯"],
    )


def test_parse_missing_mandarin_list():
    body = json.dumps(
        {
            "列表": [
                {
                    "新詞文本": [
                        {"文本資料": "蕃薯", "音標資料": "han-tsî", "按呢講好": 1}
                    ]
                }
            ]
        },
        ensure_ascii=False,
    )
    assert parse_itaigi_json(body, "蕃薯") == ("han-tsî", [])


def test_parse_empty_tailo():
    body = json.dumps(
        {
            "列表": [
                {
                    "新詞文本": [
                        {
                            "文本資料": "蕃薯",
                            "音標資料": "",
                            "按呢講好": 1,
                            "按呢講的外語列表": [{"外語資料": "地瓜"}],
                        }
                    ]
                }
            ]
        },
        ensure_ascii=False,
    )
    assert parse_itaigi_json(body, "蕃薯") == ("", ["地瓜"])


@pytest.mark.parametrize(
    "body",
    [
        json.dumps({"列表": [], "其他建議": []}),
        json.dumps({"列表": [{"新詞文本": []}]}),
        "not json",
    ],
)
def test_parse_not_found_returns_none(body):
    assert parse_itaigi_json(body, "whatever") is None
