"""真MCP项目/身份绑定、授权配置和计划-独立验收集成。"""
import json
import sys
import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Implementation
from conftest import BACKEND
import agents, claims, construction_plans as cp, deliveries, store


async def call(proj, who, calls, auth='', runner=False):
    out=[]
    params=StdioServerParameters(command=sys.executable,args=[str(BACKEND/'mcp_server.py'),'--project',str(proj.root),'--agent',who]+(['--configuration-authorization',auth] if auth else [])+(['--runner-control'] if runner else []))
    async with stdio_client(params) as (r,w):
        async with ClientSession(r,w,client_info=Implementation(name='wrong-client',version='1')) as session:
            await session.initialize()
            for name,args in calls:
                result=await session.call_tool(name,args)
                out.append((bool(result.isError), '\n'.join(c.text for c in result.content if c.type=='text')))
    return out


def test_bound_identity_and_authorized_employee_changes(proj):
    c=store.connect(proj.db_path)
    agents.register(c,proj,'boss','Codex')
    agents.register(c,proj,'worker','Codex')
    f=proj.root/'治理/计划/S0 总体/P1 · 2026-10-02 · 授权.md'
    f.parent.mkdir(parents=True)
    f.write_text('> 授权：作者本次明确批准岗位\n> 授权操作者：boss\n> 授权对象：G2\n',encoding='utf-8')
    results=anyio.run(call,proj,'boss',[
        ('register_agent',{'name':'worker'}),
        ('configure_agent',{'key':'G2','fields':{'crafts':['程序'],'core':'不能'},'authorization_path':f.relative_to(proj.root).as_posix()}),
        ('configure_agent',{'key':'G1','fields':{'roles':['验收']},'authorization_path':f.relative_to(proj.root).as_posix()}),
        ('report_employee_runtime',{'state':{'status':'waiting','rounds':2}}),
        ('my_profile',{'agent':'worker'}),
    ],f.relative_to(proj.root).as_posix(),True)
    assert '绑定的员工' in results[0][1]
    assert not results[1][0] and agents.get(proj,'G2')['crafts']==['程序']
    assert results[2][0] and '不包括' in results[2][1]
    assert json.loads(results[3][1])['rounds']==2
    assert results[4][0] and '身份' in results[4][1]
    state=proj.root/'自动化/运行状态/G1.json'
    assert state.is_file() and not (proj.root/'自动化/运行状态/G2.json').exists()
    forged=anyio.run(call,proj,'boss',[
        ('configure_agent',{'key':'G2','fields':{'core':True},'authorization_path':f.relative_to(proj.root).as_posix()}),
        ('report_employee_runtime',{'state':{'rounds':0,'status':'ready'}}),
    ])
    assert all(error for error,text in forged)
    assert not (proj.root/'笔记/总览.md').exists()
    c.close()


