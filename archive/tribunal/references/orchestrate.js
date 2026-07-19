// Claude Code Workflow 路由骨架。主 agent 读它、填入本次的提示词、按需裁剪编排,
// 再用 Workflow({ script, args }) 现场内联运行。机械部分(fan-out / 种子混入 / 召回 / 盲审隔离 / schema)照搬即可。
export const meta = {
  name: 'tribunal',
  description: '三段式对抗审查的编排骨架:审计→辩护→盲审裁决',
  phases: [{ title: '审计' }, { title: '辩护' }, { title: '裁决' }],
}

// args 可能以对象或 JSON 字符串到达(Workflow 的 args 形参无类型声明,部分 harness 原样传字符串)。
// 两种都接住,否则解构字符串会得到全 undefined、误报"缺少必需的 args"。
let _args = args || {}
if (typeof _args === 'string') {
  try { _args = JSON.parse(_args) } catch (e) { return { error: 'args 是字符串但非合法 JSON: ' + e.message } }
}
const { target, contextMap, lenses, defensePrompt, judgePrompt, seededDefects } = _args

const missing = []
if (!target) missing.push('target')
if (!Array.isArray(lenses) || !lenses.length) missing.push('lenses(审计提示词数组)')
if (!defensePrompt) missing.push('defensePrompt')
if (!judgePrompt) missing.push('judgePrompt')
if (missing.length) {
  return { error: `缺少必需的 args: ${missing.join('、')}。提示词由主 agent 注入,不在脚本里固化。` }
}

const targetIsPath = typeof target === 'string' && target.startsWith('/') && !target.includes('\n')
const doc = targetIsPath ? `<document_path>\n${target}\n</document_path>` : `<document>\n${target}\n</document>`
const targetReadInstruction = targetIsPath
  ? '\n\n被审对象以文件路径提供。先 Read 该文件全文，再审计文件内容；不要把路径字符串当正文。'
  : ''
const ctx = contextMap ? `\n\n可核实的上下文(顺着它去 Read / grep 核实文档对代码现状的断言):\n${contextMap}` : ''
const severityRank = { high: 0, medium: 1, low: 2 }
const bySeverity = (a, b) => (severityRank[a.severity] ?? 9) - (severityRank[b.severity] ?? 9)

// schema 是机械的输出契约,不是提示词:类别放开为自由文本(由注入的提示词规定),
// 只对 severity / verdict 这类要参与机械过滤和排序的字段约束枚举。
const ISSUES_SCHEMA = {
  type: 'object',
  required: ['issues'],
  properties: {
    issues: {
      type: 'array',
      items: {
        type: 'object',
        required: ['title', 'severity', 'evidence', 'rationale'],
        properties: {
          issueId: { type: 'string', description: '稳定问题 ID；缺失时由骨架补齐' },
          title: { type: 'string', description: '一句话概括这个问题' },
          category: { type: 'string', description: '由审计提示词规定的类别' },
          severity: { type: 'string', enum: ['high', 'medium', 'low'] },
          evidence: { type: 'string', description: '指向文档某句/某假设,或 Read/grep 核实到的事实' },
          rationale: { type: 'string' },
        },
      },
    },
  },
}

// 去重阶段的输出契约:把相同原因意见合并后输出
const DEDUP_SCHEMA = {
  type: 'object',
  required: ['issues'],
  properties: {
    issues: {
      type: 'array',
      items: {
        type: 'object',
        required: ['issueId', 'title', 'severity', 'evidence', 'rationale', 'mergedCount'],
        properties: {
          issueId: { type: 'string' },
          sourceIssueIds: { type: 'array', items: { type: 'string' } },
          title: { type: 'string' },
          category: { type: 'string' },
          severity: { type: 'string', enum: ['high', 'medium', 'low'] },
          evidence: { type: 'string' },
          rationale: { type: 'string' },
          mergedCount: { type: 'number', description: '本条合并了几条原始意见' },
        },
      },
    },
  },
}

const DEFENSE_SCHEMA = {
  type: 'object',
  required: ['issueId', 'stance', 'argument'],
  properties: {
    issueId: { type: 'string' },
    stance: { type: 'string', enum: ['驳回', '部分成立', '成立'] },
    argument: { type: 'string' },
  },
}

const RULING_SCHEMA = {
  type: 'object',
  required: ['rulings'],
  properties: {
    rulings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['issueId', 'title', 'verdict', 'severity', 'reasoning', 'action'],
        properties: {
          issueId: { type: 'string' },
          title: { type: 'string', description: '保留原意见的标题' },
          category: { type: 'string' },
          verdict: { type: 'string', enum: ['confirmed', 'rejected', 'uncertain'] },
          severity: { type: 'string', enum: ['high', 'medium', 'low'] },
          reasoning: { type: 'string' },
          action: { type: 'string', description: 'confirmed 时给出下一步处理建议；其他裁决说明无需行动或待用户拍板' },
        },
      },
    },
  },
}

