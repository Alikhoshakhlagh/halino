from rest_framework import serializers

from accounts.models import City
from content.models import Category, Item, Occasion
from journey.models import Mood, Question, QuestionOption


class MoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mood
        fields = ["id", "name", "face", "valence"]


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ["id", "name", "is_supported"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "is_serial", "needs_city"]


class ItemSerializer(serializers.ModelSerializer):
    category = CategorySerializer()
    city = serializers.CharField(source="city.name", default="")

    class Meta:
        model = Item
        fields = [
            "id",
            "title",
            "subtitle",
            "description",
            "image_url",
            "external_url",
            "duration_minutes",
            "category",
            "city",
        ]


class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ["id", "text"]


class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True)

    class Meta:
        model = Question
        fields = ["id", "text", "kind", "allows_other", "options"]


class OccasionSerializer(serializers.ModelSerializer):
    source_label = serializers.CharField(source="get_source_display")

    class Meta:
        model = Occasion
        fields = ["title", "quote", "quote_author", "source", "source_label"]
