from rest_framework import serializers
from datetime import date

class CompanyResearchQuerySerializer(serializers.Serializer):
    ticker = serializers.CharField(
        max_length=20,
        required=True,
    )

    market = serializers.ChoiceField(
        choices=["US", "IN"],
        required=True,
    )
    
    
class IndiaOnlyResearchQuerySerializer(
    CompanyResearchQuerySerializer
):
    market = serializers.ChoiceField(
        choices=["IN"],
        required=True,
    )

    
class HistoricalResearchQuerySerializer(
    IndiaOnlyResearchQuerySerializer
):
    to_date = serializers.DateField(
        required=True,
        input_formats=["%Y-%m-%d"],
    )

    from_date = serializers.DateField(
        required=False,
        input_formats=["%Y-%m-%d"],
        allow_null=True,
    )

    def validate(self, attrs):
        from_date = attrs.get("from_date")
        to_date = attrs["to_date"]
        today = date.today()

        if to_date > today:
            raise serializers.ValidationError(
                {
                    "to_date": "to_date cannot be in the future."
                }
            )

        if from_date and from_date > today:
            raise serializers.ValidationError(
                {
                    "from_date": "from_date cannot be in the future."
                }
            )

        if from_date and from_date > to_date:
            raise serializers.ValidationError(
                {
                    "from_date": (
                        "from_date must be before or equal to to_date."
                    )
                }
            )

        return attrs
    
