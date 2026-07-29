"""个人 Wiki 反向代理 — /wiki。

本机单独跑一份 Quartz（127.0.0.1:8080），ngrok 免费版一条隧道只转发本 app
所在端口，8080 出不了公网。把 Wiki 挂在 /wiki 底下走同一条隧道。

Quartz 页面里的资源/内部链接都是相对路径，且每页的 "../" 层数是按该页真实
目录深度精确算的（叶子页 0 层，一层子目录 1 层，以此类推），不多不少。相对
路径的解析对"整体加前缀"是平移不变的，所以只要原样转发路径（不改写、不
强加/去掉尾斜杠），/wiki 前缀会被正确地叠加进每一层相对引用，不需要额外
补偏移逻辑。原样转发时如果 Quartz 自己发 30x（比如某个 slug 的 canonical
形式跟请求的尾斜杠不一致），要把 Location 头补上 /wiki 前缀再还给浏览器，
否则会把用户带出前缀跳到本 app 的域名根。

侧边栏目录树 / 搜索结果卡片点了 404：这两处不是走静态相对链接，是页面
自带的 JS（explorer / search）在点击时现算 `data-basepath + "/" + slug`
拼绝对路径。`data-basepath` 由 Quartz 的 renderPage.tsx 写进 <body> 标签，
但只要是 `quartz build --serve`（本机这个部署方式）就硬编码成空——它假设
dev server 永远部署在域名根，不知道自己被套了 /wiki 前缀。改 Quartz 项目
本身的 baseUrl 没用（--serve 模式下这行判断直接忽视 baseUrl）。只能在这层
代理把响应体里的 `data-basepath` 属性原地改写成 `data-basepath="/wiki"`
——只有 <body> 标签这一处，处理一次即可。

vault 里正好有个真实存在的顶层文件夹叫「wiki」（personal wiki 分类，装
synthesis/concepts/entities 等），跟我们代理的 /wiki 前缀撞名。大部分内部
链接靠上面说的"相对路径整体平移不变"正确落到 /wiki/wiki/... 这层双重路径。
但 Quartz 自己「文件夹目录页」列子项那个组件，在给「wiki」这个顶层文件夹
生成自己的子项链接时有个真实 bug——直接在 Quartz 源站（不经过我们代理）
验证过：`/wiki/`（文件夹目录页）列出的子项 href 漏算了一层，写成
`../synthesis/xxx` 而不是 `../wiki/synthesis/xxx`，比该到达的深度浅一层，
点了会真的跳出 wiki 落到域名根去。这是 Quartz 自身的 bug，不是我们代理引入
的，不打算去改 /Users/mark/quartz 那个独立项目。改用兜底：upstream 404 时，
如果请求路径本身还没带 "wiki/" 前缀，就用 "wiki/" + 路径再试一次；命中了
说明本来就该用双重路径，302 带浏览器纠正过去（不能直接吞下内容原样返回——
被代理返回的内容里嵌的 slug 跟地址栏 URL 不匹配，会让这页面自己往下的相对
链接又算错一层）。
"""
from __future__ import annotations

import re

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response

router = APIRouter(tags=["wiki"])

QUARTZ_ORIGIN = "http://127.0.0.1:8080"
_DROP_HEADERS = {"content-length", "content-encoding", "transfer-encoding", "connection"}
_BASEPATH_RE = re.compile(rb'data-basepath(?:="[^"]*")?(?=[\s>])')


@router.get("/wiki")
def wiki_root_redirect():
    return RedirectResponse(url="/wiki/")


@router.get("/wiki/{path:path}")
async def wiki_proxy(path: str, request: Request):
    upstream_url = f"{QUARTZ_ORIGIN}/{path}"
    try:
        async with httpx.AsyncClient() as client:
            upstream = await client.get(upstream_url, timeout=10.0, follow_redirects=False)
            if upstream.status_code == 404 and path != "wiki" and not path.startswith("wiki/"):
                retry = await client.get(f"{QUARTZ_ORIGIN}/wiki/{path}", timeout=10.0, follow_redirects=False)
                if retry.status_code != 404:
                    qs = f"?{request.url.query}" if request.url.query else ""
                    return RedirectResponse(url=f"/wiki/wiki/{path}{qs}", status_code=302)
    except httpx.ConnectError:
        return Response(
            content="个人 Wiki 服务(127.0.0.1:8080)没启动，先把 Quartz serve 进程拉起来再试。",
            status_code=502,
            media_type="text/plain; charset=utf-8",
        )

    headers = {k: v for k, v in upstream.headers.items() if k.lower() not in _DROP_HEADERS}
    location = headers.get("location")
    if location and location.startswith("/"):
        headers["location"] = f"/wiki{location}"

    content = upstream.content
    content_type = upstream.headers.get("content-type", "")
    if "text/html" in content_type:
        content = _BASEPATH_RE.sub(b'data-basepath="/wiki"', content, count=1)

    return Response(
        content=content,
        status_code=upstream.status_code,
        headers=headers,
        media_type=upstream.headers.get("content-type"),
    )
