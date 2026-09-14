#!/usr/bin/env node
/**
 * AI臭チェッカー（台本・原稿用）
 *
 *   node tools/ai-smell-check.mjs <原稿.md> [--source <文字起こし.txt>] [--json]
 *
 * 原稿の中から「AIが書いた文章の癖」を行番号つきで列挙します。
 * --source を渡すと、文字起こし（本人が喋った素材）に無い文も一緒に出します。
 * パターンの根拠は style/ai-smell.md を参照。
 */
import { readFileSync } from 'node:fs';

const args = process.argv.slice(2);
const file = args.find(a => !a.startsWith('--'));
const srcIdx = args.indexOf('--source');
const source = srcIdx >= 0 ? args[srcIdx + 1] : null;
const asJson = args.includes('--json');
if (!file) {
  console.error('使い方: node tools/ai-smell-check.mjs <原稿.md> [--source <文字起こし.txt>] [--json]');
  process.exit(1);
}

/* ---------- パターン定義 ---------- */
// id / 名前 / 正規表現 / 直し方
const PATTERNS = [
  ['dash', 'ダッシュ記号', /[—–]|——/, '話し言葉に無い。読点か改行に置き換える'],
  ['zenbu', '代弁→「全部◯◯します」', /全部(潰し|答え|見せ|話し|回収|解決|お渡し|渡し)/, '悩みを3つ並べて全部潰す型はテンプレ。悩みは1つに絞って、答えは本文で言う'],
  ['punch', '一語キメ台詞', /(^|[。、])\s*(知ってます|違います|逆です|断言します|はっきり言います|はっきり否定します|結論から言うと|結論、|正直に言うと|正直に言います|言い切ります)[。、]/, '短い断言で溜めを作るのはAIの定番。削るか、理由を続けて普通の文にする'],
  ['tease', '予告・引き・前置き', /(先に(言って|1つ|1個|ひとつ)|ここで(絶対|必ず)出てくる|付き合ってください|待っててください|(後|あと)で(回収|話し)|ここで回収|で(丸ごと|全部)話します|次のステップで|意外なところに|ここからが本題|ここが今日の本題|今日一番)/, '本題の予告は削って本題から入る。回収宣言もいらない'],
  ['mindread', '視聴者の心を読む', /(って(思|感じ)(った|ってる|う)(人|方)|いますよね|思いますよね|わかります。|気持ちはわかります|ごもっともです|その疑い、正しい)/, '「〜と思った人いますよね」の代弁は1本に1回まで。それ以上は説教に聞こえる'],
  ['rival', '競合・他の発信者への当てこすり', /(山ほどある|世の中の.{0,10}情報|情報商材|煽り|脅し|発信者は|発信者を|そういう動画は|ああいう動画)/, '競合批判はなし（オーナー指示）。自分のやり方だけ話す'],
  ['contrast', '「AじゃなくてBです」の対比枠', /(じゃなくて|じゃないです|ではなく)[^。]{1,25}(です|なんです|だ)[。、]/, '1章に1回まで。多いと全部が名言っぽくなって嘘くさい'],
  ['metaphor', 'キメ比喩', /(罰じゃなくて|健康診断|筋肉|心臓|ラーメン屋|カップ麺|畑|温床|お墨付き|地雷|墓標|請求書|占い|工学|鏡|発注書|教科書|辞書|物差し|階段|坂|土台|宝の山|使い捨て|投資してる)/, '比喩は本人が喋ったものだけ使う。AIが足した比喩は消す'],
  ['kango', '漢語の名詞句', /(点検項目|付加価値|勤勉さ|再現性|構造的|非対称性|遅行指標|先行指標|変数|独壇場|明文化|実務的|観測|判定基準|言語化|最適分業|サンクコスト|生存者バイアス|複利|縮小均衡|意思決定|定量|可視化|本質的|抜本的|包括的|網羅)/, '動詞の文にほどく。「点検項目に入れる」→「毎回チェックしてる」'],
  ['summary', 'まとめ・締めの決まり文句', /(まとめます。|データで全部説明できます|の正体です|の分かれ目です|これだけです。|それだけです。|それが答えです|これが答えです|やるかやらないか)/, '章ごとの「まとめます」「〜が正体です」は削る。話し言葉ではまとめない'],
  ['triple', '3連発の列挙で畳みかける', /(。[^。]{5,30}。[^。]{5,30}。[^。]{5,30}。)(?=[^。]*(今日|全部|この3つ|3つ))/, '悩み・不安の3連発は定型。1つに絞る'],
  ['nandesuyo', '「〜なんですよ」系の語尾', /(なんですよ|んですよね|んですよ)[。、]/, '密度が高いと不自然。1,000字に3回以内が目安'],
];

