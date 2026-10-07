"""普通内置工具指南：网页与 MCP 同读；清单不执行命令、不推断安装状态。"""
from __future__ import annotations

import hashlib
import json
import posixpath
import re
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

import builtin

CATALOG = "工具库/安装指南/catalog.json"              # 10-07 统一内置：各处的 内置/ 去掉了这一层
ROOTS = ("工具库/安装指南/", "品牌/", "插件/网页终端/安装指南.md",
         "插件/PPT预览/安装指南.md", "插件/剪辑/安装指南.md")
IMAGES = {".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico"}
MAX_TEXT = 512 * 1024
FIELDS = ("id", "name", "name_en", "group", "group_en", "summary", "summary_en",
          "guide", "icon", "logo", "logo_source", "section", "image", "image_kind", "image_source", "official", "download", "notice", "notice_en", "verified")


class Invalid(ValueError):
    pass


def _path(root: Path, value: str, suffixes: set[str]) -> Path:
    if not isinstance(value, str) or not any(value.startswith(prefix) for prefix in ROOTS):
        raise Invalid("只读取已批准的指南目录里的指南或图片")
    try:
        path = builtin.path(root, value)
    except builtin.Invalid as err:
        raise Invalid(str(err)) from err
    if not path.is_file() or path.suffix.lower() not in suffixes:
        raise Invalid("引用必须是指南目录里的 Markdown 指南或支持的图片")
    return path


def _read(root: Path, value: str, suffixes: set[str]) -> bytes:
    path = _path(root, value, suffixes)
    if path.stat().st_size > MAX_TEXT:
        raise Invalid("指南文件超过 512 KB")
    return path.read_bytes()


