from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from content.models import Category, Item
from journey import engine
from journey.models import UserItemStatus

from ..serializers import CategorySerializer, ItemSerializer

ACTIONS = {
    "done": UserItemStatus.DONE,
    "skip": UserItemStatus.SKIPPED,
    "progress": UserItemStatus.IN_PROGRESS,
    "reset": UserItemStatus.NOT_STARTED,
}


@api_view(["GET"])
def category_list_view(request):
    categories = Category.objects.all()
    if not request.user.can_see_places:
        categories = categories.filter(needs_city=False)
    categories = categories.annotate(count=Count("items")).order_by("order", "name")

    data = []
    for category in categories:
        row = CategorySerializer(category).data
        row["count"] = category.count
        data.append(row)
    return Response({"categories": data, "can_see_places": request.user.can_see_places})


@api_view(["GET"])
def category_detail_view(request, slug):
    category = get_object_or_404(Category, slug=slug)
    if category.needs_city and not request.user.can_see_places:
        raise Http404

    items = Item.objects.filter(category=category, is_active=True).select_related(
        "category", "city"
    )
    if category.needs_city:
        items = items.filter(city=request.user.city)

    statuses = {
        row.item_id: row
        for row in UserItemStatus.objects.filter(user=request.user, item__in=items)
    }

    rows = []
    for item in items[:300]:
        row = ItemSerializer(item).data
        status = statuses.get(item.id)
        row["status_label"] = status.get_status_display() if status else ""
        rows.append(row)
    return Response({"category": CategorySerializer(category).data, "items": rows})


@api_view(["GET"])
def item_detail_view(request, pk):
    item = get_object_or_404(Item.objects.select_related("category", "city"), pk=pk)
    status = UserItemStatus.objects.filter(user=request.user, item=item).first()
    data = ItemSerializer(item).data
    data["status_label"] = status.get_status_display() if status else ""
    data["tags"] = [tag.name for tag in item.tags.order_by("-itemtag__weight", "name")[:4]]
    return Response(data)


@api_view(["POST"])
def item_action_view(request, pk):
    item = get_object_or_404(Item.objects.select_related("category"), pk=pk)
    action = request.data.get("action")
    if action not in ACTIONS:
        return Response({"detail": "اکشن نامعتبر"}, status=400)

    status = ACTIONS[action]
    if status == UserItemStatus.IN_PROGRESS and not item.category.is_serial:
        return Response({"detail": "این دسته وضعیت «در حال انجام» ندارد."}, status=400)

    rating = str(request.data.get("rating") or "")
    engine.apply_feedback(
        request.user, item, status, rating=int(rating) if rating.isdigit() else None
    )
    return Response({"detail": "ثبت شد."})