/* ---------- 本文の読み込み ---------- */
const raw = readFileSync(file, 'utf8');
const lines = raw.split('\n');
const isMeta = l => /^\s*(\[|［|【画面|【図解|【モジュール|#|\*\*［|\||---|\\-)/.test(l);

const hits = [];
lines.forEach((line, i) => {
  if (isMeta(line) || !line.trim()) return;
  for (const [id, name, re, fix] of PATTERNS) {
    const m = line.match(re);
    if (m) hits.push({ line: i + 1, id, name, match: m[0].slice(0, 30), text: line.trim().slice(0, 80), fix });
  }
});

/* ---------- 密度指標 ---------- */
const body = lines.filter(l => !isMeta(l)).join('\n');
const chars = body.replace(/\s/g, '').length;
const per1000 = n => (n / Math.max(chars, 1) * 1000).toFixed(1);
const count = id => hits.filter(h => h.id === id).length;

/* ---------- 同じ文の繰り返し（くどさ） ---------- */
const sentences = body.split(/[。！!？?]\s*/).map(s => s.trim()).filter(s => s.length >= 10);
const freq = new Map();
for (const s of sentences) freq.set(s, (freq.get(s) || 0) + 1);
const repeats = [...freq].filter(([, n]) => n >= 2).map(([s, n]) => ({ text: s.slice(0, 60), times: n }));

/* ---------- 文字起こし照合 ---------- */
let ungrounded = [];
if (source) {
  const src = readFileSync(source, 'utf8').replace(/\s/g, '');
  const K = 4;
  const shingles = new Set();
  for (let i = 0; i + K <= src.length; i++) shingles.add(src.slice(i, i + K));
  const norm = s => s.replace(/[\s「」『』（）()、,。.!！?？—–―・…]/g, '');
  for (const s of sentences) {
    const n = norm(s);
    if (n.length < 15) continue;
    let hit = 0, total = 0;
    for (let i = 0; i + K <= n.length; i++) { total++; if (shingles.has(n.slice(i, i + K))) hit++; }
    const ratio = total ? hit / total : 0;
    if (ratio < 0.25) ungrounded.push({ text: s.slice(0, 80), ratio: +ratio.toFixed(2) });
  }
}

/* ---------- 出力 ---------- */
const summary = {
  file, chars, hits: hits.length, per1000: per1000(hits.length),
  byPattern: Object.fromEntries(PATTERNS.map(([id, name]) => [name, count(id)])),
  nandesuyoPer1000: per1000(count('nandesuyo')),
  repeats: repeats.length,
  ungrounded: source ? ungrounded.length : null,
  ungroundedRatio: source ? (ungrounded.length / Math.max(sentences.length, 1)).toFixed(2) : null,
};

if (asJson) {
  console.log(JSON.stringify({ summary, hits, repeats, ungrounded }, null, 2));
  process.exit(0);
}

console.log(`# AI臭チェック: ${file}`);
console.log(`本文 ${chars.toLocaleString()} 字 / 検出 ${hits.length} 件（1,000字あたり ${summary.per1000} 件）`);
console.log(`「なんですよ」系の語尾: 1,000字あたり ${summary.nandesuyoPer1000} 回（目安 3.0 以下）`);
console.log('');
console.log('## パターン別');
for (const [id, name, , fix] of PATTERNS) {
  const n = count(id);
  if (n) console.log(`- ${name}: ${n} 件 … ${fix}`);
}
if (repeats.length) {
  console.log('');
  console.log('## 同じ文の繰り返し（くどい）');
  for (const r of repeats) console.log(`- ×${r.times} 「${r.text}」`);
}
if (source) {
  console.log('');
  console.log(`## 文字起こしに無い文（${ungrounded.length} 文 / 全 ${sentences.length} 文）`);
  console.log('AIが足した可能性が高い文。本人が喋っていない主張・比喩・キメ台詞はここに出ます。');
  for (const u of ungrounded.slice(0, 60)) console.log(`- ${u.text}`);
  if (ungrounded.length > 60) console.log(`  …ほか ${ungrounded.length - 60} 文`);
}
console.log('');
console.log('## 該当箇所');
for (const h of hits) console.log(`L${h.line} [${h.name}] ${h.text}`);
