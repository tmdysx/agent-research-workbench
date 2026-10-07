/* 纯英文界面的对照表（设置 → 通用 → 语言 → English）。
   dict：界面上一整段中文 → 英文（网页画出来的一段字，整段一样才换）。
   parts：带数字、带名字的句式；最后一条把「A · B · C」拆开，逐段对照。
   只管界面上的字——你的文件、笔记、蓝图、工具卡、快捷指令这些内容不在这里，照你写的样子。
   以后网页上加了新的中文字，在这里补一行英文；English 档里调 enMissing() 能看到还有哪些没换。 */
(function () {
  const D = {
    // ---- 顶栏 · 三栏 ----
    '总览': 'Overview', '笔记本': 'Notebook', '外部资料入口': 'Intake', '全站检索': 'Search',
    '业务载荷': 'Modules', '治理': 'Governance', '存档': 'Snapshots', '问答': 'Q&A', '计划': 'Plans', '自动化': 'Automation',
    '技能': 'Skills', '工具': 'Tools', '快捷指令': 'Commands', '设置': 'Settings', '使用说明': 'Guide', '清理': 'Cleanup',
    '蓝图': 'Blueprint', '戒律': 'Rules', '源代码': 'Code', '论文': 'Paper', '文献': 'Literature', '实验': 'Experiments',
    '亮': 'Light', '暗': 'Dark', '禅读': 'Zen', '笔记': 'Notes',
    '后端断了 · 重连中…': 'Backend lost · reconnecting…', '没连后端 · 双击「启动.bat」': 'Backend not connected · double-click 启动.bat',
    '固定模块，不能删': 'Fixed module, cannot be deleted', '上一个': 'Previous', '下一个': 'Next',
    '没连后端：先双击「启动.bat」': 'Backend not connected: double-click 启动.bat first',
    '没连后端，加了也存不住。先双击「启动.bat」': 'Backend not connected, nothing would be saved. Double-click 启动.bat first',

    // ---- 总览 ----
    '本页目录': 'On this page', '关键路径': 'Critical path', '模块': 'Modules', '待你判断': 'Waiting for you',
    '最近的决定': 'Recent decisions', '还没有': 'None yet', '待拍板': 'To decide', '没有': 'None', '快捷键': 'Shortcuts',
    '笔记 / 导出给 agent': 'Notes / export for the agent', '收放侧栏': 'Show / hide the side column', '昼夜模式': 'Light / dark',
    '齐了': 'Done', '不够': 'Partial', '在做': 'Doing', '还没开始': 'Not started',
    '① 关键路径': '① Critical path', 'Critical Path — 谁卡着谁': 'Critical Path — who is blocking whom',
    '示意 · 要等 B-03 graph 做完才是真数据': 'Mock-up · real data comes once the dependency graph is built',
    '一句话说清最要紧的阻塞（由后端现算，不手写）。': 'One sentence on the most important blocker (computed by the backend, not typed by hand).',
    '根阻塞项': 'Root blocker', '为什么卡住': 'Why it is stuck', '等它的下一环': 'The next link waiting on it', '说明': 'Notes',
    '终点：最终交付物': 'End point: the final deliverable',
    '② 模块': '② Modules', 'Modules — 「资料/」下一个文件夹就是一个模块，点一行进去看': 'Modules — each folder under 资料/ is one module; click a row to open it',
    '文件数': 'Files', '大小': 'Size', '最近变动': 'Last changed', '谁加的': 'Added by', '默认': 'default', '文件夹里发现的': 'found in the folder',
    '人': 'you', '你': 'you',
    '③ 待你判断': '③ Waiting for you', 'Decisions — AI 攒着的，不打断你': 'Decisions — saved up by the AI instead of interrupting you',
    '全部问答 →': 'All Q&A →',
    '没有等你判断的事。agent 用 ask_human 提的问题会出现在这里，攒着一起处理。': 'Nothing is waiting for you. Questions an agent asks with ask_human appear here, to be handled together.',
    '你的决定，写一句就行': 'Your decision — one sentence is enough', '拍板': 'Decide',
    '写一句你的决定再拍板': 'Write your decision first', '已拍板，agent 下次看全貌就知道': 'Decided — the agent will see it next time it reads the overview',
    '④ 蓝图': '④ Blueprint', 'Blueprint — 资料/蓝图/ 的目标金字塔': 'Blueprint — the goal pyramid in 资料/蓝图/',
    '编号': 'Code', '目标': 'Goal', '状态': 'Status', '小目标做完': 'Small goals done',
    '怎么算做到': 'How we know it is done', '底下还没有 S2': 'No S2 below yet',
    '一个模块 = 「资料/」下一个文件夹 = 一页': 'One module = one folder under 资料/ = one page',
    '：点中间那条的标签进去，左边是目录，右边是预览。': ': click its tab on the middle bar — folder on the left, preview on the right.',
    '加减模块在「设置 → 模块」': 'Add and remove modules in Settings → Modules',
    '：删不会真删，只往笔记里写一句删除请求，复制给 agent，由它挪进项目根的 回收站/（第三栏最右「清理」看得见，能还原）。': ': “Delete” never really deletes — it writes a delete request into the notes for an agent, which moves the item into 回收站/ at the project root (see Cleanup at the far right of the third bar; it can be restored).',
    '按 N': 'Press N',
    '→ 记笔记。导出的那段就是给 agent 的指令，会自动带上你这次看了哪些文件、点了什么、拍了什么板。': '→ take a note. What you export is the instruction for the agent, and it includes which files you viewed, what you clicked and what you decided.',
    '（蓝图 S0 里还没写终极目标）': '(no ultimate goal written in blueprint S0 yet)',

    // ---- 笔记窗 ----
    '随堂笔记': 'Notes', '拖我移动 · 双击归位': 'Drag to move · double-click to reset', '写完点': 'When done, click ',
    '「记下」': '“Save”', '：存进这个模块的笔记本（笔记/ 文件夹里，一条一个编号）。': ': it goes into this module’s notebook (in the 笔记/ folder, one number per entry).',
    '「复制为 agent 指令」': '“Copy as agent instruction”',
    '会带上上次复制以后新记的笔记和页面状态，复制过的整段存进 笔记/历史/。': ' includes the notes since the last copy and the page state; every copied block is kept in 笔记/历史/.',
    '例：③ 里那两条清理候选我看过了，第一条可以删，第二条留着——它虽然没人引用，但是原始数据。\n让 agent 把第一条挪进回收站，第二条标成「人工保留」。': 'E.g. I checked the two cleanup candidates in ③: the first can go, keep the second — nothing refers to it, but it is raw data.\nAsk the agent to move the first into the recycle bin and mark the second “kept by hand”.',
    '记下': 'Save', '复制为 agent 指令': 'Copy as agent instruction', '清空': 'Clear',
    '＋ 快捷': '＋ Quick', '复制给 agent': 'Copy for agent', '想到什么，写下来…': 'Write what you think…', '还没有快捷指令': 'No commands yet',
    '截图': 'Screenshot', '去掉': 'Remove', '没连后端，贴不进来': 'Backend not connected — cannot add it',
    '图还在传，等一下': 'Images still uploading — one moment', '随堂笔记只收图片和录屏；别的文件拖到页面别处，放进外部资料入口': 'The notes window only takes images and recordings; drop other files elsewhere on the page to put them into Intake',
    '录屏': 'Record', '等你框选…': 'Select an area…', '录屏中…': 'Recording…', '抽画面…': 'Getting frames…', '正在录屏': 'Already recording',
    '系统录屏没叫出来：按 Win+Shift+R 录好，把 mp4 拖进小窗': 'The system recorder did not open: record with Win+Shift+R and drag the mp4 into the window',
    '录屏的画面还在抽，等一下': 'Still getting frames from the recording — one moment', '这张图打不开': 'Cannot open this image',
    '这段录屏打不开': 'Cannot open this recording', '读不出录屏有多长': 'Cannot tell how long the recording is', '画面没存上': 'Frames not saved', '没存上': 'Not saved', '没传上': 'Not uploaded',
    '随堂笔记只收图片（png、jpg、webp、gif）和录屏（mp4、webm）': 'The notes window only takes images (png, jpg, webp, gif) and recordings (mp4, webm)',
    // 画板
    '框': 'Box', '圈': 'Circle', '箭头': 'Arrow', '画笔': 'Pen', '文字': 'Text', '马赛克': 'Mosaic', '细': 'Thin', '粗': 'Thick',
    '撤销': 'Undo', '完成': 'Done', '看录屏': 'Watch', '红': 'Red', '黄': 'Yellow', '绿': 'Green', '蓝': 'Blue', '白': 'White', '黑': 'Black',
    // 设置 → 截图与录屏
    '截图与录屏': 'Screenshots & recording', '截图快捷键': 'Screenshot shortcut', '录屏快捷键': 'Recording shortcut', '系统录屏存在哪': 'Where the system saves recordings',
    '恢复默认': 'Restore defaults', '在用': 'Active', '被别的程序占了，换一个': 'Taken by another program — pick another', '不用': 'Off',
    '重启后台后生效': 'Takes effect after restarting the backend', '这台电脑用不了': 'Not available on this computer', '你改过的': 'Changed by you',
    '截图工具的默认': 'Snipping Tool default', '按下新的组合…': 'Press the new combination…', '要带上 Ctrl 或 Alt': 'Include Ctrl or Alt',
    '还没有这个文件夹：截图工具设置里打开「自动保存屏幕录制」，录一次就有了': 'No such folder yet: turn on “Automatically save screen recordings” in Snipping Tool settings, then record once',
    '截图和录屏的快捷键不能一样': 'The screenshot and recording shortcuts cannot be the same', '存好了': 'Saved',
    '框选中…': 'Selecting…',
    '网页有新版本：你停手就自己刷新': 'New version of the page: it refreshes itself once you pause',
    // 自动化仪表盘
    '仪表盘': 'Dashboard', '开工': 'Start', '开工单': 'Work order',
    '运转 · 自动化/日志/': 'Running · 自动化/日志/', '交付 · 自动化/交付/': 'Deliveries · 自动化/交付/',
    '好了': 'Good', '能转，建议补': 'Can run, better fix', '要补': 'Needs fixing',
    '未发动': 'Not started', '已发动': 'Started', '熄火': 'Stop', '熄火了': 'Stopped', '发动': 'Start',
    '就绪，可以发动': 'Ready to start', '已发动 · 等 agent 转': 'Started · waiting for the agent', '机器已发动 · 等 agent 转': 'Machine started · waiting for the agent',
    '这次做': 'This time', '档位': 'Level', '最多': 'At most', '必停': 'Must stop', '还没选': 'Not chosen yet', '没选': 'Not chosen', '改 →': 'Change →', '去补 →': 'Fix →',
    '删 / 搬文件、改核心、公开发布、花钱、装软件': 'deleting / moving files, changing the core, publishing, spending money, installing software',
    'Claude Code 里贴：': 'Paste into Claude Code:', '复制': 'Copy', '没写怎么验': 'No check written',
    '这次做什么': 'What to do this time', '怎么转': 'How it runs', '同一件失败': 'Stop after', '次就停': 'failures on one item',
    '半自动：新写的计划、每件的验收都等你点头': 'Semi-auto: each new plan and each acceptance waits for your nod',
    '保存开工单': 'Save work order', '回仪表盘': 'Back to dashboard', '开工单存好了': 'Work order saved', '蓝图里还没有目标。': 'No goals in the blueprint yet.',
    '待你验收': 'Waiting for your check', '验收通过': 'Accept', '打回': 'Send back',
    '不行的话写一句为什么，agent 照着改': 'If not, write one sentence why — the agent will fix it', '写一句为什么，agent 照着改': 'Write one sentence why — the agent will fix it',
    '发动了：在 Claude Code 里贴 /loop /advance': 'Started: paste /loop /advance into Claude Code', '熄火了：agent 下一圈看见就停': 'Stopped: the agent stops at its next round',
    '复制好了，贴进 Claude Code': 'Copied — paste it into Claude Code', '没复制上，手动选中那一行': 'Not copied — select the line by hand',
    '待你装': 'To install', '装好了': 'Installed', '待你装：agent 找的，照下面「怎么装」装好，点「装好了」': 'To install: found by the agent — install it as described below, then click “Installed”',
    '档位、圈数、这次做什么：在「自动化」页的开工单里 →': 'Level, rounds and what to do: in the work order on the Automation page →',
    '没连后端，看不到。日志在 自动化/日志/，交付单在 自动化/交付/。': 'Backend not connected. Logs are in 自动化/日志/, delivery slips in 自动化/交付/.', '没连后端，截不了': 'Backend not connected — cannot take a screenshot', '正在等你框选': 'Waiting for you to select an area',
    '系统截图没叫出来：按 Win+Shift+S 截好，在这里 Ctrl+V 贴': 'The system screenshot did not open: take one with Win+Shift+S and paste it here with Ctrl+V',
    '这台电脑叫不出系统截图：用系统自带的截图截好，在笔记里 Ctrl+V 贴': 'This computer cannot open the system screenshot: take one with the system tool and paste it into the note with Ctrl+V',
    '已复制，粘给 agent': 'Copied — paste it to the agent', '没复制上，但已存进库': 'Not copied, but saved', '没复制上，再点一次': 'Not copied — click again',
    '先写点什么': 'Write something first', '没连后端，记不进笔记本。先双击「启动.bat」': 'Backend not connected — cannot save to the notebook. Double-click 启动.bat first',

    // ---- 笔记本 ----
    '笔记本 · 笔记/': 'Notebooks · 笔记/', '历史 · 复制过的和改动记录（不删）': 'History · copied blocks and edit log (never deleted)',
    '改动记录': 'Edit log', '改': 'Edit', '删': 'Delete', '保存': 'Save', '取消': 'Cancel',
    '这本还没有笔记。按 N 打开笔记窗，写完点「记下」。': 'This notebook is empty. Press N to open the note window and click “Save”.',
    '没连后端，看不到笔记本。笔记文件在项目根的 笔记/ 文件夹里。': 'Backend not connected — cannot show the notebook. Note files are in 笔记/ at the project root.',
    '改好了（原文在 笔记/历史/改动记录.md）': 'Updated (the original is in 笔记/历史/改动记录.md)',
    '改了核心': 'core changed', '删除请求': 'delete request', '新建模块': 'new module', '放进来': 'added', '放进外部资料入口': 'added to intake',
    '装技能': 'installed skill', '复制技能': 'copied skill', '新建快捷指令': 'New command', '改快捷指令': 'edited command',
    '装快捷指令进 Claude Code': 'installed command into Claude Code', '改了自动化设置': 'automation settings changed',
    '改了模块设置': 'module settings changed', '改了模块顺序': 'module order changed',

    // ---- 外部资料入口 ----
    '空的：把文件拖进网页': 'Empty: drag files onto the page',
    '外面的材料扔进来，先放在 资料/_外部资料入口/。agent 给几个候选，你点一个才放进模块；一模一样的文件只存一份。': 'Drop outside material here; it lands in 资料/_外部资料入口/ first. An agent suggests a few candidates, and nothing moves into a module until you click one. Identical files are stored once.',
    '把文件或整个文件夹拖到这里': 'Drag files or whole folders here', '也可以点这里选文件': 'or click here to choose files',
    '生成分拣指令': 'Make a sorting instruction', '外部资料入口是空的。': 'The intake is empty.', '外部资料入口是空的': 'The intake is empty',
    '放进来的': 'added', '放这里': 'Put it here', '放进去': 'Put it in', '都不对，我自己选：': 'None fit — I’ll choose:',
    '还没有候选：等 agent 看过给建议，或点上面「生成分拣指令」。': 'No candidates yet: wait for an agent to suggest some, or click “Make a sorting instruction” above.',
    '高': 'high', '中': 'medium', '低': 'low',
    '没连后端，收不了。先双击「启动.bat」': 'Backend not connected — cannot receive files. Double-click 启动.bat first', '没收成': 'Could not receive the files',
    '没连后端，看不到。双击「启动.bat」再打开。': 'Backend not connected — nothing to show. Double-click 启动.bat and reopen.',

    // ---- 全站检索 ----
    '整个项目 · 点文件在右边看': 'Whole project · click a file to view it on the right',
    '搜所有模块的文件名和文件内容，还有笔记、决定、蓝图。点一条直接打开那个文件。': 'Searches file names and contents in every module, plus notes, decisions and the blueprint. Click a result to open that file.',
    '输入要找的词': 'Type what you are looking for', '没连后端，搜不了。': 'Backend not connected — cannot search.',
    '决定': 'Decisions', '草稿': 'Draft',

    // ---- 模块页 ----
    '总的': 'Main', '目录': 'Contents', '其它': 'Other', '本模块戒律': 'This module’s rules',
    '收起目录': 'Hide folder', '显示目录': 'Show folder', '写进笔记': 'Add to notes', '新标签打开': 'Open in new tab',
    '一行版': 'one line each', '戒律模块': 'Rules module', '源代码模块': 'Code module', '蓝图模块': 'Blueprint module',
    '代码地图': 'Code map', '每个文件一句话': 'one line per file', '链接': 'link', '项目根目录': 'Project root',
    '（开头没写说明）': '(no description at the top)',
    '出了问题先在这儿找是哪一块，跟 agent 说「是后台的笔记那块」比说「它不动了」准得多。点文件名看代码。': 'When something breaks, find the part here first — telling an agent “it is the notes part of the backend” is far more precise than “it stopped working”. Click a file name to see the code.',
    '文件': 'Files', '左边点一个文件看预览。': 'Click a file on the left to preview it.', '（还没写一句话说明）': '(no one-line description yet)',
    '起步模块': 'starter module', '挂的链接（原件待在原位）：': 'Linked files (the originals stay where they are): ',
    '文件太多，只列了前 3000 个': 'Too many files — showing the first 3000', '文件太大，只显示了前 200 KB。': 'The file is large — showing the first 200 KB.',
    '没连后端，看不到模块里的东西。双击「启动.bat」再打开。': 'Backend not connected — cannot show this module. Double-click 启动.bat and reopen.',
    '回总览': 'Back to overview',
    '这是个文件夹（或看不了的文件），在「全站检索」左边能展开看。': 'This is a folder (or a file that cannot be previewed); expand it on the left of Search.',

    // ---- 问答 ----
    '你和 agent 之间的一问一答。agent 有问题先查你拍过的板、戒律、计划、笔记，查不到才到你这；以后查出来的违规也在这里等你判断。': 'Questions and answers between you and the agent. The agent first checks your past decisions, the rules, the plans and the notes; only what it cannot find comes to you. Rule violations found later will wait here too.',
    '还没有问答。agent 用 ask_human 提问、find_answer 查答案，都会出现在这里。': 'No Q&A yet. Questions an agent asks with ask_human and answers it looks up with find_answer will appear here.',
    '答疑': 'Answers', '待删请求': 'Delete requests', '问题': 'Question', '写一句再拍板': 'Write one sentence, then decide', '没连后端，看不到。': 'Backend not connected — nothing to show.',
    '自动答上': 'answered automatically', '转给你了': 'passed to you', '你拍板了': 'you decided',
    '问题：': 'Question: ', '运行：': 'Run: ', '查过：': 'Checked: ', '用的：': 'Used: ', '答案：': 'Answer: ',
    '转成待拍板：': 'Became item to decide: ', '你拍板：': 'Your decision: ', '答的是：': 'Answers: ',

    // ---- 计划 ----
    '待归位 · 还没挂到目标下': 'To be filed · not under a goal yet', '计划 · 计划/': 'Plans · 计划/',
    '还没有计划。在这个项目文件夹里打开 Claude Code，用计划模式做的计划会自动存进 计划/。': 'No plans yet. Open Claude Code in this project folder; plans made in plan mode are saved into 计划/ automatically.',
    '没连后端，看不到计划。计划文件在项目根的 计划/ 文件夹里。': 'Backend not connected — cannot show plans. Plan files are in 计划/ at the project root.',

    // ---- 自动化 ----
    '工作流 · 自动化/工作流/': 'Workflows · 自动化/工作流/', '日志 · 自动化/日志/': 'Log · 自动化/日志/', '还没跑过': 'Not run yet',
    'agent 的问题和答疑在「问答」页': 'The agent’s questions and answers are on the Q&A page', '改设置': 'change settings',
    '。转圈的是 agent（在项目文件夹里的 Claude Code 敲': '. The agent does the running (type', '），这里只看。': ' in Claude Code in the project folder); this page only watches.',
    '还没有工作流和运行。': 'No workflows or runs yet.',
    '没连后端，看不到。日志在 自动化/日志/，答疑在 自动化/答疑/。': 'Backend not connected — nothing to show. The log is in 自动化/日志/, answers in 自动化/答疑/.',
    '在跑': 'running', '停了等你': 'stopped, waiting for you', '跑完待验收': 'finished, waiting for your check', '失败停了': 'failed and stopped',
    '在做：': 'Working on: ', '做了：': 'Did: ', '结果：': 'Result: ', '下一步：': 'Next: ', '自动推进': 'Auto-advance',

    // ---- 技能 ----
    '应用自带的技能，点了才装。「本项目」只给这个项目里的 agent 用；「本机」这台电脑所有项目都能用。那边已经有不一样的同名技能，会先问你；覆盖前旧的先备份到 索引/技能备份/。': 'Skills that come with the app, installed only when you click. “This project” is for agents in this project only; “this computer” is for every project on this computer. If a different skill with the same name is already there, you are asked first, and the old one is backed up to 索引/技能备份/.',
    '没装': 'Not installed', '已装·不一样': 'Installed · different', '本机已装': 'Installed on this computer', '本项目已装': 'Installed in this project',
    '本机已装，但跟库里的不一样': 'Installed on this computer, but different from the library', '本项目已装，但跟库里的不一样': 'Installed in this project, but different from the library',
    '装到本项目': 'Install to this project', '装到本机': 'Install on this computer', '复制一份改': 'Copy and edit',
    '技能库是空的。把技能文件夹放进应用根目录的 技能库/ 就会出现。': 'The skill library is empty. Put a skill folder into 技能库/ in the app folder and it will show up.',
    '空的': 'empty', '没装，原来那份没动': 'Not installed; the existing one was left alone', '没装成': 'Could not install',

    // ---- 工具 ----
    '技术栈': 'Tech stack', '外部工具': 'External tools', '查着…': 'checking…', '内置': 'built in', '未接通': 'not connected', '接通': 'connected',
    '不用装': 'nothing to install', '不用装（内置）': 'nothing to install (built in)',
    '加一个：在 工具库/ 放一张卡（抄一张改，用下一个 T 号；类别写「技术栈」或「外部工具」）': 'To add one: put a card into 工具库/ (copy one and edit it, use the next T number; set the category to 技术栈 or 外部工具)',
    '再查一遍': 'Check again', '放进笔记': 'Add to notes', '工具库是空的。': 'The tool library is empty.',
    '网页只看接没接通，不替你跑工具——调工具是 agent 的活。': 'The page only checks whether a tool is connected; it never runs tools for you — calling tools is the agent’s job.',
    '没连后端，看不到。卡片在应用根目录的 工具库/ 里。': 'Backend not connected — nothing to show. The cards are in 工具库/ in the app folder.',

    // ---- 快捷指令 ----
    '常用的指令存成模板：在笔记窗顶上点一下，自动填好当前项目、模块、文件，追加进笔记。同一份也能装进 Claude Code，在那边敲 /英文短名。': 'Frequent instructions saved as templates: click one at the top of the note window and it fills in the current project, module and file, then adds it to your note. The same one can be installed into Claude Code, where you type /short-name.',
    '＋ 新建': '+ New', '用一下': 'Use', '装进 Claude Code（本项目）': 'Install into Claude Code (this project)', '装进 Claude Code（本机）': 'Install into Claude Code (this computer)',
    '还没有快捷指令。点「＋ 新建」。': 'No commands yet. Click “+ New”.',
    '名字，比如 整理本周进展': 'Name, e.g. 整理本周进展', '英文短名，比如 weekly-review（Claude Code 里敲 /它）': 'Short English name, e.g. weekly-review (type /it in Claude Code)',
    '一句话：它是干什么的': 'One line: what it is for', '点一下插入空位：': 'Click to insert a slot:', '指令正文': 'Instruction text',
    '正在写的新建 / 改动还没保存，丢掉吗？': 'What you are writing (new or edit) is not saved yet. Discard it?', '改好了': 'Updated', '存好了，笔记窗顶上多了一个按钮': 'Saved — there is a new button at the top of the note window',

    // ---- 设置 ----
    '通用 General': 'General', '模块 Modules': 'Modules', '自动化 Automation': 'Automation', '通用': 'General',
    '跟着你走（存在这台电脑的浏览器里），不改项目': 'Follows you (kept in this computer’s browser); does not change the project',
    '只看中文，英文都藏起来': 'Chinese only, English hidden', '中英对照': '中英对照 (Chinese with English)', '标签后面跟英文': 'labels followed by English',
    '界面全是英文': 'the whole interface in English',
    '点一下就换，不用保存（换进、换出 English 会重新打开一次页面）。换的是界面上的字；你的文件、笔记、蓝图这些内容照你写的样子。': 'Switches at once, nothing to save (switching into or out of English reopens the page once). Only the interface changes; your files, notes and blueprint stay exactly as you wrote them.',
    '项目名': 'Project name', '项目在哪': 'Location', '终极目标': 'Ultimate goal', '（蓝图 S0 里还没写）': '(not written in blueprint S0 yet)',
    '第二栏的顺序、英文名、一句话；存在这个项目里': 'Order on the second bar, English names, one-line descriptions; saved in this project',
    '顺序': 'Order', '英文名': 'English name', '一句话': 'One line', '模块戒律': 'Module rules', '固定': 'fixed',
    '比如 Literature': 'e.g. Literature', '一句话说它是干什么的': 'One line on what it is for', '有，看 →': 'Yes, view →',
    '往前挪': 'Move up', '往后挪': 'Move down', '不会真删：往它的笔记里写一条删除请求，交给 agent': 'Does not really delete: writes a delete request into its notes for an agent',
    '保存模块设置': 'Save module settings', '不改了，恢复': 'Discard changes', '加一个模块': 'Add a module',
    '名字（也是文件夹名），比如 数据': 'Name (also the folder name), e.g. 数据', '英文名，比如 Data': 'English name, e.g. Data',
    '一句话说它是干什么的（可空）': 'One line on what it is for (optional)', '加上': 'Add',
    '加上就在 资料/ 下建好同名文件夹，第二栏多一个。': '“Add” creates a folder of that name under 资料/ and a new tab on the second bar. ',
    '不会真删：只往那个模块的笔记里写一条删除请求，复制给 agent，由它挪进 回收站/（能还原）。固定的三个（蓝图 · 戒律 · 源代码）不能删，永远在最前；改名是挪文件夹，写进笔记交给 agent。': ' never really deletes: it only writes a delete request into that module’s notes; copy it to an agent, which moves it into 回收站/ (it can be restored). The three fixed modules (Blueprint · Rules · Code) cannot be deleted and always come first; renaming moves a folder — write it in the notes for an agent.',
    'agent 自己转的时候，放手到什么程度': 'How much the agent may do on its own',
    '手动：不自己转，你复制指令给 agent': 'Manual: it does not run on its own; you copy instructions to the agent',
    '半自动：自己转，但新写的计划、每件的验收都等你点头': 'Semi-auto: it runs on its own, but new plans and every acceptance wait for your nod',
    '自动：计划和做都自己来，只在必停时停': 'Auto: it plans and works by itself, stopping only where it must',
    '每次最多': 'At most', '圈，转满就停': 'rounds per run, then it stops',
    '不管哪一档，碰到要删或搬文件、改核心、公开发布、花钱，都一定停下来等你。': 'At every level it always stops and waits for you before deleting or moving files, changing the core, publishing, or spending money.',
    '先写模块的名字': 'Write the module name first', '没有要存的': 'Nothing to save', '顺序换了': 'order changed',
    '换成中文': 'Switched to Chinese', '换成中英对照': 'Switched to Chinese with English', '没连后端，改不了。': 'Backend not connected — cannot change settings.',

    // ---- 清理 ----
    '回收站 · 回收站/': 'Recycle bin · 回收站/',
    '回收站在项目根的 回收站/。挪进去、还原都是 agent 做（照你的删除请求），网页只看不动；彻底删掉是另一件事，要你明说。': 'The recycle bin is 回收站/ at the project root. An agent moves things in and restores them (following your delete requests); the page only looks. Deleting for good is a separate step that needs your explicit word.',
    '没有待删的，回收站也是空的。': 'No delete requests, and the recycle bin is empty.',
    '没连后端，看不到。回收站在项目根的 回收站/ 里。': 'Backend not connected — nothing to show. The recycle bin is 回收站/ at the project root.',
    '在回收站': 'in the bin', '已还原': 'restored', '原来在：': 'Originally at: ', '放在：': 'Kept at: ', '为什么：': 'Why: ',
    '删除请求：': 'Delete request: ', '还原于：': 'Restored at: ',
    '放进笔记：请照这条删': 'Add to notes: please delete as requested', '放进笔记：请还原': 'Add to notes: please restore',
    '放进笔记：请彻底删掉': 'Add to notes: please delete for good',

    // ---- 存档 ----
    '＋ 存一档': '+ New snapshot', '还没有存档': 'No snapshots yet', '定': 'settled',
    '每一档都记下全部文件的指纹；复制多少由你选。一档一个文件夹，放在 存档/ 下，资源管理器里直接能翻。': 'Every snapshot records the fingerprints of all files; you choose how much to copy. One snapshot = one folder under 存档/, which you can browse in Explorer.',
    '名字，比如 表1跑完': 'Name, e.g. Table 1 done', '为什么存：做完了什么': 'Why: what was just finished',
    '全量': 'Full', '自定义': 'Custom', '只记指纹': 'Fingerprints only',
    '整个项目复制一份（大关口用：投稿前、实验全部跑完）': 'copy the whole project (for milestones: before submitting, after all experiments)',
    '只复制你勾的（平时用：保住正在改的那几样）': 'copy only what you tick (everyday: protect what you are editing)',
    '不复制，只做个记号，以后对照用': 'copy nothing, just a marker to compare against later',
    '勾上要复制的（勾文件夹 = 里面全部）：': 'Tick what to copy (a folder = everything in it):',
    '展开': 'expand', '收起': 'collapse', '算着…': 'calculating…', '存': 'Save', '存着…': 'Saving…',
    '复制了': 'Copied', '记了指纹': 'Fingerprinted', '检查': 'Checks', '当时': 'At the time', '文件夹': 'Folder',
    '没带检查': 'no checks', '跟': 'Compare with', '现在': 'now', '比一比': 'Compare', '复活整档': 'Restore whole snapshot',
    '定性：这是安全点': 'Settle: this is a safe point', '删这一档': 'Delete this snapshot',
    '筛一下：输入文件名的一部分': 'Filter: type part of a file name', '看那时候': 'view as it was', '复活这个': 'restore this',
    '这一档只记了指纹，没复制文件。单个文件要是别的档里有一模一样的副本，在「比一比」里照样能看、能复活。': 'This snapshot only recorded fingerprints and copied no files. If another snapshot holds an identical copy of a file, you can still view and restore it from “Compare”.',
    '没有对得上的': 'No match', '给这一档起个名字': 'Give this snapshot a name',
    '自定义要勾上至少一个；什么都不复制就选「只记指纹」': 'Custom needs at least one tick; to copy nothing, choose “Fingerprints only”',
    '跟现在一样，没什么要复活的': 'Same as now — nothing to restore',
    '没连后端，看不到。存档在项目根的 存档/ 里，一档一个文件夹。': 'Backend not connected — nothing to show. Snapshots are in 存档/ at the project root, one folder each.',
    '绿档': 'green', '黄档': 'yellow', '已定性': 'settled', '今天': 'today', '昨天': 'yesterday',
    '还没有定性过的存档：先在存档页把一档定性，它以前进回收站的才能彻底删': 'No settled snapshot yet: settle one on the Snapshots page first; only what entered the bin before it can be deleted for good',

    // ---- 清理（这次加的）----
    '回收站在项目根的 回收站/：删模块、复活换下来的、删掉的存档、agent 照删除请求挪的，都在这，一件（一批）一个编号。还原直接点；彻底删掉只能删定性过的存档以前进来的，还要再确认一次。': 'The recycle bin is 回收站/ at the project root: deleted modules, files replaced by a restore, deleted snapshots and whatever an agent moved on a delete request all land here, one number per item (or batch). Restore with one click; deleting for good only works for what entered before a settled snapshot, and asks once more.',
    '还没有定性过的存档：在存档页把一档定性以后，它以前进回收站的才能彻底删掉。': 'No settled snapshot yet: once you settle one on the Snapshots page, what entered the bin before it can be deleted for good.',
    '全部彻底删掉': 'Delete all for good', '还原': 'Restore', '彻底删掉': 'Delete for good',
    '彻底删掉：要等有一档存档定性、而且它是在那以前进来的': 'Delete for good: needs a settled snapshot, and the item must have entered before it',
    '已彻底删掉': 'deleted for good', '从哪来：': 'From: ', '大小：': 'Size: ', '彻底删于：': 'Deleted for good at: ',
    '设置里删模块': 'module deleted in Settings', 'agent 照删除请求挪的': 'moved by an agent on a delete request',

    // ---- 设置（这次改的）----
    '：空文件夹直接删；里面有文件先问你，确认后整个文件夹挪进 回收站/（能还原，不是真删）。固定的三个（蓝图 · 戒律 · 源代码）不能删，永远在最前；改名是挪文件夹，写进笔记交给 agent。': ': an empty folder is deleted straight away; if it has files you are asked first, then the whole folder moves into 回收站/ (it can be restored — nothing is really deleted). The three fixed modules (Blueprint · Rules · Code) cannot be deleted and always come first; renaming moves a folder — write it in the notes for an agent.',
    '空的直接删；有文件先问你，确认后挪进回收站（能还原）': 'Empty: deleted at once; with files: asks first, then moves it into the recycle bin (restorable)',
    '：删的时候空的直接删，有文件先问你，确认后整个文件夹挪进项目根的 回收站/（第三栏最右「清理」看得见，能还原）。': ': an empty module is deleted at once; one with files asks first, then its whole folder moves into 回收站/ at the project root (see Cleanup at the far right of the third bar; it can be restored).',

    // ---- 使用说明 ----
    '没连后端，看不到说明书。也可以直接打开应用文件夹里的 使用说明.md。': 'Backend not connected — cannot show the guide. You can also open 使用说明.en.md in the app folder.',

    // ---- 禅读 ----
    '这是最后一篇了': 'This is the last one', '这是第一篇': 'This is the first one', '这是最后一个模块了': 'This is the last module',
    '这是第一个模块': 'This is the first module', '这是最后一个目标了': 'This is the last goal', '这是第一个目标': 'This is the first goal',
    'English 暂停了：有别的东西（多半是浏览器的自动翻译或翻译插件）一直在改页面上的字。把它对这个网址关掉，再刷新': 'English paused: something (most likely the browser’s auto-translate or a translation extension) keeps changing the text on the page. Turn it off for this address, then refresh.',
    '已经是最后一篇': 'Already the last one', '已经是第一篇': 'Already the first one', '再按一次 ↓': 'press ↓ again', '再按一次 ↑': 'press ↑ again'
  };

  // 一段（「A · B · C」里的一段）的句式：带数字、带名字的
  const SEG = [
    [/^(\d+) 个文件$/, function (m, n) { return pl(n, 'file'); }], [/^资料\/ (\d+) 个文件$/, function (m, n) { return '资料/ ' + pl(n, 'file'); }], [/^已连后端$/, 'Connected'],
    [/^(\d+) 条$/, function (m, n) { return pl(n, 'item'); }], [/^共 (\d+) 条$/, '$1 in all'], [/^(\d+) 个$/, '$1'], [/^(\d+) 份$/, '$1 files'],
    [/^(\d+) 圈$/, function (m, n) { return pl(n, 'round'); }], [/^(\d+) 字$/, '$1 chars'], [/^第 (\d+) 圈$/, 'round $1'],
    [/^(\d+)\/(\d+) 接通$/, '$1/$2 connected'], [/^做完 (\d+)\/(\d+)$/, 'done $1/$2'], [/^挂了 (\d+) 个链接$/, function (m, n) { return pl(n, 'link'); }],
    [/^(\d+) 个程序文件$/, '$1 program files'], [/^待分拣 (\d+) 个$/, '$1 to sort'], [/^档 (\d)$/, 'Level $1'],
    [/^开始于 (.+)$/, 'started $1'], [/^最后一圈 (.+)$/, 'last round $1'], [/^在做 (.+)$/, 'working on $1'],
    [/^(.+) 问的$/, function (m, w) { return 'asked by ' + (D[w] || w); }], [/^(.+) 挪的$/, function (m, w) { return 'moved by ' + (D[w] || w); }],
    [/^(.+) 加的$/, function (m, w) { return 'added by ' + (D[w] || w); }],
    [/^把握 (高|中|低)$/, function (m, c) { return 'confidence ' + D[c]; }],
    [/^原来是 (.+)$/, 'originally $1'], [/^配套技能：(.+)$/, 'matching skill: $1'], [/^P 计划$/, 'P plan'], [/^R 设计参考$/, 'R design reference'],
    [/^字小一点（现在 (\d+)%）$/, 'Smaller text (now $1%)'], [/^字大一点（现在 (\d+)%）$/, 'Larger text (now $1%)'],
    [/^记在「(.+)」的笔记本$/, 'noted in the “$1” notebook'],
    [/^已存$/, 'saved'], [/^没存上$/, 'not saved'], [/^后端断了，先存本机$/, 'backend offline, kept on this computer'],
    [/^每次最多 (\d+) 圈$/, 'at most $1 rounds per run'],
    [/^一共 (.+)$/, 'total $1'], [/^(.+) 存的$/, function (m, w) { return 'saved by ' + (D[w] || w); }], [/^已定性（(.+)）$/, 'settled ($1)'],
    [/^蓝图小目标做完 (\d+)\/(\d+)$/, 'blueprint small goals done $1/$2'], [/^待拍板 (\d+) 条$/, '$1 to decide'], [/^最近的笔记 (.+)$/, 'latest note $1'],
    [/^(C\d+) 里那时候的样子$/, 'as it was in $1'], [/^最近的存档 (.+)$/, 'Latest snapshot $1'], [/^(\d+) 天前$/, '$1 days ago'],
    [/^复活 (C\d+) 换下来的$/, 'replaced when restoring $1'], [/^还原 (X\d+) 换下来的$/, 'replaced when restoring $1'],
    [/^删掉的存档 (C\d+)$/, 'deleted snapshot $1'], [/^(\d+) 字节$/, '$1 bytes'], [/^装在 (.+)$/, 'at $1']
  ];
  function pl(n, w) { return n + ' ' + w + (n === '1' ? '' : 's'); }
  function one(x) {
    const k = x.trim();
    if (!k) return x;
    if (Object.prototype.hasOwnProperty.call(D, k)) return x.replace(k, D[k]);
    for (let i = 0; i < SEG.length; i++) if (SEG[i][0].test(k)) return x.replace(k, k.replace(SEG[i][0], SEG[i][1]));
    return x;
  }

  window.UI_EN = {
    dict: D,
    parts: [
      // 整句的句式（带名字、带数字）
      [/^有 (\d+) 处要看一下：/, 'There are $1 things to check: '],
      [/^Blueprint — 资料\/蓝图\/ 的目标金字塔：(\d+) 个大目标，底下 (\d+) 个小目标做完 (\d+) 个；状态从小目标现算，点一行看$/,
        'Blueprint — the goal pyramid in 资料/蓝图/: $1 big goals, $3 of $2 small goals done; status is computed from the small goals — click a row'],
      [/^打开 (S[\d-]+) (.+) →$/, 'Open $1 $2 →'],
      [/^记到：(.+)$/, 'Saves to: $1'],
      [/^录屏 (\d+(?::\d+)+)$/, 'Rec $1'],
      [/^画面 (\d+)$/, 'Frame $1'],
      [/^录屏的画面没抽成：(.+)$/, 'Could not get frames: $1'],
      [/^开工准备 · (\d+)\/(\d+)$/, 'Readiness · $1/$2'],
      [/^交付 · 自动化\/交付\/ · (\d+) 件等你$/, 'Deliveries · 自动化/交付/ · $1 waiting'],
      [/^未就绪 · 还差 (\d+) 样：(.+)$/, 'Not ready · $1 missing: $2'],
      [/^运转中 (.+)$/, 'Running $1'],
      [/^交付 (\d+) 件等你验收$/, '$1 deliveries to check'],
      [/^(\d+) 件没做完$/, '$1 not done'],
      [/^验收通过：(.+)$/, 'Accepted: $1'],
      [/^打回了：(.+)$/, 'Sent back: $1'],
      [/^装好了：(.+)$/, 'Installed: $1'],
      [/^还有红灯，发动不了：(.+)$/, 'Red lamps left, cannot start: $1'],
      [/^截图记进了 (.+)$/, 'Screenshot saved as $1'],
      [/^录屏记进了 (.+)$/, 'Recording saved as $1'],
      [/^笔记\/(.+) · (\d+) 条。每条有编号，改和删之前原文先记进 笔记\/历史\/改动记录\.md。$/, '笔记/$1 · $2 entries. Every entry is numbered; before an edit or deletion the original goes into 笔记/历史/改动记录.md.'],
      [/^笔记\/历史\/(.+) · 只读，不删$/, '笔记/历史/$1 · read-only, never deleted'],
      [/^删掉 (\S+)？原文会先记进 笔记\/历史\/改动记录\.md，不会丢。$/, 'Delete $1? The original goes into 笔记/历史/改动记录.md first, so nothing is lost.'],
      [/^删了 (\S+)（原文在 笔记\/历史\/改动记录\.md）$/, 'Deleted $1 (the original is in 笔记/历史/改动记录.md)'],
      [/^记下了：(.+)$/, 'Saved: $1'],
      [/^空的。把文件放进 (.+)，这里会自己出现。$/, 'Empty. Put files into $1 and they show up here.'],
      [/^文件夹：(.+)$/, 'Folder: $1'],
      [/^没有「(.+)」这个模块（文件夹可能被挪走了）。$/, 'There is no module “$1” (its folder may have been moved).'],
      [/^这种文件网页里看不了，去资源管理器里打开：(.+)$/, 'This kind of file cannot be shown in the page; open it in Explorer: $1'],
      [/^编码：(.+)$/, 'Encoding: $1'],
      [/^(\d+) 个程序文件 · 每句取自文件开头的说明，现场读的$/, '$1 program files · each line is read live from the description at the top of the file'],
      [/^档位 (\d)：(.+) · 每次最多 (\d+) 圈 ·$/, function (m, l, t, n) { return 'Level ' + l + ': ' + (D[t] || t) + ' · at most ' + n + ' rounds per run ·'; }],
      [/^存好了：档 (\d) · 每次最多 (\d+) 圈$/, 'Saved: level $1 · at most $2 rounds per run'],
      [/^存好了(：改了 (\d+) 个模块的说明)?([，：]顺序换了)?$/, function (m, a, n, b) { return 'Saved' + (n ? ': ' + n + ' module description(s) changed' : '') + (b ? (n ? ', ' : ': ') + 'order changed' : ''); }],
      [/^加上了：(.+)$/, 'Added: $1'],
      [/^没删任何东西：已记进「(.+)」的笔记（(.+)），复制给 agent 去删$/, 'Nothing deleted: noted in the “$1” notes ($2); copy it to an agent to carry out'],
      [/^已放进 (.+)$/, 'Moved into $1'],
      [/^正在收 (\d+) 个文件…$/, 'Receiving $1 files…'],
      [/^没找到「(.+)」$/, 'Nothing found for “$1”'],
      [/^第 (\d+) 行：$/, 'Line $1:'],
      [/^已复制成「(.+)」：要改哪里，写进笔记交给 agent$/, 'Copied as “$1”: write what to change in the notes for an agent'],
      [/^(本项目|本机)已经有一份不一样的「(.+)」。\n覆盖吗？旧的会先备份到 索引\/ 下面，不会丢。$/, function (m, w, l) { return (w === '本机' ? 'This computer' : 'This project') + ' already has a different “' + l + '”.\nReplace it? The old one is backed up under 索引/ first, so nothing is lost.'; }],
      [/^(本项目|本机)已经装着一样的了$/, function (m, w) { return 'Already installed ' + (w === '本机' ? 'on this computer' : 'in this project'); }],
      [/^已装到(本项目|本机)(（旧的已备份）)?$/, function (m, w, b) { return 'Installed ' + (w === '本机' ? 'on this computer' : 'in this project') + (b ? ' (the old one was backed up)' : ''); }],
      [/^改「(.+)」$/, 'Edit “$1”'],
      [/^↓ 下一篇：/, '↓ Next: '], [/^↑ 上一篇：/, '↑ Previous: '],
      [/^没找到 (.+)：PATH 里没有，卡上写的「在哪」里也没有$/, '$1 not found: not on PATH, nor where the card says'],
      [/^(\d+) 秒没反应$/, 'no response in $1 seconds'], [/^退出码 (\d+)$/, 'exit code $1'],
      // 存档
      [/^(?:要复制 (\d+) 个文件、(.+?)|不复制文件) · 整个项目 (\d+) 个文件、(.+?)（都记指纹）· 盘上还剩 (.+)$/, function (m, n, b, an, ab, free) {
        return (n ? 'copies ' + n + ' files, ' + b : 'copies no files') + ' · whole project ' + an + ' files, ' + ab + ' (all fingerprinted) · ' + free + ' free on disk'; }],
      [/^(\d+) 个文件，(\S+ ?\S*?)(?:（(.+)）)?$/, function (m, n, b, w) { return n + ' files, ' + b + (w ? ' (' + w + ')' : ''); }],
      [/^全部 (\d+) 个文件，(.+)$/, 'all $1 files, $2'],
      [/^复制了的文件（(\d+)）$/, 'Copied files ($1)'], [/^还有 (\d+) 个，筛一下再看$/, '$1 more — filter to see them'],
      [/^从 (C\d+) 到(.+)：$/, function (m, a, b) { return 'From ' + a + ' to ' + (D[b] || b) + ':'; }],
      [/^改了的（(\d+)）$/, 'Changed ($1)'], [/^删了的（(\d+)）$/, 'Deleted ($1)'], [/^新加的（(\d+)）$/, 'Added ($1)'],
      [/^存好了：(C\d+)「(.+)」· 复制了 (\d+) 个文件$/, 'Saved: $1 “$2” · copied $3 files'],
      [/^复活了 (C\d+)：换回 (\d+) 个、放回 (\d+) 个、挪进回收站 (\d+) 个(?:（(X\d+)，能还原）)?$/, function (m, c, a, b, d, x) {
        return 'Restored ' + c + ': ' + a + ' replaced, ' + b + ' put back, ' + d + ' moved to the recycle bin' + (x ? ' (' + x + ', restorable)' : ''); }],
      [/^定性了：(C\d+) 是安全点。回收站里在它以前进来的，现在可以彻底删了$/, 'Settled: $1 is a safe point. What entered the recycle bin before it can now be deleted for good'],
      [/^把 (C\d+) 整个挪进回收站？回收站里能还原。$/, 'Move the whole of $1 into the recycle bin? It can be restored from there.'],
      [/^挪进回收站了：(X\d+)$/, 'Moved into the recycle bin: $1'],
      [/^复活 (C\d+)「(.+)」：(\d+) 个文件换回那时的样子，(\d+) 个放回来，(\d+) 个是那之后新加的、会挪进回收站。换下来的都进回收站（一个编号），能还原。笔记、计划、日志不倒回。确定吗？$/,
        'Restore $1 “$2”: $3 files go back to how they were, $4 are put back, and $5 added since then move into the recycle bin. Everything replaced goes into the recycle bin (one number) and can be restored. Notes, plans and logs are not rolled back. Go ahead?'],
      [/^(C\d+) 只记了指纹、没复制文件，整档复活不了/, '$1 only recorded fingerprints and copied no files, so it cannot be restored as a whole'],
      // 清理
      [/^存档定性到 (.+)：在那以前进来的 (\d+) 件可以彻底删掉。$/, 'Settled up to $1: the $2 items that entered before then can be deleted for good.'],
      [/^还原了 (X\d+) → (.+?)(?:（原位置上的挪进了 (X\d+)）)?$/, function (m, x, p, s) { return 'Restored ' + x + ' → ' + p + (s ? ' (what was there moved into ' + s + ')' : ''); }],
      [/^彻底删掉了 (\d+) 件，腾出 (.+)$/, 'Deleted $1 items for good, freeing $2'],
      [/^彻底删掉 (.+)？删了就收不回来了。$/, 'Delete $1 for good? This cannot be undone.'],
      [/^原来的位置已经有 (\d+) 个同名的了（比如 (.+)）。还原的话，它们会先挪进回收站（另一个编号，能再换回来）。确定吗？$/,
        'The original location already has $1 item(s) with the same name (e.g. $2). Restoring moves them into the recycle bin first (another number, restorable). Go ahead?'],
      [/^(X\d+) (.+)$/, function (m, x, rest) { const s = one(rest); return s === rest ? m : x + ' ' + s; }],
      [/^(.+) 等 (\d+) 个（按原路径放在那个文件夹里）$/, '$1 and $2 more (kept at their original paths in that folder)'],
      // 设置：删模块
      [/^「(.+)」里有 (\d+) 个文件（(.+)）。整个文件夹挪进回收站吗？回收站里能还原。$/, '“$1” has $2 files ($3). Move the whole folder into the recycle bin? It can be restored from there.'],
      [/^删了「(.+)」：文件夹挪进了回收站，能还原$/, 'Deleted “$1”: its folder moved into the recycle bin and can be restored'],
      // 顶上黄条里的几种问题（一条条用「；」连着）
      [/S0 里列了 (S[\d-]+)，资料\/蓝图\/ 里找不到它那一份/g, 'S0 lists $1, but 资料/蓝图/ has no file for it'],
      [/(S[\d-]+) 有文件，S0 的表里没列它/g, '$1 has a file, but the S0 table does not list it'],
      [/资料\/蓝图\/ 里有 S1，没有 S0 终极目标/g, '资料/蓝图/ has S1 files but no S0 ultimate goal'],
      [/(\S+)\/\.链接\.txt：「(.+?)」找不到/g, '$1/.链接.txt: “$2” not found'],
      [/(\S+)\/\.链接\.txt：「(.+?)」指到项目外面去了，不认/g, '$1/.链接.txt: “$2” points outside the project, ignored'],
      [/(\S+) 暂时读不了：/g, '$1 cannot be read right now: '],
      // 最后：一行一行、「A · B · C」一段一段对照；没有 · 的整段也按句式试一次
      [/^[\s\S]+$/, function (s) {
        return s.split('\n').map(function (line) { return line.indexOf(' · ') >= 0 ? line.split(' · ').map(one).join(' · ') : one(line); }).join('\n');
      }]
    ]
  };
})();
