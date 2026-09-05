# -*- coding: utf-8 -*-
"""Extract stock mentions from zsxq topics."""
import json, re, sys, os
from collections import defaultdict

DATA_DIR = '/tmp/zsxq_fetch'
STOCK_A = json.load(open(f'{DATA_DIR}/stock_a.json'))

# -- stock name dictionary ------------------------------------------------
# filter out names that are too generic / short or likely to cause noise
BAD_NAMES = set()
GENERIC = {'万科', '平安', '光大', '华夏', '中国', '东方', '北方', '南方', '西部',
           '中体', '国新', '川能', '华为', '大族', '中航', '机器人'}
# names of exactly 2 chars are risky; drop those in GENERIC only (keep others via context check)
name2code = {}
for s in STOCK_A:
    n = s['name'].strip()
    if not n or n in ('N', 'C', 'G'):
        continue
    n = n.replace(' ', '')
    if n in GENERIC:
        BAD_NAMES.add(n)
        continue
    name2code.setdefault(n, s['code'])

# add common HK/US names manually (code marked as market tag)
EXTRA = {
    '腾讯控股': 'HK.00700', '腾讯': 'HK.00700', '阿里巴巴': 'HK.09988', '美团': 'HK.03690',
    '小米集团': 'HK.01810', '小米': 'HK.01810', '网易': 'HK.09999', '京东集团': 'HK.09618',
    '快手': 'HK.01024', '中芯国际': 'SH.688981', '华虹': 'HK.01347', '华虹半导体': 'HK.01347',
    '理想汽车': 'HK.02015', '小鹏汽车': 'HK.09868', '蔚来': 'NYSE.NIO',
    '港交所': 'HK.00388', '友邦保险': 'HK.01299', '中国移动': 'SH.600941',
    '中国海洋石油': 'SH.600938', '中海油': 'SH.600938', '中国重汽': 'SZ.000951',
    '比亚迪': 'SZ.002594', '百度': 'HK.09888', '金山软件': 'HK.03888',
    'AMD': 'NASDAQ.AMD', 'ARM': 'NASDAQ.ARM', 'NVDA': 'NASDAQ.NVDA', '英伟达': 'NASDAQ.NVDA',
    'TSLA': 'NASDAQ.TSLA', '特斯拉': 'NASDAQ.TSLA', 'AAPL': 'NASDAQ.AAPL', '苹果': 'NASDAQ.AAPL',
    'MSFT': 'NASDAQ.MSFT', '微软': 'NASDAQ.MSFT', 'GOOGL': 'NASDAQ.GOOGL', '谷歌': 'NASDAQ.GOOGL',
    'META': 'NASDAQ.META', 'AMZN': 'NASDAQ.AMZN', '亚马逊': 'NASDAQ.AMZN',
    'INTC': 'NASDAQ.INTC', '英特尔': 'NASDAQ.INTC', 'QCOM': 'NASDAQ.QCOM', '高通': 'NASDAQ.QCOM',
    'MU': 'NASDAQ.MU', '美光': 'NASDAQ.MU', '台积电': 'NYSE.TSM', 'ASML': 'NASDAQ.ASML',
    '甲骨文': 'NYSE.ORCL', 'ORCL': 'NYSE.ORCL', '博通': 'NASDAQ.AVGO', 'AVGO': 'NASDAQ.AVGO',
    '梅西百货': 'NYSE.M', '诺华': 'NYSE.NVS', '礼来': 'NYSE.LLY', '安进': 'NASDAQ.AMGN',
    '吉利德': 'NASDAQ.GILD', '辉瑞': 'NYSE.PFE', '默沙东': 'NYSE.MRK',
}
for n, c in EXTRA.items():
    name2code.setdefault(n, c)

names_sorted = sorted(name2code.keys(), key=len, reverse=True)
# regex: longest-first alternation, avoid matching when followed/preceded by more name chars
NAME_RE = re.compile('(' + '|'.join(re.escape(n) for n in names_sorted) + ')')