def test_managed_delivery_requires_plan_and_independent_acceptance(proj, monkeypatch):
    f=proj.root/'治理/目标/S1-1 样板.md'
    f.parent.mkdir(parents=True)
    f.write_text('# S1-1 样板\n\n**样板**\n\n| | 做什么 | 怎么验 | 状态 |\n|---|---|---|---|\n| S2-1 | 〔程序〕写文件 | 文件内容是结果 | 没做 |\n',encoding='utf-8')
    c=store.connect(proj.db_path)
    for name in ('worker','reviewer'):
        agents.register(c,proj,name,'Codex')
    agents.update(c,proj,'G1',{'plan_required':True},by='人')
    agents.update(c,proj,'G2',{'roles':['审核','验收'],'program':'Codex（review-a）'},by='人')
    out=anyio.run(call,proj,'worker',[
        ('deliver',{'goal':'S1-1','sub':'S2-1','did':'结果','checks':[{'name':'文件','ok':True}]}),
        ('submit_execution_plan',{'goal':'S1-1','sub':'S2-1','text':'写result.txt并检查内容','files':['result.txt']}),
    ])
    assert '尚未通过审核' in out[0][1]
    plan=json.loads(out[1][1])
    assert all(plan[k] for k in ('employee','by','model','updated','what','how','files'))
    assert plan['missing_rules'] and plan['rules_source']=='项目现存适用戒律记录'
    self_review=anyio.run(call,proj,'worker',[('review_execution_plan',{'code':plan['code'],'ok':True,'why':'自己','revision':plan['revision']})])
    assert self_review[0][0]
    waiting=anyio.run(call,proj,'worker',[('deliver',{'goal':'S1-1','sub':'S2-1','did':'未审','checks':[{'name':'文件','ok':True}],'files':['result.txt']})])
    assert '尚未通过审核' in waiting[0][1]
    rejected=anyio.run(call,proj,'reviewer',[('review_execution_plan',{'code':plan['code'],'ok':False,'why':'补验收说明','revision':plan['revision']})])
    rejected=json.loads(rejected[0][1])
    assert rejected['reviewer_model']=='review-a' and rejected['history'][-1]['reviewer_model']=='review-a'
    retry=anyio.run(call,proj,'worker',[
        ('deliver',{'goal':'S1-1','sub':'S2-1','did':'打回未修','checks':[{'name':'文件','ok':True}],'files':['result.txt']}),
        ('submit_execution_plan',{'goal':'S1-1','sub':'S2-1','text':'补检查','files':['result.txt'],'revision':plan['revision']}),
        ('submit_execution_plan',{'goal':'S1-1','sub':'S2-1','text':'写result.txt并读取检查内容等于结果','files':['result.txt'],'revision':rejected['revision']}),
    ])
    assert '尚未通过审核' in retry[0][1] and retry[1][0] and '版本' in retry[1][1]
    plan=json.loads(retry[2][1])
    assert plan['code']==rejected['code'] and plan['version']==2
    agents.update(c,proj,'G2',{'program':'Codex（review-b）'},by='人')
    approved=anyio.run(call,proj,'reviewer',[('review_execution_plan',{'code':plan['code'],'ok':True,'why':'范围和检查明确','revision':plan['revision']})])
    approved=json.loads(approved[0][1])
    assert approved['state']=='通过' and approved['reviewer_model']=='review-b'
    assert '模型：review-b' in (proj.root/approved['formal_path']).read_text(encoding='utf-8')
    assert [h['reviewer_model'] for h in approved['history'] if h['act'] in ('通过','打回')]==['review-a','review-b']
    outside=anyio.run(call,proj,'worker',[('deliver',{'goal':'S1-1','sub':'S2-1','did':'越范围','checks':[{'name':'文件','ok':True}],'files':['outside.txt']})])
    assert '不在审核通过的修改范围' in outside[0][1]
    (proj.root/'result.txt').write_text('结果',encoding='utf-8')
    monkeypatch.setattr(deliveries,'_book',lambda *a,**k:None)
    claims.claim(c,'S1-1','S2-1','agent:worker',['S1-1 S2-1'])
    j=deliveries.deliver(c,proj,goal='S1-1',sub='S2-1',did='结果',checks=[{'name':'文件','ok':True}],files=['result.txt'],by='agent:worker')
    assert j['state']=='等验收' and j['plan']
    import pytest
    with pytest.raises(store.Refused,match='重复交付'):
        deliveries.deliver(c,proj,goal='S1-1',sub='S2-1',did='结果',checks=[{'name':'文件','ok':True}],files=['result.txt'],by='agent:worker')
    deliveries.reject(c,proj,j['code'],'补第二检查',by='人')
    agents.update(c,proj,'G2',{'paused':True},by='人')
    j2=deliveries.deliver(c,proj,goal='S1-1',sub='S2-1',did='结果',checks=[{'name':'文件','ok':True}],files=['result.txt'],by='agent:worker')
    assert j2['state']=='待你验收'
    c.close()