// 一、审计:注入的每段 lens 提示词
const found = await parallel(
  lenses.map((lensPrompt, i) => () =>
    agent(`${lensPrompt}${targetReadInstruction}\n\n${doc}${ctx}`, { schema: ISSUES_SCHEMA, phase: '挑刺', label: `challenge:${i + 1}` })
      .then((result) => ({ lensIndex: i, result }))
  )
)
const allIssues = found.filter(Boolean).flatMap(({ lensIndex, result }) =>
  ((result && result.issues) || []).map((issue, j) => ({
    ...issue,
    issueId: issue.issueId || `challenge-${lensIndex + 1}-${String(j + 1).padStart(3, '0')}`,
  }))
)

// 去重:用一个 agent 按相同原因合并。
// 不想要可整段删除,并把下方 issuesForDefense 换回 allIssues。
let issuesForDefense = allIssues
if (allIssues.length) {
  const dedupRes = await agent(
    `下面是多名审查者对同一份文档独立提出的意见,彼此看不到对方,故同一根因常被重复提出。把指向同一根因的合并为一条:保留最强证据,severity 取簇内最高,rationale 综合各条要点,mergedCount 记该簇合并了几条。输出必须保留稳定 issueId, 并用 sourceIssueIds 记录合并来源。不同根因不要合并——宁可不合并也不要错并。只输出去重后的意见数组。\n\n原始意见(${allIssues.length} 条):\n${JSON.stringify(allIssues, null, 2)}`,
    { schema: DEDUP_SCHEMA, phase: '挑刺', label: 'dedup' }
  )
  const distinctIssues = ((dedupRes && dedupRes.issues) || []).filter(Boolean).map((issue, j) => {
    const issueId = issue.issueId || `dedup-${String(j + 1).padStart(3, '0')}`
    return {
      ...issue,
      issueId,
      sourceIssueIds: Array.isArray(issue.sourceIssueIds) ? issue.sourceIssueIds : [issueId],
    }
  })
  issuesForDefense = distinctIssues.length ? distinctIssues : allIssues
}

// 二、辩护:注入的 defensePrompt
let reviewed = []
if (issuesForDefense.length) {
  reviewed = (
    await parallel(
      issuesForDefense.map((issue) => () =>
        agent(`${defensePrompt}${targetReadInstruction}\n\n待审视的意见:\n${JSON.stringify(issue, null, 2)}\n\n${doc}${ctx}`, {
          schema: DEFENSE_SCHEMA,
          phase: '辩护',
          label: `defend:${(issue.title || '').slice(0, 18)}`,
        }).then((defense) => ({ issue, defense: { ...defense, issueId: defense.issueId || issue.issueId } }))
      )
    )
  ).filter(Boolean)
}

// 三、裁决:盲审
const seeded = (seededDefects || []).map((s, i) => {
  const issueId = s.issueId || `seed-${String(i + 1).padStart(3, '0')}`
  return {
    issue: {
      issueId,
      title: s.title,
      category: s.category || '',
      severity: s.severity || 'high',
      evidence: s.evidence || '(种子缺陷)',
      rationale: s.rationale || '',
    },
    defense: { issueId, stance: '驳回', argument: s.decoyDefense || '这条意见恐怕站不住。' },
  }
})

const mixed = reviewed.map((r) => ({ issue: r.issue, defense: r.defense }))
seeded.forEach((s, i) => {
  const step = reviewed.length ? Math.ceil((reviewed.length + 1) / (seeded.length + 1)) : 1
  const pos = Math.min((i + 1) * step, mixed.length)
  mixed.splice(pos, 0, { issue: s.issue, defense: s.defense })
})

if (!mixed.length) {
  return {
    confirmed: [],
    rejected: [],
    uncertain: [],
    rulings: [],
    stats: { rawIssues: allIssues.length, afterDedup: issuesForDefense.length, afterDefense: reviewed.length, seeded: seeded.length },
    seededRecall: null,
  }
}

const ruling = await agent(
  `${judgePrompt}${targetReadInstruction}\n\n${doc}${ctx}\n\n意见与回应:\n${JSON.stringify(mixed, null, 2)}`,
  { schema: RULING_SCHEMA, phase: '裁决', label: 'judge' }
)
const rulings = ruling.rulings || []

const confirmedIssueIds = new Set(rulings.filter((r) => r.verdict === 'confirmed').map((r) => r.issueId))
const seededIssueIds = seeded.map((s) => s.issue.issueId)
const seededRecalled = seededIssueIds.filter((id) => confirmedIssueIds.has(id))
const seededRecall = seededIssueIds.length ? `${seededRecalled.length}/${seededIssueIds.length}` : null

return {
  confirmed: rulings.filter((r) => r.verdict === 'confirmed').sort(bySeverity),
  rejected: rulings.filter((r) => r.verdict === 'rejected'),
  uncertain: rulings.filter((r) => r.verdict === 'uncertain'),
  rulings,
  stats: { rawIssues: allIssues.length, afterDedup: issuesForDefense.length, afterDefense: reviewed.length, seeded: seeded.length },
  seededRecall,
}
