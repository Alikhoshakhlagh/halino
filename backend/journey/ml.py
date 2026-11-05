"""
یک مدل یادگیری ماشین بسیار ساده: Naive Bayes چندجمله‌ای به‌ازای هر کاربر، پایتون خالص.

- داده‌ی آموزش: ردیف‌های UserItemStatus همان کاربر (که apply_feedback می‌نویسد).
  کلاس like = «انجام دادم» / «شروع کردم»؛ کلاس dislike = «نمی‌خوام».
- «کلمات» هر نمونه: تگ‌های آیتم (با شمارش = وزن تگ ۱..۵) + توکن مودِ روزِ بازخورد
  (mood:<id>) اگر آن روز مودی ثبت شده باشد.
- خروجی: P(like | tags, mood) با هموارسازی لاپلاس.
- فقط برای بازچینش بخش «متناسب با حالت»: امتیاز قاعده‌محور × احتمال مدل.
- با کمتر از MIN_ROWS رکورد بازخورد (یا وقتی فقط یک کلاس دیده شده) مدل غیرفعال
  است و ترتیب قاعده‌محور خالص می‌ماند. آموزش تنبل، در همان درخواست.
"""

import math

from content.models import ItemTag

from .models import MoodEntry, UserItemStatus

MIN_ROWS = 10
ALPHA = 1.0  # هموارسازی لاپلاس
LIKE, DISLIKE = "like", "dislike"
POSITIVE = {UserItemStatus.DONE, UserItemStatus.IN_PROGRESS}
NEGATIVE = {UserItemStatus.SKIPPED}


def tokens(tag_weights, mood):
    """{token: count} — تگ‌ها با وزنشان، مود به‌عنوان یک توکن جدا."""
    bag = {f"t{tag_id}": float(weight) for tag_id, weight in tag_weights.items()}
    if mood is not None:
        bag[f"mood:{mood.id}"] = 1.0
    return bag


def training_rows(user):
    """[(bag, class)] برای هر بازخورد قطعی کاربر."""
    statuses = list(
        UserItemStatus.objects.filter(
            user=user, status__in=list(POSITIVE | NEGATIVE)
        ).select_related("item")
    )
    if not statuses:
        return []

    tag_map = {}
    for item_tag in ItemTag.objects.filter(item_id__in=[s.item_id for s in statuses]):
        tag_map.setdefault(item_tag.item_id, {})[item_tag.tag_id] = item_tag.weight

    days = {s.updated_at.date() for s in statuses}
    moods_by_day = {
        entry.date: entry.mood
        for entry in MoodEntry.objects.filter(user=user, date__in=days).select_related("mood")
    }

    return [
        (
            tokens(tag_map.get(s.item_id, {}), moods_by_day.get(s.updated_at.date())),
            LIKE if s.status in POSITIVE else DISLIKE,
        )
        for s in statuses
    ]


class NaiveBayes:
    """Multinomial NB روی شمارش توکن‌ها؛ فقط جمع و لگاریتم."""

    def __init__(self, rows):
        self.class_count = {LIKE: 0, DISLIKE: 0}
        self.token_count = {LIKE: {}, DISLIKE: {}}
        self.total = {LIKE: 0.0, DISLIKE: 0.0}
        vocab = set()
        for bag, label in rows:
            self.class_count[label] += 1
            for token, count in bag.items():
                vocab.add(token)
                self.token_count[label][token] = self.token_count[label].get(token, 0.0) + count
                self.total[label] += count
        self.vocab_size = max(len(vocab), 1)
        self.n = len(rows)

    def _log_likelihood(self, bag, label):
        # log P(label) + Σ count·log P(token | label)
        score = math.log((self.class_count[label] + ALPHA) / (self.n + 2 * ALPHA))
        denom = self.total[label] + ALPHA * self.vocab_size
        for token, count in bag.items():
            score += count * math.log((self.token_count[label].get(token, 0.0) + ALPHA) / denom)
        return score

    def p_like(self, bag):
        like = self._log_likelihood(bag, LIKE)
        dislike = self._log_likelihood(bag, DISLIKE)
        m = max(like, dislike)
        return math.exp(like - m) / (math.exp(like - m) + math.exp(dislike - m))


def reranker(user, mood):
    """
    اگر داده کافی باشد تابعی برمی‌گرداند که فهرست امتیازخورده‌ی موتور
    [(score, item), ...] را دوباره مرتب می‌کند؛ وگرنه None.
    امتیاز نهایی = امتیاز قاعده‌محور × P(like) — مدل فقط ترتیب را عوض می‌کند.
    """
    rows = training_rows(user)
    if len(rows) < MIN_ROWS or len({label for _, label in rows}) < 2:
        return None
    model = NaiveBayes(rows)

    def rerank(scored):
        item_ids = [item.id for _, item in scored]
        tag_map = {}
        for item_tag in ItemTag.objects.filter(item_id__in=item_ids):
            tag_map.setdefault(item_tag.item_id, {})[item_tag.tag_id] = item_tag.weight
        adjusted = [
            (score * model.p_like(tokens(tag_map.get(item.id, {}), mood)), item)
            for score, item in scored
        ]
        adjusted.sort(key=lambda pair: pair[0], reverse=True)
        return adjusted

    return rerank
