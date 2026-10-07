"""首次默认玉色科技；已有皮肤、玩家自定义均可通过网页读取。"""
import shutil

import skins


def test_the_shipped_skins_default_first_and_your_own_shows_up(tmp_path, monkeypatch):
    names = [k["name"] for k in skins.listing()]
    assert names[0] == "玉色科技"
    assert {"黑白极简", "暖色纸质", "精密深色", "玉色科技"}.issubset(names)
    jade = next(k for k in skins.listing() if k['name'] == '玉色科技')
    assert jade['builtin'] and jade['default'] and all(jade['swatch'])
    first = skins.listing()[0]
    assert first["default"] and first["builtin"] and first["one_line"] and all(first["swatch"])
    d = tmp_path / "外观"
    shutil.copytree(skins.DIR, d)
    monkeypatch.setattr(skins, "DIR", d)
    (d / "我的蓝.css").write_text((d / "黑白极简.css").read_text(encoding="utf-8")
                                .replace("自带：是", "").replace("--accent:#171717", "--accent:#1f5fbf"), encoding="utf-8")
    mine = skins.listing()[-1]
    assert mine["name"] == "我的蓝" and not mine["builtin"] and mine["swatch"][3] == "#1f5fbf"   # 复制一份改个名，多一项
    assert skins.css_file("我的蓝") == d / "我的蓝.css"
    assert skins.css_file("../main") is None and skins.css_file("说明") is None                  # 外观/ 外面的、不是 .css 的都不给


def test_the_page_gets_the_list_and_the_css(proj):
    from fastapi.testclient import TestClient
    from main import create_app
    with TestClient(create_app(proj)) as client:
        d = client.get("/api/skins").json()
        assert d["default"] == "玉色科技" and d['skins'][0]['name'] == '玉色科技'
        assert {"黑白极简", "暖色纸质", "精密深色", "玉色科技"}.issubset({k['name'] for k in d['skins']})
        r = client.get("/skin/精密深色.css")
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/css") and "--accent" in r.text
        jade = client.get('/skin/玉色科技.css')
        assert jade.status_code == 200 and jade.headers['content-type'].startswith('text/css')
        assert '--onaccent' in jade.text and 'dark' in jade.text
        assert client.get("/skin/没有这套.css").status_code == 404
        page = client.get("/").text
        assert "tpl_skin" in page and "var(--onaccent)" in page and "--accent:#171717" in page   # 经典黑白仍可切回，主按钮文字跟着皮肤变
