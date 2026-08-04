import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from fix_jp_pinyin_front import plan_updates, run, transform

REAL_FRONT = (
    "<div><div><div>您的 通訊 地址 是 ？</div>"
    "<div>現住所 は どこ です か？</div>"
    '<div><div><span style="font-weight: 700;">拼音練習</span><i></i>'
    "&nbsp;:&nbsp;genjuusho wa doko desu ka?<br>(genzyuusyo ha doko desu ka?)</div>"
    '<div><span style="font-weight: 700;">發音</span><i></i>'
    "&nbsp;:&nbsp;genjūsho wa doko des[u] ka?</div>"
    '<div><span style="font-weight: 700;">音標</span><i></i>'
    "&nbsp;:&nbsp;ɡe̞nʥūɕo̞ ɰɑ do̞ko̞ de̞s[ɯ] kɑ?</div></div>"
    "<div><i></i><div></div></div></div><div><div><div><br></div></div></div></div>"
)
REAL_BACK = "[sound:4922.mp3]"


def _note(note_id, front, back):
    return {
        "noteId": note_id,
        "fields": {
            "Front": {"value": front, "order": 0},
            "Back": {"value": back, "order": 1},
            "ID": {"value": "", "order": 2},
        },
    }


def test_transform_real_card_moves_japanese_line_to_front():
    new_front, new_back = transform(REAL_FRONT, REAL_BACK)
    assert new_front == "現住所はどこですか？"
    # The rest of the old front lands above the sound line.
    assert new_back.endswith(REAL_BACK)
    rest = new_back[: -len(REAL_BACK)]
    assert "您的 通訊 地址 是 ？" in rest
    assert "拼音練習" in rest
    assert "現住所 は どこ です か？" not in rest


def test_transform_strips_only_spacing_from_japanese_line():
    front = "<div>中文 行 。</div><div>a b&nbsp;c&nbsp;&nbsp;d</div><div>拼音練習 : x</div>"
    new_front, _ = transform(front, "")
    assert new_front == "abcd"


CANTONESE_FRONT = (
    "<div><div><div>我們 該 走 了 。</div>"
    "<div>我哋 要 走 喇 。</div>"
    '<div><div><span style="font-weight: 700;">拼音練習</span><i></i>'
    "&nbsp;:&nbsp;Typing: ngo5 dei6 jiu3 zau2 laa3.<br>"
    "To view more transcriptions for speaking, turn on recording or switch "
    "to listening mode.</div>"
    '<div><span style="font-weight: 700;">發音</span><i></i>'
    "&nbsp;:&nbsp;ngo5 dei6 jiu3 zau2 laa3.</div>"
    '<div><span style="font-weight: 700;">音標</span><i></i>'
    "&nbsp;:&nbsp;ŋɔ̗ːt˭e̱ʲ ji̟ːʷ ʦ˭ɐ́ʷ la̟ː</div></div></div>"
    "<div><i></i><div></div></div></div><div><div><div><br></div></div></div></div>"
)


def test_transform_cantonese_card_keeps_typing_block_in_back():
    back = "[sound:1732-b500cd9641324e6068ea31a09edb15cd36a85f66.mp3]"
    new_front, new_back = transform(CANTONESE_FRONT, back)
    assert new_front == "我哋要走喇。"
    assert new_back.endswith(back)
    rest = new_back[: -len(back)]
    assert "我們 該 走 了 。" in rest
    assert "Typing: ngo5 dei6 jiu3 zau2 laa3." in rest
    assert "我哋 要 走 喇 。" not in rest


def test_transform_leaves_back_alone_when_it_already_has_the_practice_block():
    back = '<div><div><div>她的 小孩 在 學校 。</div><div>拼音練習 : Typing: keoi5...</div></div></div><div>[sound:8.mp3]</div>'
    new_front, new_back = transform(CANTONESE_FRONT, back)
    assert new_front == "我哋要走喇。"
    assert new_back == back


def test_transform_handles_br_separated_front():
    front = (
        "抱歉 我 遲到 了 。<br>"
        "對唔住 我 遲到 。<br>"
        "拼音練習 : Typing: deoi3 m4 zyu6 ngo5 ci4 dou3.<br>"
        "To view more transcriptions for speaking, turn on recording or switch "
        "to listening mode.<br>"
        "發音 : deoi3 m4 zyu6 ngo5 ci4 dou3.<br>"
        "音標 : t˭ø̟ᶣm̖ʦ˭y̱ː ŋɔ̗ː ʦʰi̖ːt˭o̟ʷ"
    )
    new_front, new_back = transform(front, "[sound:x.mp3]")
    assert new_front == "對唔住我遲到。"
    rest = new_back[: -len("[sound:x.mp3]")]
    assert rest.startswith("抱歉 我 遲到 了 。<br>拼音練習 : Typing:")
    assert "對唔住 我 遲到 。" not in rest


def test_transform_drops_ruby_readings_from_japanese_line():
    front = (
        "<div>中文。</div>"
        "<div><ruby>空<rt>あ</rt></ruby>き <ruby>巣<rt>す</rt></ruby></div>"
        "<div>拼音練習 : suki akisu</div>"
    )
    new_front, _ = transform(front, "")
    assert new_front == "空き巣"


def test_transform_returns_none_without_marker():
    assert transform("<div>皮膚科に診て貰った方が好いね。</div>", REAL_BACK) is None


def test_transform_returns_none_when_japanese_line_missing():
    front = "<div>拼音練習 : li2 ho2 bo5?</div>"
    assert transform(front, "") is None


def test_transform_returns_none_for_blank_japanese_line():
    front = "<div>中文。</div><div>&nbsp;</div><div>拼音練習 : x</div>"
    assert transform(front, "") is None


def test_plan_updates_targets_front_and_back_fields():
    updates = plan_updates([_note(1, REAL_FRONT, REAL_BACK)])
    assert updates == [
        {
            "id": 1,
            "fields": {
                "Front": "現住所はどこですか？",
                "Back": updates[0]["fields"]["Back"],
            },
        }
    ]
    assert updates[0]["fields"]["Back"].endswith(REAL_BACK)


def test_plan_updates_skips_notes_without_marker_or_back():
    notes = [
        _note(1, "<div>already fixed</div>", REAL_BACK),
        {"noteId": 2, "fields": {"Front": {"value": "拼音練習", "order": 0}}},
    ]
    assert plan_updates(notes) == []


def test_run_dry_run_makes_no_writes(capsys):
    calls = []

    def invoke(action, params=None):
        calls.append(action)
        if action == "findNotes":
            return [1]
        if action == "notesInfo":
            return [_note(1, REAL_FRONT, REAL_BACK)]
        raise AssertionError(f"unexpected write action {action}")

    summary = run(invoke, "deck:x", apply=False)
    assert calls == ["findNotes", "notesInfo"]
    assert summary == {"matched": 1, "planned": 1, "written": 0}
    out = capsys.readouterr().out
    assert "現住所はどこですか？" in out


def test_run_apply_writes_each_planned_note():
    written = []

    def invoke(action, params=None):
        if action == "findNotes":
            return [1, 2]
        if action == "notesInfo":
            return [
                _note(1, REAL_FRONT, REAL_BACK),
                _note(2, "<div>already fixed</div>", "[sound:9.mp3]"),
            ]
        if action == "updateNoteFields":
            written.append(params["note"])
            return None
        raise AssertionError(action)

    summary = run(invoke, "deck:x", apply=True)
    assert summary == {"matched": 2, "planned": 1, "written": 1}
    assert written[0]["id"] == 1
    assert written[0]["fields"]["Front"] == "現住所はどこですか？"
