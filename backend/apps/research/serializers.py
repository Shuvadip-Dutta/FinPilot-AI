from rest_framework import serializers


class CompanyResearchQuerySerializer(serializers.Serializer):
    ticker = serializers.CharField(
        max_length=20,
        required=True,
    )

    market = serializers.ChoiceField(
        choices=["US", "IN"],
        required=True,
    )