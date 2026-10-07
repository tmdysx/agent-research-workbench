---
编号: T14
名字: Three.js
类别: 技术栈
一句话: 3D 模型和动画：图解里能拖着转的结构图（浏览器自带的 WebGL 之上）
检查: 文件 工具库/下载/three/three.module.js
在哪: 工具库/下载/three
配套技能:
---
# T14 Three.js

## 用在哪

- 图解里的 3D 模型和动画，能拖着转（文献蓝图 S2-14、S2-15）

## 为什么要

- 作者 09-27：「有些东西需要动画演示更能理解原理，或者建模之类的，这个是我超越这两个软件的亮点」——3D 的图解（文献蓝图 S2-14、S2-15）
- WebGL 浏览器自带，不用装；Three.js 是在它上面最常用的库，开源（MIT），放在应用里不联网
- 2D 动画不用它：浏览器自带的 SVG / Canvas 就够

## 装在哪

已经下好了（09-27，作者授权，版本 0.186.1）：`工具库/下载/three/`——`three.module.js`（它会自己去拿旁边的 `three.core.js`）、`addons/controls/OrbitControls.js`，来源和校验见 `工具库/下载/清单.md`。

## 怎么调

图解页（沙箱里跑）：

```html
<script type="importmap">{"imports": {"three": "/lib/three/three.module.js",
  "three/addons/": "/lib/three/addons/"}}</script>
<script type="module">
  import * as THREE from 'three';
  import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
</script>
```
- 后台把 `/lib/` 指到 `工具库/下载/`，加「沙箱里也能用」的放行（文献蓝图 S2-10）

## 改动注意

- 升级先问人；addons 只放要用到的