# -- broker/industry tag --------------------------------------------------
BROKERS = ['中信建投', '国泰海通', '中信', '中金', '中泰', '天风', '广发', '长江', '国信', '华福', '华泰',
           '国盛', '民生', '招商', '兴业', '兴证', '光大', '申万宏源', '申万', '海通', '东方财富', '东方',
           '东吴', '东兴', '平安', '浙商', '开源', '华西', '华创', '国金', '银河', '太平洋',
           '粤开', '财通', '德邦', '华安', '东北', '山西', '首创', '中银', '交银', '信达',
           '方正', '国海', '西部', '高盛', '瑞银', '摩根', '大摩', '小摩', '花旗', '野村',
           '美银', '巴克莱', '里昂', '大和', '群益', '中邮', '国联', '华鑫', '甬兴', '国投',
           '银河国际', '建投', '工银', '农银', '中航', '招商证券', 'glms', '华源', '财信',
           '东亚前海', '湘财', '东兴证券', '国海证券', '东方证券', '安信']
TAG_RE = re.compile(r'【([^】]{2,20})】')

def parse_tag(text):
    m = TAG_RE.search(text)
    if not m:
        return None, None
    tag = m.group(1)
    for b in sorted(BROKERS, key=len, reverse=True):
        if tag.startswith(b):
            return b, tag[len(b):].strip(' ：:-丨|')
    return None, tag

INDUSTRY_MAP = [
    ('半导体', '半导体'), ('芯片', '半导体'), ('电子', '电子'), ('元器件', '电子'),
    ('电新', '电力设备与新能源'), ('电力设备', '电力设备与新能源'), ('新能源', '电力设备与新能源'),
    ('锂电', '电力设备与新能源'), ('光伏', '电力设备与新能源'), ('风电', '电力设备与新能源'),
    ('计算机', '计算机'), ('AI', '计算机'), ('算力', '计算机'), ('通信', '通信'), ('液冷', '通信'),
    ('机械', '机械'), ('军工', '国防军工'), ('国防', '国防军工'),
    ('汽车', '汽车'), ('交运', '交通运输'), ('油运', '交通运输'), ('物流', '交通运输'),
    ('医药', '医药生物'), ('生物', '医药生物'), ('创新药', '医药生物'), ('医疗', '医药生物'),
    ('中药', '医药生物'), ('cxo', '医药生物'), ('CXO', '医药生物'),
    ('有色', '有色金属'), ('钢铁', '钢铁'), ('煤炭', '煤炭'), ('石油', '石油石化'),
    ('化工', '基础化工'), ('磷', '基础化工'), ('氟', '基础化工'), ('材料', '基础化工'),
    ('食品', '食品饮料'), ('饮料', '食品饮料'), ('白酒', '食品饮料'), ('农业', '农林牧渔'),
    ('农牧', '农林牧渔'), ('银行', '银行'), ('非银', '非银金融'), ('证券', '非银金融'),
    ('保险', '非银金融'), ('地产', '房地产'), ('房地产', '房地产'), ('建筑', '建筑装饰'),
    ('建材', '建筑材料'), ('公用', '公用事业'), ('环保', '环保'), ('互联网', '互联网'),
    ('海外', '海外TMT'), ('TMT', '海外TMT'), ('金股', '金股组合'),
    ('中小盘', '策略/宏观'), ('中小市值', '策略/宏观'),
    ('传媒', '传媒'), ('游戏', '传媒'), ('纺服', '纺织服装'), ('轻工', '轻工制造'),
    ('家电', '家用电器'), ('策略', '策略/宏观'), ('宏观', '策略/宏观'), ('固收', '策略/宏观'),
    ('金工', '策略/宏观'), ('小熊团队', ''), ('zx', ''), ('HF', ''), ('点评', ''), ('数据', ''), ('段子', ''), ('跟踪', ''),
]

def industry_of(tag):
    if not tag:
        return ''
    for k, v in INDUSTRY_MAP:
        if k in tag:
            return v
    return tag

