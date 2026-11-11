import datetime
import json
import math
import os
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="簿記1級 4象限マトリックス & SRS学習OS",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================================================================
# 0. デザイン・スタイル定義
# ==============================================================================
st.markdown(
    """
<style>
    .block-container { 
        padding-top: 4.5rem !important; 
        padding-bottom: 2rem; 
    }
    .matrix-box {
        background: #1e293b;
        border-radius: 8px;
        padding: 12px;
        min-height: 220px;
        border: 1px solid #334155;
        margin-bottom: 12px;
    }
    .matrix-header {
        font-weight: bold;
        font-size: 14px;
        margin-bottom: 8px;
        padding-bottom: 4px;
        border-bottom: 1px solid #475569;
    }
    .badge-red { color: #f87171; font-weight: bold; margin-bottom: 6px; display: block; font-size: 13.5px; line-height: 1.4; }
    .badge-blue { color: #60a5fa; font-weight: bold; margin-bottom: 6px; display: block; font-size: 13.5px; line-height: 1.4; }
    .badge-purple { color: #c084fc; font-weight: bold; margin-bottom: 6px; display: block; font-size: 13.5px; line-height: 1.4; }
    .badge-green { color: #4ade80; font-weight: bold; margin-bottom: 6px; display: block; font-size: 13.5px; line-height: 1.4; }
    .step-tag { font-size: 11px; background: #334155; color: #cbd5e1; padding: 2px 6px; border-radius: 4px; margin-left: 4px; }
    .weight-tag { font-size: 10.5px; background: #0369a1; color: #e0f2fe; padding: 1px 5px; border-radius: 3px; margin-left: 4px; }
    .rec-tag { font-size: 11px; background: #f59e0b; color: #111827; font-weight: bold; padding: 2px 7px; border-radius: 4px; margin-left: 6px; }
    .due-card {
        background: #1e293b;
        border-left: 4px solid #f59e0b;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 10px;
        border-top: 1px solid #334155;
        border-right: 1px solid #334155;
        border-bottom: 1px solid #334155;
    }
    .due-card-rec {
        background: #1e293b;
        border-left: 4px solid #38bdf8;
        border-top: 1px solid #0284c7;
        border-right: 1px solid #0284c7;
        border-bottom: 1px solid #0284c7;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .due-action {
        color: #38bdf8;
        font-weight: bold;
        font-size: 13.5px;
        margin-top: 4px;
    }
    .stat-card {
        background: #0f172a;
        border-radius: 6px;
        padding: 12px 6px;
        text-align: center;
        border: 1px solid #334155;
        margin-bottom: 8px;
    }
    .neglect-alert {
        background: #450a0a;
        border-left: 5px solid #ef4444;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 14px;
        color: #fecaca;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ==============================================================================
# 1. マスターデータ定義 ＆ ページ数準拠の精密重み辞書
# ==============================================================================
TOPICS_MASTER = {
    "商業・個別(教科書2)": [
        "CH01 有形固定資産",
        "CH02 資産除去債務",
        "CH03 リース会計",
        "CH04 固定資産の減損会計",
        "CH05 無形固定資産・繰延資産",
        "CH06 研究開発費・ソフトウェア",
        "CH07 引当金",
        "CH08 退職給付会計",
        "CH09 社債",
        "CH10 株主資本",
        "CH11 新株予約権ほか",
        "CH12 税効果会計",
    ],
    "商業・基礎/特殊(教科書1)": [
        "CH01 会計学基礎",
        "CH02 P/L基礎",
        "CH03 収益認識",
        "CH04 工事契約",
        "CH05 一般商品売買",
        "CH06-08 特殊商品売買",
        "CH09 会計上の変更・誤謬",
        "CH10 B/S基礎",
        "CH11 現金預金",
        "CH12 債権・貸倒引当金",
        "CH13 有価証券",
        "CH14 デリバティブ",
    ],
    "商業・連結(教科書3)": [
        "CH01 本支店会計",
        "CH02 企業結合・事業分離",
        "CH03-05 連結会計(I~III)",
        "CH06 持分法",
        "CH07 外貨換算",
        "CH08-09 キャッシュ・フロー",
        "CH10 包括利益",
    ],
    "工業簿記・原価計算": [
        "費目別計算",
        "製造間接費会計",
        "部門別計算",
        "個別原価計算",
        "総合原価計算",
        "標準原価計算",
        "直接原価計算",
        "CVP分析・予算編成",
        "事業部制・差異分析",
        "業務的・設備投資の意思決定",
        "戦略的原価管理(ABC等)",
    ],
}

ALL_TOPICS = [t for sublist in TOPICS_MASTER.values() for t in sublist]

# 論点からカテゴリーを逆引きするマップ
TOPIC_TO_CAT_MAP = {
    t: cat for cat, t_list in TOPICS_MASTER.items() for t in t_list
}

TOPIC_WORKLOAD_WEIGHTS = {
    # 商業簿記・基礎/特殊 (教科書1: 全278p)
    "CH01 会計学基礎": 0.6,
    "CH02 P/L基礎": 0.3,
    "CH03 収益認識": 1.1,
    "CH04 工事契約": 1.1,
    "CH05 一般商品売買": 1.4,
    "CH06-08 特殊商品売買": 1.6,
    "CH09 会計上の変更・誤謬": 0.5,
    "CH10 B/S基礎": 0.3,
    "CH11 現金預金": 0.6,
    "CH12 債権・貸倒引当金": 2.0,
    "CH13 有価証券": 1.0,
    "CH14 デリバティブ": 1.2,
    # 商業簿記・個別 (教科書2: 全295p)
    "CH01 有形固定資産": 1.8,
    "CH02 資産除去債務": 0.8,
    "CH03 リース会計": 1.3,
    "CH04 固定資産の減損会計": 1.4,
    "CH05 無形固定資産・繰延資産": 0.4,
    "CH06 研究開発費・ソフトウェア": 0.7,
    "CH07 引当金": 0.5,
    "CH08 退職給付会計": 1.5,
    "CH09 社債": 1.3,
    "CH10 株主資本": 1.0,
    "CH11 新株予約権ほか": 1.1,
    "CH12 税効果会計": 1.5,
    # 商業簿記・連結 (教科書3: 全364p)
    "CH01 本支店会計": 1.2,
    "CH02 企業結合・事業分離": 1.3,
    "CH03-05 連結会計(I~III)": 4.5,
    "CH06 持分法": 1.0,
    "CH07 外貨換算": 1.5,
    "CH08-09 キャッシュ・フロー": 2.2,
    "CH10 包括利益": 0.8,
    # 工業簿記・原価計算 (教科書1〜3: 全829p)
    "費目別計算": 2.2,
    "製造間接費会計": 1.1,
    "部門別計算": 2.0,
    "個別原価計算": 1.4,
    "総合原価計算": 4.5,
    "標準原価計算": 4.0,
    "直接原価計算": 1.5,
    "CVP分析・予算編成": 2.5,
    "事業部制・差異分析": 2.4,
    "業務的・設備投資の意思決定": 2.6,
    "戦略的原価管理(ABC等)": 1.1,
}

LEVELS_LIST = [
    "TAC入門 (赤)",
    "TAC詳細 (青)",
    "ALFA演習 (紫)",
    "クレアドバンスト (緑)",
]

LEVEL_KEY_MAP = {
    "TAC入門 (赤)": "red",
    "TAC詳細 (青)": "blue",
    "TAC詳細/ALFA (青)": "blue",
    "ALFA演習 (紫)": "purple",
    "クレアドバンスト (緑)": "green",
}

LEVEL_RANK = {
    "TAC入門 (赤)": 1,
    "TAC詳細 (青)": 2,
    "TAC詳細/ALFA (青)": 2,
    "ALFA演習 (紫)": 3,
    "クレアドバンスト (緑)": 4,
}

LEVEL_MAX_CAP = {
    "TAC入門 (赤)": 0.25,
    "TAC詳細 (青)": 0.50,
    "TAC詳細/ALFA (青)": 0.50,
    "ALFA演習 (紫)": 0.75,
    "クレアドバンスト (緑)": 1.00,
}

STEPS = [
    "未着手",
    "① 流し読み完了",
    "② 例題解いた",
    "③ 問題集1周目解いた",
    "④ 問題集2周目解いた",
    "⑤ 反復演習(3周目以降)",
]

VALID_STEPS = STEPS[1:]
DATA_FILE = "boki1_study_data.json"
EXAM_DATE = datetime.date(2027, 2, 21)

# ==============================================================================
# 2. データ読み込み ＆ 状態サニタイズ
# ==============================================================================
def create_default_topic(category):
  return {
      "category": category,
      "level": "TAC入門 (赤)",
      "step": "未着手",
      "status_quadrant": "右下_苦手未達",
      "streak": 0,
      "round_count": 0,
      "last_date": None,
      "scheduled_interval": 3,
      "next_date": datetime.date.today().isoformat(),
      "stability": 6.0,
      "careless_count": 0,
      "lack_count": 0,
      "caution_flag": False,
      "caution_memo": "",
  }


def sanitize_and_patch_data(raw_data):
  if not isinstance(raw_data, dict):
    raw_data = {}
  raw_data.setdefault("topics", {})
  raw_data.setdefault("logs", [])
  raw_data.setdefault("mock_exams", [])

  for cat, t_list in TOPICS_MASTER.items():
    for t in t_list:
      if t not in raw_data["topics"]:
        raw_data["topics"][t] = create_default_topic(cat)
      else:
        item = raw_data["topics"][t]
        if not item.get("category"):
          item["category"] = cat
        item.setdefault("level", "TAC入門 (赤)")
        item.setdefault("step", "未着手")
        item.setdefault("status_quadrant", "右下_苦手未達")
        item.setdefault("streak", 0)
        item.setdefault("round_count", 0)
        item.setdefault("last_date", None)
        item.setdefault("scheduled_interval", 3)
        item.setdefault("next_date", datetime.date.today().isoformat())
        item.setdefault("stability", 6.0)
        item.setdefault("careless_count", 0)
        item.setdefault("lack_count", 0)
        item.setdefault("caution_flag", False)
        item.setdefault("caution_memo", "")
  return raw_data


def load_data():
  # 旧ファイル名互換（boki1_os_data.json があればそれも探索）
  target_files = [DATA_FILE, "boki1_os_data.json"]
  for fname in target_files:
    if os.path.exists(fname):
      try:
        with open(fname, "r", encoding="utf-8") as f:
          data = json.load(f)
          if (
              isinstance(data, dict)
              and "topics" in data
              and len(data["topics"]) > 0
          ):
            return sanitize_and_patch_data(data)
      except Exception:
        pass
  return sanitize_and_patch_data({})


def save_data():
  with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(st.session_state.app_data, f, ensure_ascii=False, indent=2)


if "app_data" not in st.session_state:
  st.session_state.app_data = load_data()

app_data = st.session_state.app_data

# ==============================================================================
# 3. 基礎スコア計算 ＆ ガイド
# ==============================================================================
def calculate_topic_single_score(d):
  step = d.get("step", "未着手")
  if step == "未着手":
    return 0.0

  lvl = d.get("level", "TAC入門 (赤)")
  rounds = max(1, d.get("round_count", 1))
  quad = d.get("status_quadrant", "右下_苦手未達")

  max_cap = LEVEL_MAX_CAP.get(lvl, 0.25)
  round_saturation = 1.0 - (0.5**rounds)

  if quad == "左上_得意できた":
    quality = 1.0
  elif quad == "左下_苦手できた":
    quality = 0.85
  elif quad == "右上_得意未達":
    quality = 0.65
  else:
    quality = 0.45

  topic_point = min(max_cap, max_cap * round_saturation * quality)
  return round(topic_point * 100, 1)


def calculate_safe_progress(topics_dict):
  if not topics_dict:
    return 0.0
  total_weighted_score = 0.0
  total_weight = 0.0
  for t_name, d in topics_dict.items():
    w = TOPIC_WORKLOAD_WEIGHTS.get(t_name, 1.0)
    score = calculate_topic_single_score(d)
    total_weighted_score += score * w
    total_weight += w

  if total_weight == 0:
    return 0.0
  return round(total_weighted_score / total_weight, 1)


def get_topic_action_guide(topic_data):
  level = topic_data.get("level", "TAC入門 (赤)")
  step = topic_data.get("step", "未着手")
  quadrant = topic_data.get("status_quadrant", "右下_苦手未達")
  caution = topic_data.get("caution_flag", False)
  memo = topic_data.get("caution_memo", "")

  if caution:
    return (
        f"🚨 【模試失点リベンジ】 {memo}。解説・下書きを見直し、もう一度白紙で解き直す！"
    )

  if step == "未着手":
    return (
        f"📖 【{level}】 該当箇所の『① 流し読み』で骨組みと解法パターンを把握！"
    )
  elif step == "① 流し読み完了":
    return (
        f"✏️ 【{level}】 『② 例題解いた』を白紙から手を動かして下書きを作る！"
    )
  elif step == "② 例題解いた":
    if "苦手" in quadrant:
      return (
          f"🔄 【{level}】 迷いあり。例題の再演習 または 『③"
          " 問題集1周目』で定着！"
      )
    return f"🎯 【{level}】 『③ 問題集1周目解いた』をタイムアタックで解く！"
  elif step == "③ 問題集1周目解いた":
    if "苦手" in quadrant:
      return (
          f"🔥 【{level}】 間違い要因を分析し、『④"
          " 問題集2周目解いた』で自力クリア！"
      )
    return (
        f"⏳ 【{level}】 日を空けて『④"
        " 問題集2周目解いた』を解き、完全定着・次教材へ！"
    )
  else:
    if "左上" in quadrant:
      if level == "クレアドバンスト (緑)":
        return "👑 【完全制覇】 忘却防止の定期メンテ演習（または本番答練へ）"
      return (
          f"🎉 【{level} クリア】"
          " 上位教材（青/紫/緑）へ進めて演習を記録しよう！"
      )
    else:
      return (
          f"🔁 【{level}】 まだ定着が不十分（{quadrant}）。『⑤"
          " 反復演習』で自力満点を目指す！"
      )


# ==============================================================================
# 4. 【上位レイヤー】3フェーズ適応型 ＆ 負荷重み連動 逆算エンジン
# ==============================================================================
def run_phase_aware_backprop_engine(app_data, today_date):
  days_left = max(1, (EXAM_DATE - today_date).days)
  topics = app_data.get("topics", {})
  mock_exams = app_data.get("mock_exams", [])
  logs = app_data.get("logs", [])

  if days_left <= 28:
    current_phase = 3
  elif len(mock_exams) > 0 or days_left <= 45:
    current_phase = 2
  else:
    current_phase = 1

  # 今日の消化枠数を集計
  today_str = today_date.isoformat()
  today_done = sum(
      TOPIC_WORKLOAD_WEIGHTS.get(lg.get("topic"), 1.0)
      for lg in logs
      if lg.get("date") == today_str
  )

  # -------------------------------------------------------------
  # Phase 1: 導入期（基礎3周目標 ＆ 本日の消化進捗）
  # -------------------------------------------------------------
  if current_phase == 1:
    phase1_days_left = max(1, days_left - 45)
    remaining_workload = 0.0
    for t, d in topics.items():
      w = TOPIC_WORKLOAD_WEIGHTS.get(t, 1.0)
      st_val = d.get("step", "未着手")
      if st_val == "未着手":
        remaining_workload += w
      elif st_val == "① 流し読み完了":
        remaining_workload += w * 0.5

    daily_workload_quota = round(
        (remaining_workload / phase1_days_left) * 10, 1
    )
    daily_workload_quota = max(8, daily_workload_quota)

    norma_text = f"{round(today_done, 1)} / {daily_workload_quota} 枠"
    norma_subtext = "🎯 本日ノルマ (基礎10周基準)"

    def p1_key(t_name):
      d = topics[t_name]
      step_order = 0 if d.get("step") == "未着手" else 1
      return (
          step_order,
          TOPIC_WORKLOAD_WEIGHTS.get(t_name, 1.0),
          calculate_topic_single_score(d),
      )

    sorted_p1 = sorted(topics.keys(), key=p1_key)
    rec_topic = sorted_p1[0] if sorted_p1 else ALL_TOPICS[0]

  # -------------------------------------------------------------
  # Phase 2: 応用期（模試スコア逆算）
  # -------------------------------------------------------------
  elif current_phase == 2:
    if len(mock_exams) >= 2:
      scores = [m.get("total", 45) for m in mock_exams[-3:]]
      latest_score = scores[-1] * 0.6 + scores[-2] * 0.4
      has_cutoff = any(m.get("has_cutoff", False) for m in mock_exams[-3:])
    elif mock_exams:
      latest_score = mock_exams[-1].get("total", 45)
      has_cutoff = mock_exams[-1].get("has_cutoff", False)
    else:
      latest_score = 45
      has_cutoff = False

    score_gap = max(5, 75 - latest_score)
    needed_hours = score_gap * 7.5
    if has_cutoff:
      needed_hours *= 1.25

    daily_hours = round(needed_hours / days_left, 1)
    daily_hours = max(1.5, daily_hours)
    daily_workload_quota = round(daily_hours / 0.5, 1)

    norma_text = f"{round(today_done, 1)} / {daily_workload_quota} 枠"
    norma_subtext = f"⚡ 模試逆算 (日: {daily_hours}h)"

    def p2_key(t_name):
      d = topics[t_name]
      c = 1 if d.get("caution_flag") else 0
      is_due = (
          1
          if d.get("step") != "未着手"
          and d.get("next_date", today_date.isoformat()) <= today_date.isoformat()
          else 0
      )
      w = TOPIC_WORKLOAD_WEIGHTS.get(t_name, 1.0)
      return (c, is_due, w, -calculate_topic_single_score(d))

    sorted_p2 = sorted(topics.keys(), key=p2_key, reverse=True)
    rec_topic = sorted_p2[0] if sorted_p2 else ALL_TOPICS[0]

  # -------------------------------------------------------------
  # Phase 3: 直前スプリント
  # -------------------------------------------------------------
  else:
    daily_workload_quota = 8.0
    norma_text = f"{round(today_done, 1)} / {daily_workload_quota} 枠"
    norma_subtext = "🔥 直前総回転モード"

    def p3_key(t_name):
      d = topics[t_name]
      c = 1 if d.get("caution_flag") else 0
      quad = d.get("status_quadrant", "")
      fail = 1 if "未達" in quad else 0
      w = TOPIC_WORKLOAD_WEIGHTS.get(t_name, 1.0)
      return (c, fail, w, -calculate_topic_single_score(d))

    sorted_p3 = sorted(topics.keys(), key=p3_key, reverse=True)
    rec_topic = sorted_p3[0] if sorted_p3 else ALL_TOPICS[0]

  rec_cat = topics[rec_topic].get(
      "category", TOPIC_TO_CAT_MAP.get(rec_topic, list(TOPICS_MASTER.keys())[0])
  )

  return {
      "phase": current_phase,
      "daily_workload_quota": daily_workload_quota,
      "norma_text": norma_text,
      "norma_subtext": norma_subtext,
      "recommended_topic": rec_topic,
      "recommended_category": rec_cat,
  }


# ==============================================================================
# 5. 【下位レイヤー】SRSスケジューラ
# ==============================================================================
def calculate_adaptive_srs_interval(
    current_s,
    elapsed_days,
    scheduled_interval,
    result_quadrant,
    streak,
    prev_level,
    new_level,
    days_to_exam,
    volatility_ratio,
):
  prev_rank = LEVEL_RANK.get(prev_level, 1)
  new_rank = LEVEL_RANK.get(new_level, 1)
  if new_rank > prev_rank:
    diff = new_rank - prev_rank
    reset_factor = 0.65 if diff == 1 else 0.45
    current_s = max(3.0, current_s * reset_factor)

  score_map = {
      "左上_得意できた": 0.95,
      "左下_苦手できた": 0.75,
      "右上_得意未達": 0.40,
      "右下_苦手未達": 0.15,
  }
  actual_score = score_map.get(result_quadrant, 0.50)

  scheduled_interval = max(1, scheduled_interval)
  early_ratio = min(1.0, max(0.1, elapsed_days / scheduled_interval))

  if elapsed_days >= 1:
    obs_s = -elapsed_days / math.log(actual_score)
    effective_alpha = 0.25 * (early_ratio**1.5)
    new_s = (1 - effective_alpha) * current_s + effective_alpha * obs_s
  else:
    new_s = current_s

  if "できた" in result_quadrant:
    growth_multiplier = 1.0 + (0.08 * (early_ratio**0.8)) * min(streak, 5)
    new_s = new_s * growth_multiplier
  else:
    new_s = max(2.5, new_s * 0.45)

  new_s = max(2.0, round(new_s, 2))

  base_opt_days = max(1, int(round(new_s * 0.1625)))

  if "未達" in result_quadrant:
    opt_days = 1 if result_quadrant == "右下_苦手未達" else 2
  else:
    stability_factor = max(0.5, 1.0 - (0.5 * volatility_ratio))
    opt_days = max(1, int(round(base_opt_days * stability_factor)))

  if days_to_exam > 50:
    max_cap = 21
  elif days_to_exam > 30:
    max_cap = 14
  elif days_to_exam > 14:
    max_cap = 8
  else:
    max_cap = 4

  safe_exam_limit = max(1, days_to_exam - 3)
  opt_days = min(opt_days, max_cap, safe_exam_limit)
  opt_days = max(1, opt_days)

  return new_s, opt_days


def update_step_progress(
    topic_name,
    selected_level,
    step_name,
    is_cleared,
    is_good_feeling,
    memo="",
):
  today = datetime.date.today()
  days_to_exam = (EXAM_DATE - today).days
  t_data = app_data["topics"][topic_name]

  prev_level = t_data.get("level", selected_level)

  if is_cleared and is_good_feeling:
    quadrant = "左上_得意できた"
  elif is_cleared and not is_good_feeling:
    quadrant = "左下_苦手できた"
  elif not is_cleared and is_good_feeling:
    quadrant = "右上_得意未達"
  else:
    quadrant = "右下_苦手未達"

  last_d_str = t_data.get("last_date")
  elapsed_days = (
      (today - datetime.date.fromisoformat(last_d_str)).days
      if last_d_str
      else 1
  )

  scheduled_interval = t_data.get("scheduled_interval", max(3, elapsed_days))
  streak = t_data.get("streak", 0)
  streak = (streak + 1) if is_cleared else 0

  past_topic_logs = [
      lg for lg in app_data.get("logs", []) if lg.get("topic") == topic_name
  ][-5:]
  if past_topic_logs:
    fail_count = sum(1 for lg in past_topic_logs if not lg.get("cleared", True))
    volatility_ratio = fail_count / len(past_topic_logs)
  else:
    volatility_ratio = 0.0

  current_s = t_data.get("stability", 6.0)
  new_s, opt_days = calculate_adaptive_srs_interval(
      current_s=current_s,
      elapsed_days=elapsed_days,
      scheduled_interval=scheduled_interval,
      result_quadrant=quadrant,
      streak=streak,
      prev_level=prev_level,
      new_level=selected_level,
      days_to_exam=days_to_exam,
      volatility_ratio=volatility_ratio,
  )

  t_data["level"] = selected_level
  t_data["step"] = step_name
  t_data["status_quadrant"] = quadrant
  t_data["streak"] = streak
  t_data["stability"] = new_s
  t_data["round_count"] = t_data.get("round_count", 0) + 1
  t_data["last_date"] = today.isoformat()
  t_data["scheduled_interval"] = opt_days
  t_data["next_date"] = (today + datetime.timedelta(days=opt_days)).isoformat()
  t_data["caution_flag"] = False
  t_data["caution_memo"] = ""

  app_data["logs"].append({
      "date": today.isoformat(),
      "topic": topic_name,
      "level": selected_level,
      "step": step_name,
      "cleared": is_cleared,
      "subjective": "得意" if is_good_feeling else "苦手",
      "elapsed_days": elapsed_days,
      "scheduled_interval": scheduled_interval,
      "volatility": round(volatility_ratio, 2),
      "stability": new_s,
      "next_interval": opt_days,
      "memo": memo,
  })
  save_data()


def record_mock_exam(
    exam_name,
    score_comm,
    score_acct,
    score_ind,
    score_cost,
    miss_topics_careless,
    miss_topics_lack,
):
  today = datetime.date.today()
  total_score = score_comm + score_acct + score_ind + score_cost
  is_failed_subject = any(
      s < 10 for s in [score_comm, score_acct, score_ind, score_cost]
  )

  for t in miss_topics_careless:
    if t in app_data["topics"]:
      item = app_data["topics"][t]
      item["status_quadrant"] = "右上_得意未達"
      item["caution_flag"] = True
      item["careless_count"] = item.get("careless_count", 0) + 1
      item["caution_memo"] = (
          f"模試({exam_name})で過信失点！トラップ・下書き要確認"
      )
      item["streak"] = 0
      item["stability"] = 2.0
      item["next_date"] = today.isoformat()

  for t in miss_topics_lack:
    if t in app_data["topics"]:
      item = app_data["topics"][t]
      item["status_quadrant"] = "右下_苦手未達"
      item["lack_count"] = item.get("lack_count", 0) + 1
      item["streak"] = 0
      item["stability"] = 2.0
      item["next_date"] = today.isoformat()

  app_data["mock_exams"].append({
      "date": today.isoformat(),
      "name": exam_name,
      "comm": score_comm,
      "acct": score_acct,
      "ind": score_ind,
      "cost": score_cost,
      "total": total_score,
      "passed": (total_score >= 70 and not is_failed_subject),
      "has_cutoff": is_failed_subject,
      "careless_miss": miss_topics_careless,
      "lack_miss": miss_topics_lack,
  })
  save_data()


# ==============================================================================
# 5.5 【追加】期待得点コーチ（今日のプランを自動提示）
#     期待得点 = 配点 × 得点力(教材レベル×ステップ×できの質) × 記憶保持 exp(-経過日数/stability)
#     1分あたりの期待得点増が大きい順に、今日使える時間へ詰める。
#     ★ 配点・時間の数値は仮置き。TOPIC_META / STEP_TIME などを過去問・実績に合わせて調整すること。
# ==============================================================================
# =============================================================================
# 設定
# =============================================================================
PASS_TOTAL = 70            # 合格点（合計）
CUTOFF = 10                # 足切り（各科目）
N_QUESTIONS = 4            # 1科目あたりの大問数（合格確率の推定に使用）

MINUTES_PER_UNIT = 30      # 負荷重み 1.0 = 30分（プロトタイプの「1枠=0.5h」と同じ）
HORIZON_DAYS = 7           # 「7日後（直前期は本番日）の期待得点」で価値を測る
SESSION_CAP_MIN = 60       # 1セッションの上限（超える分は翌日以降に分割）
STEP_GAP_DAYS = 2          # ラダーの各ステップは2日おきに行う想定
REVIEW_SHARE = 0.45        # 復習(想起)に充てる時間は1日の45%まで
MIN_BLOCK_MIN = 30         # 新規学習が短すぎるときは、次のステップと束ねてこの時間以上にする
MIN_SESSION_MIN = 10
PAPER_CAP = 0.60           # 商会/工原のどちらか一方に1日の60%超を割り当てない（まず均等、余れば偏らせてよい）
PACE_SPREAD = 1.5          # 大物論点は、所要日数の1.5倍（間隔をあけるため）の助走期間が要る
REVENGE_BOOST = 3.0        # 模試で実際に落とした論点は、推定より確実な失点源として優先
MAX_REVENGE = 2
CUT_WEIGHT = 1.5           # 足切り確率100%の科目の論点に +150% の加点
MISS_BONUS = 0.08          # 模試で落とした論点は配点を +8%/回（最大3回）上乗せ

DEFAULT_MINUTES = 180

SUBJECTS = ["comm", "acct", "ind", "cost"]
SUBJECT_LABEL = {"comm": "商業簿記", "acct": "会計学", "ind": "工業簿記", "cost": "原価計算"}

# プロトタイプの定義と一致させること
LEVELS = LEVELS_LIST   # プロトタイプの定義を共有
LEVEL_ALIAS = {"TAC詳細/ALFA (青)": "TAC詳細 (青)"}
# STEPS はプロトタイプの定義を共有
QUAD_GOOD = "左上_得意できた"

# 得点力: level の下限〜上限の間を step の進み具合と「できの質」で進む
LEVEL_FLOOR = [0.00, 0.25, 0.50, 0.75]
LEVEL_CAP = [0.25, 0.50, 0.75, 1.00]
STEP_PROGRESS = {1: 0.15, 2: 0.35, 3: 0.60, 4: 0.85, 5: 1.00}
QUALITY = {"左上_得意できた": 1.00, "左下_苦手できた": 0.85, "右上_得意未達": 0.65, "右下_苦手未達": 0.45}
Q_SUCCESS = 0.92           # 次の演習が成功したときの想定「できの質」
ABILITY_MAX = 0.92         # 本番で凡ミスゼロは無い

# 各 level で踏むステップ（紫・緑は演習教材なので ③④ から）
LADDER = {0: [1, 2, 3, 4], 1: [1, 2, 3, 4], 2: [3, 4], 3: [3, 4]}

# 1論点を1周するのに対する所要時間の比率
STEP_TIME = {1: 0.60, 2: 0.60, 3: 1.00, 4: 0.70, 5: 0.50}
LEVEL_TIME = [0.8, 1.0, 1.0, 1.0]

MATERIAL = ["TAC入門(赤)", "TAC詳細(青)", "ALFA演習(紫)", "クレアドバンスト(緑)"]
DIFFICULTY = ["基本（やさしめ）", "標準", "応用", "本試験レベル"]

# 負荷重み（プロトタイプの TOPIC_WORKLOAD_WEIGHTS のコピー。アプリ側から weights を渡せば上書きされる）
DEFAULT_WEIGHTS = TOPIC_WORKLOAD_WEIGHTS   # プロトタイプの負荷重みを共有

# 論点ごとの (出題ウェイト 0.5-14, 科目への配分)。数字が大きいほど「本番で点になりやすい」。
# ★一般的な出題傾向に基づく仮置き。過去問の実績に合わせて必ず書き換えてください。
#   科目ごとに合計25点へ自動正規化されます（相対比だけが効きます）。
_C, _A, _I, _K = "comm", "acct", "ind", "cost"
TOPIC_META = {
    # 商業・基礎/特殊
    "CH01 会計学基礎": (0.5, {_A: 1.0}),
    "CH02 P/L基礎": (0.5, {_A: 1.0}),
    "CH03 収益認識": (4, {_C: 0.5, _A: 0.5}),
    "CH04 工事契約": (2.5, {_C: 0.7, _A: 0.3}),
    "CH05 一般商品売買": (2, {_C: 0.8, _A: 0.2}),
    "CH06-08 特殊商品売買": (1.5, {_C: 0.8, _A: 0.2}),
    "CH09 会計上の変更・誤謬": (2.5, {_A: 0.7, _C: 0.3}),
    "CH10 B/S基礎": (0.5, {_A: 1.0}),
    "CH11 現金預金": (1.5, {_C: 0.6, _A: 0.4}),
    "CH12 債権・貸倒引当金": (2.5, {_C: 0.6, _A: 0.4}),
    "CH13 有価証券": (4, {_C: 0.6, _A: 0.4}),
    "CH14 デリバティブ": (2.5, {_A: 0.6, _C: 0.4}),
    # 商業・個別
    "CH01 有形固定資産": (4, {_A: 0.6, _C: 0.4}),
    "CH02 資産除去債務": (2.5, {_A: 0.5, _C: 0.5}),
    "CH03 リース会計": (4, {_C: 0.5, _A: 0.5}),
    "CH04 固定資産の減損会計": (4, {_A: 0.6, _C: 0.4}),
    "CH05 無形固定資産・繰延資産": (1.5, {_A: 0.8, _C: 0.2}),
    "CH06 研究開発費・ソフトウェア": (2.5, {_A: 0.7, _C: 0.3}),
    "CH07 引当金": (2.5, {_A: 0.6, _C: 0.4}),
    "CH08 退職給付会計": (4, {_C: 0.5, _A: 0.5}),
    "CH09 社債": (2.5, {_C: 0.6, _A: 0.4}),
    "CH10 株主資本": (3.5, {_C: 0.6, _A: 0.4}),
    "CH11 新株予約権ほか": (2.5, {_C: 0.6, _A: 0.4}),
    "CH12 税効果会計": (4, {_C: 0.7, _A: 0.3}),
    # 商業・連結（商業簿記の柱）
    "CH01 本支店会計": (4, {_C: 1.0}),
    "CH02 企業結合・事業分離": (5, {_C: 0.6, _A: 0.4}),
    "CH03-05 連結会計(I~III)": (14, {_C: 0.85, _A: 0.15}),
    "CH06 持分法": (3, {_C: 0.7, _A: 0.3}),
    "CH07 外貨換算": (5, {_C: 0.7, _A: 0.3}),
    "CH08-09 キャッシュ・フロー": (4, {_A: 0.6, _C: 0.4}),
    "CH10 包括利益": (1.5, {_A: 1.0}),
    # 工業簿記・原価計算
    "費目別計算": (4, {_I: 1.0}),
    "製造間接費会計": (4, {_I: 0.7, _K: 0.3}),
    "部門別計算": (4, {_I: 0.6, _K: 0.4}),
    "個別原価計算": (4, {_I: 1.0}),
    "総合原価計算": (9, {_I: 0.7, _K: 0.3}),
    "標準原価計算": (9, {_I: 0.5, _K: 0.5}),
    "直接原価計算": (5, {_I: 0.5, _K: 0.5}),
    "CVP分析・予算編成": (7, {_K: 1.0}),
    "事業部制・差異分析": (5, {_K: 1.0}),
    "業務的・設備投資の意思決定": (7, {_K: 1.0}),
    "戦略的原価管理(ABC等)": (3, {_K: 1.0}),
}


# =============================================================================
# 基本関数（得点力・記憶保持・状態）
# =============================================================================
@dataclass(frozen=True)
class St:
    """論点の状態。L: level(0-3) / k: step(0-5) / q: できの質 / S: stability(日) / elapsed: 最終学習からの日数"""
    L: int
    k: int
    q: float
    S: float
    elapsed: float


def _level_idx(name) -> int:
    name = LEVEL_ALIAS.get(name, name)
    return LEVELS.index(name) if name in LEVELS else 0


def _step_idx(name) -> int:
    return STEPS.index(name) if name in STEPS else 0


def _parse_date(s):
    try:
        return datetime.date.fromisoformat(s) if s else None
    except Exception:
        return None


def ability(L: int, k: int, q: float) -> float:
    """その論点で本番に取れる割合（忘却前）"""
    if k <= 0:
        return 0.0
    L = min(max(L, 0), 3)
    span = LEVEL_CAP[L] - LEVEL_FLOOR[L]
    return ABILITY_MAX * (LEVEL_FLOOR[L] + span * STEP_PROGRESS[min(k, 5)] * q)


def retention(elapsed: float, S: float) -> float:
    return math.exp(-max(0.0, elapsed) / max(0.5, S))


def value(st: St, pts: float, H: float) -> float:
    """H日後時点の期待得点（この論点ぶん）"""
    return pts * ability(st.L, st.k, st.q) * retention(st.elapsed + H, st.S)


def p_success(st: St, level_up: bool = False) -> float:
    """次の演習が「できた」になる確率（自信度と忘却から）"""
    q = st.q if st.k > 0 else 0.6
    p = (0.45 + 0.45 * q) * (0.75 + 0.25 * retention(st.elapsed, st.S))
    if level_up:
        p -= 0.08
    return min(0.92, max(0.30, p))


def _grown(S: float, R_now: float, level_up: bool = False) -> float:
    """成功後の stability。忘れかけで成功するほど伸びる（間隔効果）。直後の復習はほぼ伸びない。
    level が上がるとリセット気味"""
    if level_up:
        S = max(3.0, S * 0.65)
    return min(60.0, S * (1.05 + 1.0 * (1.0 - R_now)))


def _next_target(L: int, k: int, good: bool, cleared: bool = True):
    """(L,k) の次にやるべき (L', k', 解き直しか) を返す。プロトタイプの action_guide と同じ流れ
    good: 左上（得意×できた） / cleared: できた（左上 or 左下）"""
    if k <= 0:
        return (L, LADDER[L][0], False)
    if k == 2 and not cleared and 2 in LADDER[L]:
        return (L, 2, True)                     # 例題が解けなかった → やり直し
    later = [s for s in LADDER[L] if s > k]
    if later:
        return (L, later[0], False)
    if not good:
        return (L, 5, False)                    # 定着不足 → ⑤ 反復
    if L < 3:
        return (L + 1, LADDER[L + 1][0], False)  # 上位教材へ
    return None                                 # 緑・左上：あとは維持のみ


def _round5(x: float) -> int:
    return int(round(x / 5.0) * 5)


def full_minutes(w: float, L: int, k: int, redo: bool = False) -> int:
    f = STEP_TIME[min(max(k, 1), 5)] * (0.6 if redo else 1.0)
    return max(MIN_SESSION_MIN, _round5(MINUTES_PER_UNIT * w * f * LEVEL_TIME[L]))


def review_minutes(w: float, L: int) -> int:
    return min(45, max(MIN_SESSION_MIN, _round5(MINUTES_PER_UNIT * w * 0.25 * LEVEL_TIME[L])))


def revenge_minutes(w: float, L: int) -> int:
    return min(60, max(15, _round5(MINUTES_PER_UNIT * w * 0.5 * LEVEL_TIME[L])))


# =============================================================================
# 論点情報の構築
# =============================================================================
@dataclass
class TopicInfo:
    name: str
    category: str
    w: float
    pts: np.ndarray        # 科目別の想定配点 (4,)
    pts_eff: float         # 模試ミス補正後の合計配点
    st: St
    quad: str
    caution: bool
    memo: str
    miss: int
    paper: int             # 0: 商業簿記・会計学 / 1: 工業簿記・原価計算
    due: bool = False      # SRS上の復習期限が来ている


def _default_meta(name, d):
    if "工業" in (d.get("category") or ""):
        return 2, {_I: 0.5, _K: 0.5}
    return 2, {_C: 0.5, _A: 0.5}


def _build_infos(app_data, weights, today):
    topics = app_data.get("topics", {}) or {}
    names = list(dict.fromkeys(list(TOPIC_META) + list(topics)))
    raw = np.zeros((len(names), 4))
    for i, n in enumerate(names):
        freq, split = TOPIC_META.get(n) or _default_meta(n, topics.get(n, {}))
        for j, s in enumerate(SUBJECTS):
            raw[i, j] = freq * split.get(s, 0.0)
    col = raw.sum(axis=0)
    col[col == 0] = 1.0
    pts = 25.0 * raw / col                       # 科目ごとに合計25点

    infos = []
    for i, n in enumerate(names):
        d = topics.get(n, {}) or {}
        L, k = _level_idx(d.get("level")), _step_idx(d.get("step"))
        quad = d.get("status_quadrant", "右下_苦手未達")
        q = QUALITY.get(quad, 0.45)
        S = max(1.0, float(d.get("stability", 6.0) or 6.0))
        ld = _parse_date(d.get("last_date"))
        if ld:
            elapsed = max(0, (today - ld).days)
        else:
            elapsed = 30 if k > 0 else 0
        miss = int(d.get("careless_count", 0) or 0) + int(d.get("lack_count", 0) or 0)
        p = pts[i]
        pts_eff = float(p.sum()) * (1.0 + MISS_BONUS * min(3, miss))
        paper = 0 if (p[0] + p[1]) >= (p[2] + p[3]) else 1
        nd = _parse_date(d.get("next_date"))
        due = (nd <= today) if nd else (retention(elapsed, S) < 0.7)
        infos.append(TopicInfo(
            name=n, category=d.get("category") or "", w=float(weights.get(n, DEFAULT_WEIGHTS.get(n, 1.0))),
            pts=p, pts_eff=pts_eff, st=St(L, k, q, S, float(elapsed)), quad=quad,
            caution=bool(d.get("caution_flag", False)), memo=d.get("caution_memo", "") or "",
            miss=miss, paper=paper, due=due,
        ))
    return infos


# =============================================================================
# 現状の推定（本番を今日受けたら）
# =============================================================================
def estimate_exam(infos, mocks, rng, n=4000):
    T = len(infos)
    m = np.array([ability(i.st.L, i.st.k, i.st.q) * retention(i.st.elapsed, i.st.S) for i in infos])
    P = np.array([i.pts for i in infos])                       # (T,4)
    expected = (P * m[:, None]).sum(axis=0)

    kappa = 5.0
    mc = np.clip(m, 0.02, 0.98)
    a, b = mc * kappa, (1 - mc) * kappa
    scores = np.zeros((n, 4))
    for j in range(4):
        tot = P[:, j].sum()
        if tot <= 0:
            continue
        idx = rng.choice(T, size=(n, N_QUESTIONS), p=P[:, j] / tot)
        scores[:, j] = rng.beta(a[idx], b[idx]).sum(axis=1) * (25.0 / N_QUESTIONS)
    total = scores.sum(axis=1)
    p_pass = float(((total >= PASS_TOTAL) & (scores.min(axis=1) >= CUTOFF)).mean())
    p_cut = (scores < CUTOFF).mean(axis=0)

    last = None
    if mocks:
        last = mocks[-1]
        for j, s in enumerate(SUBJECTS):                       # 直近の模試で足切りだった科目は最低でもリスクを見積もる
            v = last.get(s)
            if v is None:
                continue
            if v < CUTOFF:
                p_cut[j] = max(p_cut[j], 0.5)
            elif v < CUTOFF + 3:
                p_cut[j] = max(p_cut[j], 0.3)

    return {
        "subject": {s: float(expected[j]) for j, s in enumerate(SUBJECTS)},
        "total": float(expected.sum()),
        "p_pass": p_pass,
        "p_cut": {s: float(p_cut[j]) for j, s in enumerate(SUBJECTS)},
        "last_mock": last,
    }


# =============================================================================
# 候補生成
# =============================================================================
@dataclass
class _Step:
    L: int
    k: int
    redo: bool
    minutes: int
    cum_minutes: int
    cum_gain: float
    state: St


def _ladder(info: TopicInfo, H: float, max_minutes: float, max_steps: int = 8):
    """成功し続けた場合の学習ラダー。各段までの累積(所要分, 期待得点増)"""
    cur = info.st
    base = value(cur, info.pts_eff, H)
    good = info.quad == QUAD_GOOD
    cleared = info.quad in (QUAD_GOOD, "左下_苦手できた")
    out, cum = [], 0
    for i in range(max_steps):
        nxt = _next_target(cur.L, cur.k, good, cleared)
        if nxt is None:
            break
        L2, k2, redo = nxt
        m = full_minutes(info.w, L2, k2, redo)
        if out and cum + m > max_minutes:
            break
        R = retention(cur.elapsed if i == 0 else STEP_GAP_DAYS, cur.S)
        S2 = _grown(cur.S, R, level_up=(L2 > cur.L and cur.k > 0))
        cur = St(L2, k2, Q_SUCCESS, S2, 0.0)
        good = cleared = True
        cum += m
        out.append(_Step(L2, k2, redo, m, cum, value(cur, info.pts_eff, H) - base, cur))
    return out


def _minutes_to_target(info: TopicInfo, target=(1, 4)) -> int:
    """「TAC詳細(青)の④」まで仕上げるのに要する分数（大物判定用）"""
    L, k, tot = info.st.L, info.st.k, 0
    good = info.quad == QUAD_GOOD
    cleared = info.quad in (QUAD_GOOD, "左下_苦手できた")
    for _ in range(12):
        if (L, k) >= target:
            break
        nxt = _next_target(L, k, good, cleared)
        if nxt is None:
            break
        L, k, redo = nxt
        tot += full_minutes(info.w, L, k, redo)
        good = cleared = True
    return tot


@dataclass
class Cand:
    info: TopicInfo
    kind: str               # learn / review / revenge
    L: int
    k: int
    redo: bool
    minutes: int
    full_minutes: int
    gain: float             # このセッションの期待得点増（成功確率込み）
    upside: float           # この先の伸びしろ（learn のみ）
    score: float
    pace: float = 1.0
    cut: float = 1.0
    block: list = field(default_factory=list)   # learn: 今日まとめてやるラダーの段


def _pace(info: TopicInfo, days_left: int) -> float:
    """大物論点（青④まで仕上げるのに何日もかかる）ほど、残り日数に対して早く着手する必要がある"""
    avail = days_left - 7                              # 直前1週間は仕上げ期間として除く
    if avail <= 7:
        return 1.0
    runway = math.ceil(_minutes_to_target(info) / SESSION_CAP_MIN) * PACE_SPREAD
    return 1.0 + min(2.0, 2.0 * runway / avail)


def _make_candidates(info, H, max_look, days_left, cut_mult):
    cur = info.st
    R = retention(cur.elapsed, cur.S)
    out = []

    if info.caution and cur.k > 0:                                   # 模試ミス → リベンジ
        after = St(cur.L, cur.k, Q_SUCCESS, _grown(max(cur.S, 3.0), R), 0.0)
        gain = p_success(cur) * (value(after, info.pts_eff, H) - value(cur, info.pts_eff, H))
        full = revenge_minutes(info.w, cur.L)
        if gain > 0:
            out.append(Cand(info, "revenge", cur.L, cur.k, False, full, full, gain, 0.0,
                            gain / full * cut_mult * REVENGE_BOOST, 1.0, cut_mult))
        return out

    if cur.k >= 3 and (info.due or R < 0.6):                         # 復習（想起）: SRSの期限が来た、問題演習済みの論点
        after = St(cur.L, cur.k, cur.q, _grown(cur.S, R), 0.0)
        gain = p_success(cur) * (value(after, info.pts_eff, H) - value(cur, info.pts_eff, H))
        full = review_minutes(info.w, cur.L)
        if gain > 0:
            out.append(Cand(info, "review", cur.L, cur.k, False, full, full, gain, 0.0,
                            gain / full * cut_mult, 1.0, cut_mult))

    path = _ladder(info, H, max_look)                               # 次のステップ
    if path:
        first = path[0]
        p1 = p_success(cur, level_up=(first.L > cur.L and cur.k > 0))
        env = max(s.cum_gain / s.cum_minutes for s in path)
        best = max(path, key=lambda s: s.cum_gain / s.cum_minutes)
        j = 0                                                       # 短すぎる作業は次のステップと束ねる
        while (path[j].cum_minutes < MIN_BLOCK_MIN and j + 1 < len(path)
               and path[j + 1].cum_minutes <= SESSION_CAP_MIN):
            j += 1
        block = path[:j + 1]
        full = block[-1].cum_minutes
        gain = p1 * block[-1].cum_gain * (0.9 ** j)
        pace = _pace(info, days_left)
        if env > 0 and gain > 0:
            out.append(Cand(info, "learn", block[-1].L, block[-1].k, first.redo, min(full, SESSION_CAP_MIN), full,
                            gain, max(best.cum_gain, 0.0), p1 * env * pace * cut_mult, pace, cut_mult, block))
    return out


# =============================================================================
# 文面
# =============================================================================
def _difficulty(L: int, q: float) -> str:
    return DIFFICULTY[min(3, max(0, L + (0 if q >= 0.9 else -1)))]


STEP_SHORT = ["", "① 流し読み", "② 例題", "③ 問題集1周目", "④ 問題集2周目", "⑤ 反復演習"]


def _step_text(info, L, k, redo, diff):
    mat = MATERIAL[L]
    if redo:
        return ("② 例題のやり直し", ["前回つまずいた例題だけを、白紙から解き直す", "解けるまで、手順を声に出して確認する"],
                "つまずいた例題を自力で解ける")
    table = {
        1: ([f"{mat}の該当箇所を通読（手は動かさず、全体像を掴む）", "仕訳・公式・用語の「型」をノート1枚に書き出す"],
            "この論点の骨組みを30秒で説明できる"),
        2: (["例題を、解説を見ずに白紙から解く", "間違い・迷った所に印をつけ、原因を1行で書く"],
            "例題の解法手順を見ずに再現できる"),
        3: ([f"難易度：{diff}。時間を計って解く", "間違いを「理解不足／知識抜け／計算ミス」に分類する"],
            "正答率70%以上（時間内）"),
        4: ([f"難易度：{diff}。1周目のミス問題を中心に、日を空けて白紙から解く", "解答を見る前に最後まで書き切る"],
            "1周目のミス問題を自力で正解"),
        5: ([f"難易度：{diff}。ミスノートの罠を先に確認してから解く", "満点と時間短縮（目標時間の90%以内）を狙う"],
            "全問正解を、目標時間内で"),
    }
    bullets, done = table[k]
    return STEP_SHORT[k], bullets, done


def _describe(c: Cand):
    info = c.info
    diff = _difficulty(c.L, info.st.q)
    if c.kind == "revenge":
        bullets = []
        if info.memo:
            bullets.append(info.memo)
        bullets += ["前回の解答・下書きを見直し、ミスの型を「過信／知識不足」に分けて1行メモ",
                    "解説を閉じて、白紙から解き直す"]
        return ("模試ミスのリベンジ", bullets, "同じ問題を白紙から満点で解き直せる",
                f"終わったら → 同じ教材・ステップ『{STEPS[info.st.k]}』で記録（注意フラグが解除されます）", diff)
    if c.kind == "review":
        return ("復習（想起テスト）",
                ["教材を見ずに、仕訳・公式・手順を白紙に書き出す（5分）",
                 "出せなかった所だけ確認し、代表問題を1問、時間を計って解く"],
                "白紙で骨組みを再現でき、代表問題が正解",
                f"終わったら → 現在のステップ『{STEPS[info.st.k]}』のまま記録（復習間隔が更新されます）", diff)

    parts = [_step_text(info, s.L, s.k, s.redo, _difficulty(s.L, Q_SUCCESS if i else info.st.q))
             for i, s in enumerate(c.block)]
    mats = list(dict.fromkeys(MATERIAL[s.L] for s in c.block))
    if len(mats) == 1:
        title = " → ".join(p[0] for p in parts) + " ― " + mats[0]
    else:                                             # 教材をまたぐ: 「紫：④ ／ 緑：③ → ④」の形にする
        groups = {}
        for s, p in zip(c.block, parts):
            groups.setdefault(MATERIAL[s.L], []).append(p[0])
        title = " ／ ".join(f"{m}：" + " → ".join(v) for m, v in groups.items())
    if len(parts) == 1:
        bullets = list(parts[0][1])
    else:
        bullets = [f"【{p[0]}】{b}" for p in parts for b in p[1]]
    done = " → ".join(p[2] for p in parts)
    if c.block[0].L > info.st.L and info.st.k > 0:
        bullets = [f"上位教材へ進む（{LEVELS[info.st.L]} → {LEVELS[c.block[0].L]}）"] + bullets
    if c.minutes < c.full_minutes:
        bullets.append(f"※ 全体で約{c.full_minutes}分。今日は約{c.minutes}分ぶん（区切りのいい所まで）")
    recs = "、".join(f"{LEVELS[s.L]}／{STEPS[s.k]}" for s in c.block)
    hint = (f"終わったら → サイドバーで『{info.name}』を記録：{recs}" if len(c.block) == 1
            else f"終わったら → サイドバーで『{info.name}』を、次の順に1ステップずつ記録：{recs}")
    return title, bullets, done, hint, diff


def _reasons(c: Cand, est):
    info, cur = c.info, c.info.st
    r = []
    if c.kind == "revenge":
        r.append("模試で失点した論点（同じ形で再び出やすい）")
    R = retention(cur.elapsed, cur.S)
    if cur.k > 0 and (R < 0.6 or c.kind == "review"):
        r.append(f"前回から{int(cur.elapsed)}日、記憶保持の推定 {R:.0%}")
    if c.kind == "learn" and cur.k == 0:
        r.append("未着手の論点（ここが入口）")
    lowest = min(est["p_cut"].values())
    worst = max(range(4), key=lambda j: info.pts[j] * est["p_cut"][SUBJECTS[j]])
    pw = est["p_cut"][SUBJECTS[worst]]
    if pw >= 0.3 and pw - lowest >= 0.15 and info.pts[worst] >= 0.8:      # 全科目が高いだけの時期は出さない
        r.append(f"{SUBJECT_LABEL[SUBJECTS[worst]]}の足切りリスク {pw:.0%}（他科目より高い）")
    if c.kind == "learn" and c.upside > max(1.0, c.gain * 2):
        r.append(f"ここから最大 +{c.upside:.1f}点の伸びしろ")
    if info.pts_eff >= 3.0:
        r.append(f"配点の大きい論点（推定{info.pts_eff:.1f}点ぶん）")
    if c.kind == "learn" and c.pace >= 1.4:
        r.append("大物論点：早めに着手して余裕を持たせる")
    return r[:3] or ["費用対効果が高い"]


@dataclass
class Session:
    topic: str
    category: str
    kind: str                    # learn / review / revenge / mock
    title: str
    level: str
    step_to_record: str
    minutes: int
    full_minutes: int
    gain: float
    per_hour: float
    upside: float = 0.0
    reasons: list = field(default_factory=list)
    instructions: list = field(default_factory=list)
    done_when: str = ""
    record_hint: str = ""
    difficulty: str = ""

    @property
    def partial(self):
        return self.minutes < self.full_minutes


@dataclass
class Plan:
    today: datetime.date
    days_left: int
    budget: int
    done_minutes: int
    sessions: list
    runners_up: list
    estimate: dict
    done_topics: list
    notes: list

    @property
    def planned_minutes(self):
        return sum(s.minutes for s in self.sessions)

    @property
    def total_gain(self):
        return sum(s.gain for s in self.sessions)


# =============================================================================
# 本試験形式の演習（時期が来たら）
# =============================================================================
def _mock_session(mocks, today, days_left, remaining, infos, est, notes):
    if days_left <= 2:
        return None                                   # 直前2日は模試より、復習と体調管理
    started = sum(1 for i in infos if i.st.k >= 3)
    coverage = started / max(1, len(infos))
    if coverage < 0.6 and days_left > 21:
        return None                                   # 基礎が固まる前の模試は費用対効果が低い
    last_date = max((_parse_date(m.get("date")) for m in mocks if _parse_date(m.get("date"))), default=None)
    last = mocks[-1] if mocks else None
    since = (today - last_date).days if last_date else 999
    interval = 14 if days_left > 45 else (7 if days_left > 21 else 4)
    if since < interval:
        return None
    if remaining < 120:
        notes.append("本試験形式の演習をやる時期ですが、今日は時間が足りません。まとまった時間が取れる日に回しましょう。")
        return None
    e = est["subject"]
    paper1, paper2 = e["comm"] + e["acct"], e["ind"] + e["cost"]
    if last:
        paper1, paper2 = paper1 + last.get("comm", 0) + last.get("acct", 0), paper2 + last.get("ind", 0) + last.get("cost", 0)
    pick = 0 if paper1 <= paper2 else 1
    name = "商業簿記・会計学" if pick == 0 else "工業簿記・原価計算"
    return Session(
        topic=f"本試験形式の演習（{name}）", category="模試", kind="mock",
        title="時間を計った通し演習 + 失点分析", level="", step_to_record="",
        minutes=120, full_minutes=120, gain=0.0, per_hour=0.0,
        reasons=[f"前回の模試から{since}日" if last_date else "初めての実力測定",
                 "点数と失点論点が、次回以降のプランの精度を上げる"],
        instructions=[f"90分タイマーで{name}を通しで解く（過去問・答練）",
                      "終了後30分：失点を「過信／知識不足」に分け、論点ごとに原因を1行メモ"],
        done_when="全問を時間内に最後まで解き、失点論点を洗い出せた",
        record_hint="終わったら → サイドバー『模試・答練スコア』に点数と失点論点を登録（該当論点が自動でリベンジ対象になります）",
    )


# =============================================================================
# 今日のプラン
# =============================================================================
def _log_minutes(lg, weights):
    w = weights.get(lg.get("topic"), DEFAULT_WEIGHTS.get(lg.get("topic"), 1.0))
    k = _step_idx(lg.get("step"))
    if k <= 0:
        return 20
    return min(90, full_minutes(w, _level_idx(lg.get("level")), k))


def build_plan(app_data, weights=None, daily_minutes=DEFAULT_MINUTES, today=None, exam_date=None) -> Plan:
    """今日のプランを作る。app_data はプロトタイプの st.session_state.app_data（読み取りのみ）"""
    today = today or datetime.date.today()
    weights = weights or DEFAULT_WEIGHTS
    days_left = ((exam_date or EXAM_DATE) - today).days
    H = float(max(1, min(HORIZON_DAYS, days_left)))
    notes = []
    if days_left <= 0:
        notes.append("試験日を過ぎています（EXAM_DATE を確認してください）。")

    infos = _build_infos(app_data, weights, today)
    mocks = app_data.get("mock_exams", []) or []
    rng = np.random.default_rng(today.toordinal())
    est = estimate_exam(infos, mocks, rng)

    # 今日すでに記録した分
    today_s = today.isoformat()
    todays = [lg for lg in (app_data.get("logs", []) or []) if lg.get("date") == today_s]
    done_topics = list(dict.fromkeys(lg.get("topic") for lg in todays))
    done_min = sum(_log_minutes(lg, weights) for lg in todays)
    remaining = max(0, int(daily_minutes) - done_min)

    max_look = max(120.0, max(1, days_left) * daily_minutes / 10.0)

    sessions_fixed = []
    mock = _mock_session(mocks, today, days_left, remaining, infos, est, notes)
    if mock:
        sessions_fixed.append(mock)
        remaining -= mock.minutes

    # 論点ごとに最良の候補を1つ選ぶ
    best = []
    for info in infos:
        if info.name in done_topics:
            continue
        cut_mult = 1.0 + CUT_WEIGHT * float(
            sum(info.pts[j] * est["p_cut"][SUBJECTS[j]] for j in range(4)) / max(info.pts.sum(), 1e-9))
        cands = _make_candidates(info, H, max_look, days_left, cut_mult)
        if cands:
            best.append(max(cands, key=lambda c: c.score))
    best.sort(key=lambda c: -c.score)

    max_main = 8                                           # 新規学習・リベンジの件数の上限
    max_reviews = max(3, int(remaining) // 40)             # 復習の件数の上限（期限切れが溜まっていても詰め込まない）
    review_cap = max(REVIEW_SHARE * max(remaining, 0), 15)  # 復習に使う時間の上限（短い日でも1〜2件は入れる）
    chosen, used, paper_used = [], 0, [0, 0]
    for strict in (True, False):
        for c in best:
            if any(c is x[0] for x in chosen):
                continue
            room = remaining - used
            if room < MIN_SESSION_MIN:
                break
            n_main = sum(1 for x in chosen if x[0].kind != "review")
            rev_min = sum(x[1] for x in chosen if x[0].kind == "review")
            if c.kind != "review" and n_main >= max_main:
                continue
            if c.kind == "revenge" and sum(1 for x in chosen if x[0].kind == "revenge") >= MAX_REVENGE:
                continue
            if c.kind == "review" and (rev_min + c.minutes > review_cap
                                       or sum(1 for x in chosen if x[0].kind == "review") >= max_reviews):
                continue
            minutes = c.minutes
            if minutes > room:
                if c.kind in ("learn", "revenge") and room >= 15:
                    minutes = int(room // 5 * 5)
                else:
                    continue
            if strict and paper_used[c.info.paper] + minutes > PAPER_CAP * max(remaining, 1):
                continue
            chosen.append((c, minutes))
            used += minutes
            paper_used[c.info.paper] += minutes

    sessions = []
    for c, minutes in chosen:
        title, bullets, done, hint, diff = _describe(c)
        frac = minutes / c.full_minutes if c.full_minutes else 1.0
        gain = c.gain * min(1.0, frac)
        sessions.append(Session(
            topic=c.info.name, category=c.info.category, kind=c.kind, title=title,
            level=LEVELS[c.L], step_to_record=STEPS[c.k], minutes=minutes, full_minutes=c.full_minutes,
            gain=gain, per_hour=gain / minutes * 60.0 if minutes else 0.0, upside=c.upside,
            reasons=_reasons(c, est), instructions=bullets, done_when=done, record_hint=hint, difficulty=diff,
        ))
    order = {"mock": 0, "review": 1, "revenge": 2, "learn": 3}
    sessions.sort(key=lambda s: order[s.kind])          # 復習(ウォームアップ) → リベンジ → 新規学習
    sessions = sessions_fixed + sessions

    rest = [c for c in best if not any(c is x[0] for x in chosen)][:6]
    runners = []
    for c in rest:
        title, *_ = _describe(c)
        runners.append({"topic": c.info.name, "title": title, "minutes": c.minutes,
                        "per_hour": c.gain / c.minutes * 60.0 if c.minutes else 0.0})

    backlog = sum(1 for c in best if c.kind == "review" and c.info.due and not any(c is x[0] for x in chosen))
    if backlog:
        notes.append(f"復習期限が来ている論点が他に{backlog}件あります。優先度の低いものは明日以降に回します。")
    if not sessions and remaining < MIN_SESSION_MIN:
        notes.append("今日の学習時間はすでに使い切っています。お疲れさまでした。")
    elif not sessions:
        notes.append("今日やる価値の高い候補がありません。過去問・答練で仕上げに入る時期です。")
    return Plan(today, days_left, int(daily_minutes), done_min, sessions, runners, est, done_topics, notes)


def sidebar_defaults(plan: Plan):
    """プロトタイプのサイドバー初期選択を、コーチの1位に揃えるための値"""
    for s in plan.sessions:
        if s.kind != "mock":
            return {"recommended_topic": s.topic, "recommended_category": s.category or None}
    return {}


# =============================================================================
# Streamlit UI
# =============================================================================
def get_daily_minutes(app_data, default=DEFAULT_MINUTES) -> int:
    """今日使える時間(分)。サイドバーより前で呼べるように session_state から読む"""
    stored = (app_data.get("coach") or {}).get("daily_minutes")
    st.session_state.setdefault("coach_minutes", min(480, max(60, int(stored or default))))
    return int(st.session_state["coach_minutes"])


def render_plan(plan: Plan, app_data=None, save_fn=None):

    def card():
        try:
            return st.container(border=True)
        except TypeError:          # 古い Streamlit
            return st.container()

    def _save_minutes():
        if app_data is not None:
            app_data.setdefault("coach", {})["daily_minutes"] = int(st.session_state["coach_minutes"])
            if save_fn:
                save_fn()

    e = plan.estimate
    p = e["p_pass"]
    p_txt = "5%未満" if p < 0.05 else f"{round(p * 20) * 5}%"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("本番まで", f"{plan.days_left}日")
    c2.metric("今日受けたら（推定）", f"{e['total']:.0f} / 100点")
    c3.metric("合格確率（目安）", p_txt)
    c4.number_input("今日使える時間（分）", min_value=30, max_value=720, step=15,
                    key="coach_minutes", on_change=_save_minutes)

    cols = st.columns(4)
    for col, s in zip(cols, SUBJECTS):
        risk = e["p_cut"][s]
        icon = "🔴" if risk >= 0.5 else ("🟡" if risk >= 0.2 else "🟢")
        col.metric(SUBJECT_LABEL[s], f"{e['subject'][s]:.1f} / 25", f"{icon} 足切りリスク {risk:.0%}", delta_color="off")
    if e["last_mock"]:
        m = e["last_mock"]
        st.caption(f"直近の模試（{m.get('name', '')}）: 合計{m.get('total', '-')}点 ／ "
                   f"商{m.get('comm', '-')} 会{m.get('acct', '-')} 工{m.get('ind', '-')} 原{m.get('cost', '-')}")

    st.subheader("🧭 今日のプラン")
    st.caption(f"{plan.planned_minutes}分 ／ 期待得点 +{plan.total_gain:.2f}点"
               + (f" ／ 記録済みの学習 約{plan.done_minutes}分を差し引き済み" if plan.done_minutes else ""))
    for n in plan.notes:
        st.info(n)

    icon = {"learn": "📘", "review": "🔁", "revenge": "🔥", "mock": "📝"}
    for i, s in enumerate(plan.sessions, 1):
        with card():
            a, b, c = st.columns([5, 1.2, 1.6])
            a.markdown(f"#### {icon[s.kind]} {i}. {s.topic}")
            a.markdown(f"**{s.title}**")
            b.metric("時間", f"{s.minutes}分")
            if s.kind == "mock":
                c.metric("目的", "実力測定")
            else:
                c.metric("期待得点", f"+{s.gain:.2f}点", f"{s.per_hour:.2f}点/時間", delta_color="off")
            st.caption("なぜ今日？ " + " ／ ".join(s.reasons))
            for line in s.instructions:
                st.markdown(f"- {line}")
            st.markdown(f"✅ **完了の目安**：{s.done_when}")
            st.caption(s.record_hint)

    if plan.done_topics:
        st.success("今日すでに記録した論点：" + "、".join(plan.done_topics))

    if plan.runners_up:
        with st.expander("次点の候補（今日は見送り）"):
            for r in plan.runners_up:
                st.markdown(f"- **{r['topic']}** ― {r['title']}（{r['minutes']}分・{r['per_hour']:.2f}点/時間）")

    with st.expander("このプランの前提（配点の仮置きを確認）"):
        st.markdown(
            "- 期待得点 = 配点 × 得点力（教材レベル×ステップ×できの質）× 記憶保持（stability から算出）\n"
            "- 「点/時間」は、その作業を成功した場合の期待得点の増分を、所要時間で割ったもの\n"
            "- 論点ごとの配点は `TOPIC_META`（出題頻度×科目配分）を科目25点に正規化した**仮置き**です。過去問に合わせて修正してください\n"
            "- 合格確率は「各科目4大問、出題は配点比で抽選」の簡易シミュレーションによる目安です")
        st.dataframe([{"論点": k, "出題頻度": v[0], **{SUBJECT_LABEL[s]: v[1].get(s, 0.0) for s in SUBJECTS}}
                      for k, v in TOPIC_META.items()], use_container_width=True)




# ==============================================================================
# 6. ヘッダー（5列カード表示）
# ==============================================================================
today = datetime.date.today()
days_left = (EXAM_DATE - today).days
engine_res = run_phase_aware_backprop_engine(app_data, today)

# --- 【追加】期待得点コーチ：今日のプランを作り、サイドバーの初期選択を1位に揃える
coach_plan = build_plan(
    app_data,
    weights=TOPIC_WORKLOAD_WEIGHTS,
    daily_minutes=get_daily_minutes(
        app_data, default=int(engine_res["daily_workload_quota"] * 30)
    ),
    today=today,
    exam_date=EXAM_DATE,
)
engine_res.update(sidebar_defaults(coach_plan))

green_mastered = sum(
    1
    for d in app_data["topics"].values()
    if "クレアドバンスト" in d.get("level", "")
    and d.get("status_quadrant") == "左上_得意できた"
)
due_topics_list = [
    t
    for t, d in app_data["topics"].items()
    if d.get("step") != "未着手"
    and d.get("next_date", today.isoformat()) <= today.isoformat()
]

total_progress = calculate_safe_progress(app_data["topics"])

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
  st.markdown(
      f"<div class='stat-card'><div style='font-size:11.5px;"
      " color:#94a3b8;'>🎯 本番 11/15 まで</div><div style='font-size:22px;"
      f" font-weight:bold; color:#f43f5e;'>残り {days_left} 日</div></div>",
      unsafe_allow_html=True,
  )
with c2:
  st.markdown(
      f"<div class='stat-card'><div style='font-size:11.5px; color:#94a3b8;'>👑"
      " 完全制覇 (緑・左上)</div><div style='font-size:22px; font-weight:bold;"
      f" color:#4ade80;'>{green_mastered} / {len(ALL_TOPICS)} 論点</div></div>",
      unsafe_allow_html=True,
  )
with c3:
  st.markdown(
      f"<div class='stat-card'><div style='font-size:11.5px; color:#94a3b8;'>🚨"
      " 本日復習 Due</div><div style='font-size:22px; font-weight:bold;"
      f" color:#fbbf24;'>{len(due_topics_list)} 論点</div></div>",
      unsafe_allow_html=True,
  )
with c4:
  st.markdown(
      f"<div class='stat-card'><div style='font-size:11.5px; color:#94a3b8;'>📊"
      " 本試験仕上がり率</div><div style='font-size:22px; font-weight:bold;"
      f" color:#a855f7;'>{total_progress:.1f} %</div></div>",
      unsafe_allow_html=True,
  )
with c5:
  st.markdown(
      f"<div class='stat-card'><div style='font-size:11.5px; color:#94a3b8;'>{engine_res['norma_subtext']}</div><div"
      " style='font-size:20px; font-weight:bold;"
      f" color:#38bdf8;'>{engine_res['norma_text']}</div></div>",
      unsafe_allow_html=True,
  )

st.write("")

# ==============================================================================
# 7. サイドバー（記録・復元）
# ==============================================================================
with st.sidebar:
  st.header("📝 学習・演習の記録")
  mode = st.radio(
      "記録の種類",
      [
          "📘 個別論点の記録 (問題解いたぞ!)",
          "🎯 模試・答練スコア (間違えたぞ!)",
      ],
  )

  if mode == "📘 個別論点の記録 (問題解いたぞ!)":
    rec_cat = engine_res["recommended_category"]
    rec_topic = engine_res["recommended_topic"]

    cat_keys = list(TOPICS_MASTER.keys())
    cat_default_idx = cat_keys.index(rec_cat) if rec_cat in cat_keys else 0
    sel_cat = st.selectbox("大項目", cat_keys, index=cat_default_idx)

    topic_options = TOPICS_MASTER[sel_cat]
    topic_default_idx = (
        topic_options.index(rec_topic) if rec_topic in topic_options else 0
    )
    sel_topic = st.selectbox("論点", topic_options, index=topic_default_idx)

    current_t = app_data["topics"].get(sel_topic, create_default_topic(sel_cat))
    current_lvl = current_t.get("level", "TAC入門 (赤)")
    cur_lvl_idx = (
        LEVELS_LIST.index(current_lvl) if current_lvl in LEVELS_LIST else 0
    )
    t_weight = TOPIC_WORKLOAD_WEIGHTS.get(sel_topic, 1.0)

    inp_level = st.selectbox(
        "今回解いた教材・レベル",
        LEVELS_LIST,
        index=cur_lvl_idx,
        key=f"level_{sel_topic}",
    )

    st.caption(
        f"現在の記録: **{current_lvl}** ｜ 進捗:"
        f" **{current_t.get('step', '未着手')}** ｜ 負荷重み: **×{t_weight}**"
    )

    cur_step = current_t.get("step", "未着手")
    default_idx = VALID_STEPS.index(cur_step) if cur_step in VALID_STEPS else 0
    inp_step = st.selectbox(
        "今回のアクション・ステップ",
        VALID_STEPS,
        index=default_idx,
        key=f"step_{sel_topic}",
    )

    col_res1, col_res2 = st.columns(2)
    with col_res1:
      inp_cleared = (
          st.radio(
              "結果", ["できた◎ (正解/時間内)", "できなかった△ (不正解/時間超過)"]
          )
          == "できた◎ (正解/時間内)"
      )
    with col_res2:
      inp_feeling = (
          st.radio(
              "手癖・自信",
              ["得意◎ (型確立/迷いなし)", "苦手△ (不安/モヤモヤ)"],
          )
          == "得意◎ (型確立/迷いなし)"
      )

    inp_memo = st.text_input("復習メモ（罠・注意点など）", value="")

    if st.button(
        "🚀 問題解いた！記録する", type="primary", use_container_width=True
    ):
      update_step_progress(
          sel_topic,
          inp_level,
          inp_step,
          inp_cleared,
          inp_feeling,
          inp_memo,
      )
      st.success(f"【{sel_topic}】（{inp_level}）の演習を記録しました！")
      st.rerun()

  else:
    st.subheader("🎯 模試・答練スコア登録")
    mock_name = st.text_input(
        "模試名/回", value=f"第{len(app_data['mock_exams'])+1}回 模試"
    )
    m_c1, m_c2 = st.columns(2)
    with m_c1:
      s_comm = st.number_input("商業簿記 (25点)", 0, 25, 18)
      s_ind = st.number_input("工業簿記 (25点)", 0, 25, 18)
    with m_c2:
      s_acct = st.number_input("会計学 (25点)", 0, 25, 18)
      s_cost = st.number_input("原価計算 (25点)", 0, 25, 18)

    st.markdown("**【失点論点の逆引き連携（自動降格）】**")
    careless_topics = st.multiselect(
        "⚠️ 過信失点（得意と思っていたのにミス ➔ 右上へ自動降格）", ALL_TOPICS
    )
    lack_topics = st.multiselect(
        "🔥 知識不足失点（解けなかった ➔ 右下へ自動降格）", ALL_TOPICS
    )

    if st.button(
        "📊 模試結果を保存して自動降格",
        type="primary",
        use_container_width=True,
    ):
      record_mock_exam(
          mock_name,
          s_comm,
          s_acct,
          s_ind,
          s_cost,
          careless_topics,
          lack_topics,
      )
      st.success(
          "模試結果を保存し、間違えた論点をマトリックスの要復習ゾーンへ自動降格させました！"
      )
      st.rerun()

  st.write("---")
  today_str = datetime.date.today().isoformat()
  json_str = json.dumps(st.session_state.app_data, ensure_ascii=False, indent=2)
  st.download_button(
      "📥 データをダウンロード保存",
      json_str.encode("utf-8"),
      f"boki1_data_backup_{today_str}.json",
      "application/json",
      use_container_width=True,
  )

  uploaded_file = st.file_uploader("📤 JSONをアップロードして復元", type=["json"])
  if uploaded_file is not None:
    try:
      content = uploaded_file.read().decode("utf-8")
      restored_data = json.loads(content)
      if isinstance(restored_data, dict) and "topics" in restored_data:
        st.session_state.app_data = sanitize_and_patch_data(restored_data)
        save_data()
        st.success("✅ 学習データを完全復元・更新しました！")
        st.rerun()
      else:
        st.error("⚠️ 無効なバックアップ形式です。")
    except Exception as e:
      st.error(f"読み込みエラー: {e}")

# ==============================================================================
# 8. メイン画面：6つのタブ（先頭に「今日のコーチ」を追加）
# ==============================================================================
tab_coach, tab_radar, tab_due, tab_matrix, tab_mock, tab_all = st.tabs([
    "🧭 今日のコーチ",
    "🕸️ 42論点バランス円グラフ",
    "🚨 本日の復習タスク",
    "🎯 4象限マトリックス",
    "📈 模試・答練スコア推移",
    "📋 全論点一覧",
])

# ------------------------------------------------------------------------------
# TAB COACH: 今日のコーチ（期待得点最大化プラン）
# ------------------------------------------------------------------------------
with tab_coach:
  _unmatched = [t for t in ALL_TOPICS if t not in TOPIC_META]
  if _unmatched:
    st.warning(
        "配点表 TOPIC_META に無い論点があります（仮の配点で計算中）: "
        + "、".join(_unmatched)
    )
  render_plan(coach_plan, app_data, save_fn=save_data)

# ------------------------------------------------------------------------------
# TAB 0: 42論点バランス円グラフ & 放置地雷注意喚起
# ------------------------------------------------------------------------------
with tab_radar:
  st.subheader("🎯 42論点 バランス・レーダー（死角・凸凹検出）")

  neglected_topics = []
  radar_labels = []
  radar_scores = []
  radar_cats = []

  for t_name in ALL_TOPICS:
    d = app_data["topics"].get(t_name, {})
    score = calculate_topic_single_score(d)
    w = TOPIC_WORKLOAD_WEIGHTS.get(t_name, 1.0)
    radar_labels.append(f"{t_name} (×{w})")
    radar_scores.append(score)
    cat_name = d.get("category") or TOPIC_TO_CAT_MAP.get(t_name, "")
    radar_cats.append(cat_name)

    last_d_str = d.get("last_date")
    days_since = (
        (today - datetime.date.fromisoformat(last_d_str)).days
        if last_d_str
        else 999
    )

    if score < 25.0 and days_since >= 10:
      neglected_topics.append({
          "topic": t_name,
          "category": cat_name,
          "score": score,
          "days": days_since,
          "weight": w,
      })

  if neglected_topics:
    st.markdown(
        f"""
        <div class='neglect-alert'>
            <div style='font-weight:bold; font-size:15px; margin-bottom:6px;'>
                ⚠️ 【死角・地雷アラート】 進捗が遅れており、長期間放置されている論点が {len(neglected_topics)} 件あります！
            </div>
            <div style='font-size:13px;'>
                基礎の未消化や長期間の未復習は、本試験で足切り（各科目10点未満）の原因になります。早めに「流し読み・例題」を1本回してください。
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    alert_cols = st.columns(3)
    for idx, item in enumerate(neglected_topics):
      with alert_cols[idx % 3]:
        days_label = (
            "未着手" if item["days"] == 999 else f"{item['days']}日間 放置"
        )
        st.error(
            f"**{item['topic']}** (重み: ×{item['weight']})\n[{item['category']}]"
            f" ｜ 進捗: **{item['score']}%** ｜ ⏱️ **{days_label}**"
        )
    st.markdown("---")
  else:
    st.success(
        "🎉 素晴らしい！10日以上放置されている危険な低進捗論点はありません。"
        " 全体がバランスよく循環しています。"
    )

  plot_labels = radar_labels + [radar_labels[0]]
  plot_scores = radar_scores + [radar_scores[0]]

  fig = go.Figure()
  fig.add_trace(
      go.Scatterpolar(
          r=plot_scores,
          theta=plot_labels,
          fill="toself",
          name="現在の仕上がり率",
          line=dict(color="#38bdf8", width=2),
          fillcolor="rgba(56, 189, 248, 0.25)",
      )
  )
  fig.add_trace(
      go.Scatterpolar(
          r=[75] * len(plot_labels),
          theta=plot_labels,
          name="合格安全ライン (75%)",
          line=dict(color="#34d399", width=1.5, dash="dash"),
          hoverinfo="skip",
      )
  )
  fig.add_trace(
      go.Scatterpolar(
          r=[25] * len(plot_labels),
          theta=plot_labels,
          name="入門完了ライン (25%)",
          line=dict(color="#f87171", width=1, dash="dot"),
          hoverinfo="skip",
      )
  )

  fig.update_layout(
      polar=dict(
          radialaxis=dict(
              visible=True,
              range=[0, 100],
              tickfont=dict(size=10, color="#94a3b8"),
              gridcolor="#334155",
          ),
          angularaxis=dict(
              tickfont=dict(size=9.5, color="#cbd5e1"),
              rotation=90,
              direction="clockwise",
              gridcolor="#334155",
          ),
          bgcolor="#0f172a",
      ),
      paper_bgcolor="#020617",
      margin=dict(l=60, r=60, t=30, b=40),
      showlegend=True,
      legend=dict(
          orientation="h",
          yanchor="bottom",
          y=-0.15,
          xanchor="center",
          x=0.5,
          font=dict(color="#cbd5e1"),
      ),
      height=720,
  )
  st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------------------
# TAB 1: 本日の復習タスク（HTMLコードブロック誤認識を完全防止）
# ------------------------------------------------------------------------------
with tab_due:
  st.subheader(f"📅 本日（{today}）やるべき論点タスク一覧")

  # 1. 直近5日間の商工バランス比率集計
  five_days_ago = (today - datetime.timedelta(days=5)).isoformat()
  recent_logs = [
      lg
      for lg in app_data.get("logs", [])
      if lg.get("date", "") >= five_days_ago
  ]

  comm_load = 0.0
  ind_load = 0.0
  for lg in recent_logs:
    t_name = lg.get("topic", "")
    w = TOPIC_WORKLOAD_WEIGHTS.get(t_name, 1.0)
    cat = app_data["topics"].get(t_name, {}).get(
        "category"
    ) or TOPIC_TO_CAT_MAP.get(t_name, "")
    if "工業" in cat:
      ind_load += w
    else:
      comm_load += w

  comm_bias = 0.0
  ind_bias = 0.0
  diff = comm_load - ind_load
  if diff >= 2.5:
    ind_bias = 35.0
  elif diff <= -2.5:
    comm_bias = 35.0

  col_s1, col_s2 = st.columns([1.5, 2])
  col_s1.caption(
      f"⚖️ 直近5日間の消化バランス: **商会 {round(comm_load, 1)} 枠** vs **工原"
      f" {round(ind_load, 1)} 枠**"
  )
  if ind_bias > 0:
    col_s2.info("⚖️ 工原の復習間隔が開いています（工原優先モード発動中）")
  elif comm_bias > 0:
    col_s2.info(
        "⚖️ 商業・会計の復習間隔が開いています（商会優先モード発動中）"
    )

  # 2. オススメ優先度スコア計算
  def calc_recommend_score(t_name):
    d = app_data["topics"].get(t_name, {})
    score = 0.0
    if d.get("caution_flag", False):
      score += 100.0
    if (
        d.get("step") != "未着手"
        and d.get("next_date", today.isoformat()) <= today.isoformat()
    ):
      score += 50.0
    last_d = d.get("last_date")
    days_since = (
        (today - datetime.date.fromisoformat(last_d)).days if last_d else 30
    )
    score += min(days_since * 2, 40)
    quad = d.get("status_quadrant", "")
    if "未達" in quad:
      score += 25.0
    elif "苦手" in quad:
      score += 15.0
    cat = d.get("category") or TOPIC_TO_CAT_MAP.get(t_name, "")
    score += ind_bias if "工業" in cat else comm_bias
    return score

  sorted_all = sorted(ALL_TOPICS, key=calc_recommend_score, reverse=True)
  target_quota = engine_res.get("daily_workload_quota", 5.0)

  # 今日の目標枠数に達するまでオススメセットを抽出
  recommended_set = set()
  rec_accum = 0.0
  for t in sorted_all:
    recommended_set.add(t)
    rec_accum += TOPIC_WORKLOAD_WEIGHTS.get(t, 1.0)
    if rec_accum >= target_quota:
      break

  st.markdown(
      f"<div style='background:rgba(56,189,248,0.1); border-left:4px solid"
      " #38bdf8; padding:8px 12px; border-radius:4px; margin-bottom:12px;"
      f" font-size:13px;'>🎯 <b>本日のおすすめセット（計 {round(rec_accum, 1)} /"
      f" {target_quota} 枠）</b>: 『🔥"
      " オススメ』がついている論点を消化すると本日のノルマをちょうど達成できます！</div>",
      unsafe_allow_html=True,
  )

  display_topics = [
      t
      for t in sorted_all
      if (
          t in recommended_set
          or (
              app_data["topics"].get(t, {}).get("step") != "未着手"
              and app_data["topics"].get(t, {}).get("next_date", today.isoformat())
              <= today.isoformat()
          )
          or app_data["topics"].get(t, {}).get("caution_flag", False)
      )
  ]

  if not display_topics:
    st.success(
        "🎉"
        " 本日復習すべき論点はすべて完了しています！未着手論点のインプットか、模試の演習に進みましょう。"
    )
  else:
    for t_name in display_topics:
      d = app_data["topics"].get(t_name, {})
      lvl = d.get("level", "TAC入門 (赤)")
      quad = d.get("status_quadrant", "右下_苦手未達")
      step = d.get("step", "未着手")
      rounds = d.get("round_count", 0)
      w = TOPIC_WORKLOAD_WEIGHTS.get(t_name, 1.0)
      cat = d.get("category") or TOPIC_TO_CAT_MAP.get(t_name, "")
      is_rec = t_name in recommended_set

      action_guide = get_topic_action_guide(d)
      lvl_color = (
          "#f87171"
          if "赤" in lvl
          else (
              "#60a5fa"
              if "青" in lvl
              else ("#c084fc" if "紫" in lvl else "#4ade80")
          )
      )

      card_class = "due-card-rec" if is_rec else "due-card"
      rec_tag = "<span class='rec-tag'>🔥 本日オススメ</span>" if is_rec else ""

      # 先頭のインデントを詰めることで、Markdownパーサーによるコードブロック誤変換を防止
      card_html = (
          f"<div class='{card_class}'>"
          "<div style='display:flex; justify-content:space-between;"
          " align-items:center;'>"
          "<div>"
          f"<span style='color:{lvl_color}; font-weight:bold;"
          f" font-size:16px;'>{t_name}</span>"
          f"<span class='weight-tag'>負荷 ×{w}</span>"
          f"{rec_tag}"
          "<span style='font-size:12px; color:#94a3b8;"
          f" margin-left:8px;'>[{cat}] ｜ {lvl} ｜ 進捗: {step} (累計 {rounds}周)</span>"
          "</div>"
          "<div>"
          "<span style='font-size:12px; background:#334155; padding:3px 8px;"
          f" border-radius:4px; color:#fbbf24;'>状態: {quad}</span>"
          "</div>"
          "</div>"
          "<div class='due-action'>"
          f"👉 <b>やるべきこと：</b> {action_guide}"
          "</div>"
          "</div>"
      )
      st.markdown(card_html, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# TAB 2: 4象限マトリックス
# ------------------------------------------------------------------------------
with tab_matrix:
  st.markdown(
      """
    **【教材レベル分類】** <span class='badge-red' style='display:inline;'>■ 赤: TAC入門</span> ➔ 
    <span class='badge-blue' style='display:inline;'>■ 青: TAC詳細</span> ➔ 
    <span class='badge-purple' style='display:inline;'>■ 紫: ALFA演習</span> ➔ 
    <span class='badge-green' style='display:inline;'>■ 緑: クレADV (★完全制覇)</span>
    """,
      unsafe_allow_html=True,
  )

  q_data = {
      "左上_得意できた": [],
      "右上_得意未達": [],
      "左下_苦手できた": [],
      "右下_苦手未達": [],
  }

  for t_name, d in app_data["topics"].items():
    lvl_key = LEVEL_KEY_MAP.get(d.get("level", "TAC入門 (赤)"), "red")
    w = TOPIC_WORKLOAD_WEIGHTS.get(t_name, 1.0)

    c_cnt = d.get("careless_count", 0)
    l_cnt = d.get("lack_count", 0)
    miss_tag = f" 🚨×{c_cnt}" if c_cnt > 0 else ""
    if l_cnt > 0:
      miss_tag += f" 🔥×{l_cnt}"

    step_label = d.get("step", "未着手")
    rounds = (
        f" ({d.get('round_count', 0)}周)"
        if d.get("round_count", 0) > 0
        else ""
    )
    text = (
        f"• {t_name} <span class='weight-tag'>×{w}</span> <span"
        f" class='step-tag'>{step_label}{rounds}</span>{miss_tag}"
    )
    badge_html = f"<span class='badge-{lvl_key}'>{text}</span>"

    q_pos = d.get("status_quadrant", "右下_苦手未達")
    if q_pos in q_data:
      q_data[q_pos].append(badge_html)
    else:
      q_data["右下_苦手未達"].append(badge_html)

  m_col_left, m_col_right = st.columns(2)

  with m_col_left:
    st.markdown(
        "<div style='text-align:center; font-weight:bold; color:#4ade80;"
        " margin-bottom:4px;'>【 できた（正解 / 時間内クリア）】</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='matrix-box'><div class='matrix-header'"
        " style='color:#34d399;'>🏆 得意 × できた（順調・完全制覇ゾーン）</div>"
        + (
            "".join(q_data["左上_得意できた"])
            if q_data["左上_得意できた"]
            else "<span style='color:#64748b;'>なし</span>"
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='matrix-box'><div class='matrix-header'"
        " style='color:#38bdf8;'>🧗 苦手 × できた（手順正解・型習得ゾーン）</div>"
        + (
            "".join(q_data["左下_苦手できた"])
            if q_data["左下_苦手できた"]
            else "<span style='color:#64748b;'>なし</span>"
        )
        + "</div>",
        unsafe_allow_html=True,
    )

  with m_col_right:
    st.markdown(
        "<div style='text-align:center; font-weight:bold; color:#f87171;"
        " margin-bottom:4px;'>【 できなかった / 未読・未達 】</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='matrix-box'><div class='matrix-header'"
        " style='color:#fbbf24;'>⚠️ 得意 ×"
        " 未達（過信・模試失点で自動降格ゾーン）</div>"
        + (
            "".join(q_data["右上_得意未達"])
            if q_data["右上_得意未達"]
            else "<span style='color:#64748b;'>なし</span>"
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div class='matrix-box'><div class='matrix-header'"
        " style='color:#f87171;'>🔥 苦手 × 未達（流し読み・要特訓ゾーン）</div>"
        + (
            "".join(q_data["右下_苦手未達"])
            if q_data["右下_苦手未達"]
            else "<span style='color:#64748b;'>なし</span>"
        )
        + "</div>",
        unsafe_allow_html=True,
    )

# ------------------------------------------------------------------------------
# TAB 3: 模試推移
# ------------------------------------------------------------------------------
with tab_mock:
  if app_data["mock_exams"]:
    df_mock = pd.DataFrame(app_data["mock_exams"])
    st.subheader("📊 総合得点推移（合格ライン: 70点 ＆ 各科目10点以上）")
    st.line_chart(
        df_mock.set_index("name")[["total", "comm", "acct", "ind", "cost"]]
    )

    disp_df = df_mock.copy()
    disp_df["判定"] = disp_df.apply(
        lambda r: (
            "🎉 合格"
            if r.get("passed", False)
            else ("⚠️ 足切り" if r.get("has_cutoff", False) else "不合格")
        ),
        axis=1,
    )
    st.dataframe(
        disp_df[[
            "date",
            "name",
            "total",
            "判定",
            "comm",
            "acct",
            "ind",
            "cost",
            "careless_miss",
            "lack_miss",
        ]],
        use_container_width=True,
    )
  else:
    st.info(
        "サイドバーから模試・答練の結果を登録すると、ここに科目別推移グラフが表示されます。"
    )

# ------------------------------------------------------------------------------
# TAB 4: 全論点一覧（負荷重み・実質工数確認）
# ------------------------------------------------------------------------------
with tab_all:
  table_rows = []
  for t_name, d in app_data["topics"].items():
    is_due = (
        d.get("step") != "未着手"
        and d.get("next_date", today.isoformat()) <= today.isoformat()
    )
    w = TOPIC_WORKLOAD_WEIGHTS.get(t_name, 1.0)
    cat = d.get("category") or TOPIC_TO_CAT_MAP.get(t_name, "-")
    table_rows.append({
        "論点名": t_name,
        "大項目": cat,
        "負荷重み": f"×{w}",
        "教材レベル": d.get("level", "TAC入門 (赤)"),
        "進捗ステップ": d.get("step", "未着手"),
        "累計周回": f"{d.get('round_count', 0)}周",
        "仕上がりスコア": f"{calculate_topic_single_score(d)}%",
        "4象限状態": d.get("status_quadrant", "右下_苦手未達"),
        "次回復習日": d.get("next_date", "-"),
        "Due状態": (
            "🚨 今日復習！"
            if is_due
            else ("未着手" if d.get("step") == "未着手" else "順調")
        ),
        "やるべきアクション": get_topic_action_guide(d),
    })
  df_table = pd.DataFrame(table_rows)
  st.dataframe(df_table, use_container_width=True)