def _https(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:
        return False


def listing(root: Path) -> dict:
    """缺文件仍显示明确错误；没有清单的旧项目返回空列表。"""
    result = {"version": 1, "items": [], "errors": []}
    # 先做路径检查，不能通过一个不存在的链接伪装成旧空项目。
    try:
        candidate = builtin.path(root, CATALOG, exists=False)
        if not candidate.exists():
            return result
        data = json.loads(_read(root, CATALOG, {".json"}).decode("utf-8-sig"))
        if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("items"), list):
            raise Invalid("工具指南清单应为 version=1，items 列表")
    except (ValueError, OSError, UnicodeError) as err:
        result["errors"].append({"path": CATALOG, "message": str(err)})
        return result
    counts = Counter(x.get("id") for x in data["items"] if isinstance(x, dict) and isinstance(x.get("id"), str))
    for index, raw in enumerate(data["items"]):
        key = raw.get("id", "") if isinstance(raw, dict) else ""
        try:
            if not isinstance(raw, dict) or not isinstance(key, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", key):
                raise Invalid("应用 id 必须是小写字母、数字及连字符")
            if counts[key] != 1:
                raise Invalid("应用 id 重复，保留原清单待修正，不选择其中一份")
            for field in ("name", "group", "summary", "guide"):
                if not isinstance(raw.get(field), str) or not raw[field].strip():
                    raise Invalid("缺少应用字段：" + field)
            item = {k: raw[k] for k in FIELDS if isinstance(raw.get(k), str)}
            for field in ("official", "download", "image_source", "logo_source"):
                if raw.get(field) and (not isinstance(raw[field], str) or not _https(raw[field])):
                    raise Invalid("官方入口和下载地址只接受无账号的 HTTPS 网址")
            if raw.get("image"):
                try:
                    _path(root, raw["image"], IMAGES)
                    if raw.get("image_kind", "icon") not in ("icon", "screenshot", "illustration"):
                        raise Invalid("image_kind 只能是 icon、screenshot 或 illustration")
                except (ValueError, OSError) as err:
                    item.pop("image", None)
                    result["errors"].append({"id": key, "path": raw.get("image"), "message": str(err)})
            if raw.get("logo"):
                try:
                    _path(root, raw["logo"], IMAGES)
                except (ValueError, OSError) as err:
                    item.pop("logo", None)
                    result["errors"].append({"id": key, "path": raw.get("logo"), "message": str(err)})
            if raw.get("section") and raw["section"] not in ("s:oss", "s:links"):
                raise Invalid("资源入口只能明确关联 s:oss 或 s:links")
            targets = raw.get("targets", [])
            if not isinstance(targets, list) or any(not isinstance(x, str) or not re.fullmatch(r"(?:tool|agent|plugin):[^\r\n:]+", x) for x in targets):
                raise Invalid("targets 必须是明确 tool:/agent:/plugin: 关联列表")
            item["targets"] = list(dict.fromkeys(targets))
            if item.get("section") and item["targets"]:
                raise Invalid("资源入口不是安装能力，不能关联安装检查")
            if "routes" in raw:
                routes = raw["routes"]
                if not isinstance(routes, list):
                    raise Invalid("方案应为 routes 列表")
                route_counts = Counter(x.get("id") for x in routes if isinstance(x, dict) and isinstance(x.get("id"), str))
                item["routes"] = []
                for route in routes:
                    route_id = route.get("id", "") if isinstance(route, dict) else ""
                    try:
                        if not isinstance(route_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", route_id):
                            raise Invalid("方案 id 应为小写字母、数字及连字符")
                        if route_counts[route_id] != 1:
                            raise Invalid("方案 id 重复，不选择其中一份")
                        for field in ("label", "guide"):
                            if not isinstance(route.get(field), str) or not route[field].strip():
                                raise Invalid("缺少方案字段：" + field)
                        for field in ("official", "download"):
                            if route.get(field) and (not isinstance(route[field], str) or not _https(route[field])):
                                raise Invalid("方案入口只接受无账号的 HTTPS 网址")
                        entry = {k: route[k] for k in ("id", "label", "label_en", "guide", "official", "download", "notice", "notice_en") if isinstance(route.get(k), str)}
                        try:
                            body = _read(root, entry["guide"], {".md"})
                            body.decode("utf-8-sig")
                            entry["revision"] = hashlib.sha256(body).hexdigest()
                        except (ValueError, OSError, UnicodeError) as err:
                            entry.update(revision="", missing=True)
                            result["errors"].append({"id": key, "route": route_id, "path": entry["guide"], "message": str(err)})
                        item["routes"].append(entry)
                    except (ValueError, OSError) as err:
                        result["errors"].append({"id": key, "route": route_id, "message": str(err)})
            try:
                body = _read(root, item["guide"], {".md"})
                body.decode("utf-8-sig")
                item["revision"] = hashlib.sha256(body).hexdigest()
            except (ValueError, OSError, UnicodeError) as err:
                item["revision"] = ""
                item["missing"] = True
                result["errors"].append({"id": key, "path": item["guide"], "message": str(err)})
            result["items"].append(item)
        except (ValueError, OSError) as err:
            result["errors"].append({"id": key if isinstance(key, str) else "", "index": index, "message": str(err)})
    return result


def document(root: Path, path: str) -> dict:
    body = _read(root, path, {".md", ".txt"})
    text = body.decode("utf-8-sig")
    resources, errors, seen = [], [], set()
    # 只解析普通 Markdown 引用；正文原样返回，网页仍负责 HTML 转义。
    for match in re.finditer(r"(!?)\[[^\[\]\n]*\]\(<?([^\n]*?)>?\)", text):
        source = re.sub(r'\s+["\'][^"\']*["\']$', "", match[2]).strip().strip("<>")
        if source in seen:
            continue
        seen.add(source)
        try:
            parsed = urlsplit(source)
            if parsed.scheme or parsed.netloc or source.startswith("#"):
                continue  # 外部链接由人的点击处理，不下载，不把它变成本地资源。
            decoded = unquote(parsed.path)
            if not decoded or decoded.startswith(("/", "\\")) or "\\" in decoded or ":" in decoded:
                raise Invalid("本地引用必须是内置相对路径")
            target = posixpath.normpath(decoded if any(decoded.startswith(p) for p in ROOTS)
                                        else posixpath.join(posixpath.dirname(path), decoded))
            suffix = Path(target).suffix.lower()
            kind = "image" if match[1] else "document"
            _path(root, target, IMAGES if kind == "image" else {".md", ".txt"})
            resources.append({"source": source, "target": target, "kind": kind})
        except (ValueError, OSError) as err:
            errors.append({"source": source, "message": str(err)})
    return {"text": text, "path": path, "revision": hashlib.sha256(body).hexdigest(),
            "resources": resources, "resource_errors": errors}


def read(root: Path, key: str, route: str = "") -> dict:
    catalog = listing(root)
    item = next((x for x in catalog["items"] if x["id"] == key), None)
    if item is None:
        raise KeyError("没有这份工具指南：" + key)
    if route:
        selected = next((x for x in item.get("routes", []) if x["id"] == route), None)
        if selected is None:
            raise KeyError("没有明确记录的方案：" + route)
        return {**item, "selected_route": route, "route": selected, **document(root, selected["guide"])}
    return {**item, **document(root, item["guide"])}