# -- sentence context -----------------------------------------------------
SENT_SPLIT = re.compile(r'[。！？；\n]')
def contexts_for(text, name, max_ctx=3, ctx_len=100):
    out = []
    for sent in SENT_SPLIT.split(text):
        if name in sent and len(out) < max_ctx:
            s = sent.strip()
            if len(s) > ctx_len:
                i = s.find(name)
                l, r = max(0, i - 40), min(len(s), i + len(name) + 60)
                s = ('…' if l > 0 else '') + s[l:r] + ('…' if r < len(s) else '')
            if s and s not in out:
                out.append(s)
    return out

STOP_CTX = set()
REC_RE = re.compile(r'金股|重点推荐|首推|强call|强Call|建议关注|持续推荐|继续推荐|推荐关注|个股推荐|重点关注|主推|再推|继续大推|坚定推荐|首予|上调至|买入评级|增持评级')
def analyze(topics):
    mentions = defaultdict(lambda: {
        'count': 0, 'codes': set(), 'days': set(), 'brokers': set(), 'industries': set(),
        'digested': 0, 'likes': 0, 'topics': [], 'contexts': [], 'last_time': '', 'first_time': '9999',
        'rec_count': 0})
    for t in topics:
        body = (t['title'] or '') + ' ' + (t['text'] or '')
        broker, ind_tag = parse_tag(t['title'] or t['text'] or '')
        ind = industry_of(ind_tag)
        is_rec = bool(REC_RE.search((t['title'] or '') + ' ' + (t['text'] or '')[:300]))
        found = set(m.group(0) for m in NAME_RE.finditer(body) if m.group(0) not in BAD_NAMES)
        # longest-match filter: drop a name if it is a substring of another found name (e.g. 平安 in 中国平安)
        found = {n for n in found if not any(n != o and n in o for o in found)}
        # skip the topic's own broker name appearing as a stock (e.g. 国泰海通 in 【国泰海通海外科技】)
        if broker:
            found = {n for n in found if not (n == broker or broker in n or n in broker)}
        day = t['time'][:10]
        for n in found:
            d = mentions[n]
            d['count'] += 1
            d['codes'].add(name2code[n])
            d['days'].add(day)
            if broker:
                d['brokers'].add(broker)
            if ind:
                d['industries'].add(ind)
            d['digested'] += 1 if t['digested'] else 0
            d['rec_count'] += 1 if is_rec else 0
            d['likes'] = max(d['likes'], t['likes'] or 0)
            d['last_time'] = max(d['last_time'], t['time'])
            d['first_time'] = min(d['first_time'], t['time'])
            if len(d['topics']) < 40:
                d['topics'].append(t['id'])
            if len(d['contexts']) < 6:
                for c in contexts_for(t['text'] or t['title'] or '', n):
                    if len(d['contexts']) >= 6:
                        break
                    d['contexts'].append({'date': day, 'ctx': c, 'topic_id': t['id'], 'digested': t['digested']})
    return mentions

if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else f'{DATA_DIR}/all_topics.json'
    topics = json.load(open(src))
    mentions = analyze(topics)
    rows = []
    for name, d in mentions.items():
        rows.append({
            'name': name, 'code': sorted(d['codes'])[0], 'count': d['count'],
            'days': len(d['days']), 'brokers': sorted(d['brokers']), 'industries': sorted(d['industries']),
            'digested': d['digested'], 'likes': d['likes'], 'rec_count': d['rec_count'],
            'last_time': d['last_time'], 'first_time': d['first_time'],
            'topics': d['topics'], 'contexts': d['contexts']})
    rows.sort(key=lambda r: (-r['count'], -r['days']))
    json.dump(rows, open(f'{DATA_DIR}/mentions.json', 'w'), ensure_ascii=False, indent=1)
    print(f'topics={len(topics)} distinct names={len(rows)}')
    for r in rows[:30]:
        print(f"{r['name']:<8} {r['code']:<12} n={r['count']:<3} days={r['days']:<3} brokers={len(r['brokers'])} dig={r['digested']} last={r['last_time'][:10]} ind={','.join(r['industries'][:2])}")
