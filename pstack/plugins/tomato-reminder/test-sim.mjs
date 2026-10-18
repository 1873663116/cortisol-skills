import { apply } from './index.js';

// Minimal harness: capture listeners, fake a session with a surface.
const listeners = [];
const ctx = { on: (ev, fn) => { if (ev === 'agent/pre-step') listeners.push(fn); } };
apply(ctx, { skillPath: '/SKILL.md' });
const preStep = listeners[0];

function makeSession() {
  const log = [];
  return {
    log,
    get seq() { return log.length; },
    append(type, data, opts) {
      const ev = { type, seq: log.length, data, ...opts };
      // validate replace targets earlier seqs, like dsh-session does
      if (opts?.surfaceOp && opts.surfaceOp !== 'append') {
        const { startSeq, endSeq } = opts.surfaceOp;
        if (startSeq >= ev.seq || endSeq >= ev.seq) throw new Error('endpoints must reference earlier events');
        if (!log.find(e => e.seq === startSeq)) throw new Error('start seq not in surface');
      }
      log.push(ev);
      return ev;
    },
  };
}

// Surface projection: apply appends and replaces like the real fold.
function surface(session) {
  let nodes = [];
  for (const ev of session.log) {
    const op = ev.surfaceOp;
    if (op === 'append') nodes.push(ev.seq);
    else if (op?.op === 'replace') {
      const i = nodes.indexOf(op.startSeq);
      if (i === -1) throw new Error('replace target missing at seq ' + ev.seq);
      nodes.splice(i, 1, ev.seq);
    }
  }
  return nodes;
}

function userMsg(text) {
  return { role: 'user', content: [{ type: 'text', text }], source: { kind: 'user' } };
}

const agent = { session: makeSession() };
const next = async () => ({ kind: 'enter', messages: [] });

async function turn(text, steps = 1) {
  for (let s = 1; s <= steps; s++) {
    await preStep({ agent, messages: s === 1 ? [userMsg(text)] : [], step: s }, next);
  }
}

await turn('/tomato-mode fix this bug', 3);
console.log('after turn1: log', agent.session.log.length, 'surface', surface(agent.session).length);
await turn('now add a test', 4);
console.log('after turn2: log', agent.session.log.length, 'surface', surface(agent.session).length);
await turn('another thing', 2);
console.log('after turn3: log', agent.session.log.length, 'surface', surface(agent.session).length);
await turn('/tomato-off stop', 1);
const surf = surface(agent.session);
console.log('after off:   log', agent.session.log.length, 'surface', surf.length);
const texts = surf.map(seq => agent.session.log.find(e => e.seq === seq).data.content[0].text);
console.log('surface texts:', JSON.stringify(texts));
