import json,re,collections,sys
OWN={"UCYASX2PAaV_7aEX6EPpP8Dg":"嫁子朗読","UCGbs0tw5UQpzL26nmQ20Bzg":"嫁子漫画","UCJdP64Vdr3lFZt2wi4WJLjA":"自社(大城)"}
own={v['id']:v for v in json.load(open('own_videos.json'))}
hits=json.load(open('hits.json'))
def days(s):
    if not s: return None
    m=re.search(r'(\d+)\s*(年|か月|週間|日|時間|分)前',s)
    if not m: return None
    return int(m.group(1))*{'年':365,'か月':30,'週間':7,'日':1,'時間':0,'分':0}[m.group(2)]
rows=[];older=[]
for oid,hs in hits.items():
    for h in hs:
        if h['channelId'] in OWN: continue
        do=days(own[oid]['pub']); dc=days(h['pub'])
        if do is not None and dc is not None and dc>do*1.15+30:
            older.append(dict(orig=oid,orig_title=own[oid]['title'],orig_pub=own[oid]['pub'],**h)); continue
        t=h['title'] or ''
        fmt='LINE形式' if 'LINE' in t.upper() and '【LINE' in t.replace(' ','') or t.startswith('【LINE') else ('漫画形式' if '【漫画' in t or '【マンガ' in t or '【アニメ' in t else ('2ch形式' if '2ch' in t.lower() or 'ゆっくり' in t else '朗読/同形式'))
        rows.append(dict(orig=oid,orig_title=own[oid]['title'],orig_pub=own[oid]['pub'],**h,fmt=fmt))
print('candidate rows',len(rows),'from',len([k for k,v in hits.items() if any(h['channelId'] not in OWN for h in v)]),'originals')
bych=collections.defaultdict(list)
for r in rows: bych[(r['channel'],r['channelId'])].append(r)
def score(r): return (r['fmt']!='朗読/同形式', -r['ratio'])
lines=[]
lines.append('# 嫁子のスカッと朗読劇場【スカッとする話】 転載チャンネル 全件調査')
lines.append('')
lines.append('作成日：2026-09-15')
lines.append('')
lines.append('## 調べ方')
lines.append('')
lines.append(f'- 嫁子チャンネルの全動画 {len(own):,} 本のタイトルをYouTube検索にかけ、タイトルの一致率72%以上、または先頭20文字が一致する別チャンネルの動画を抽出した。')
lines.append('- 検索結果に出る動画は現存しているものだけなので、停止・削除済みは自動的に除外されている。')
lines.append('- 自社チャンネル（嫁子朗読、嫁子のスカッと漫画）は除外。')
lines.append('- 「形式」列：朗読/同形式＝タイトルをそのまま使った再投稿（音声コピーの可能性が高い）。LINE形式・漫画形式・2ch形式＝別形式に作り替えたもの（企画・台本の流用）。')
lines.append('- タイトルをAIで言い換えた転載は一致率が下がるため、この方法では拾い切れていない。')
lines.append('')
lines.append('## 集計')
lines.append('')
fc=collections.Counter(r['fmt'] for r in rows)
lines.append(f'- 転載疑い動画：{len(rows)} 本（内訳：' + '、'.join(f'{k} {v}本' for k,v in fc.most_common()) + '）')
lines.append(f'- 転載しているチャンネル：{len(bych)} チャンネル')
lines.append(f'- 転載された元動画：{len(set(r["orig"] for r in rows))} 本')
lines.append(f'- タイトルが一言一句同じもの（一致率100%）：{sum(1 for r in rows if r["ratio"]>=1.0)} 本')
lines.append(f'- 嫁子の動画より先に公開されていたため除外（嫁子側が参考にした元ネタの可能性）：{len(older)} 本（末尾に一覧）')
lines.append('')
lines.append('## A. チャンネル別（本数順）')
lines.append('')
lines.append('| # | チャンネル名 | チャンネルURL | 本数 | 主な形式 | 直近の投稿 |')
lines.append('|---|---|---|---|---|---|')
for i,((ch,cid),rs) in enumerate(sorted(bych.items(),key=lambda kv:-len(kv[1])),1):
    f=collections.Counter(r['fmt'] for r in rs).most_common(1)[0][0]
    pubs=[r['pub'] for r in rs if r['pub']]
    url=f'https://www.youtube.com/channel/{cid}' if cid else '（ID取得不可。動画URLから辿る）'
    lines.append(f'| {i} | {ch} | {url} | {len(rs)} | {f} | {pubs[0] if pubs else ""} |')
lines.append('')
lines.append('## B. 動画別（チャンネルごとにまとめ）')
lines.append('')
for (ch,cid),rs in sorted(bych.items(),key=lambda kv:-len(kv[1])):
    lines.append(f'### {ch}（{len(rs)}本） ' + (f'https://www.youtube.com/channel/{cid}' if cid else ''))
    lines.append('')
    lines.append('| 形式 | 一致率 | 転載動画 | 投稿 | 再生 | 嫁子の元動画 | 元タイトル |')
    lines.append('|---|---|---|---|---|---|---|')
    for r in sorted(rs,key=score):
        lines.append(f"| {r['fmt']} | {int(r['ratio']*100)}% | https://youtu.be/{r['id']} | {r['pub'] or ''} | {r['views'] or ''} | https://youtu.be/{r['orig']} | {r['orig_title'][:60]} |")
    lines.append('')
lines.append('## C. 除外：嫁子の動画より先に公開されていたもの')
lines.append('')
lines.append('| チャンネル | 相手の投稿 | 嫁子の投稿 | 相手の動画 | 嫁子の動画 | タイトル |')
lines.append('|---|---|---|---|---|---|')
for r in older:
    lines.append(f"| {r['channel']} | {r['pub']} | {r['orig_pub']} | https://youtu.be/{r['id']} | https://youtu.be/{r['orig']} | {(r['title'] or '')[:60]} |")
lines.append('')
open(sys.argv[1] if len(sys.argv)>1 else 'report.md','w').write('\n'.join(lines)+'\n')
print('written')
