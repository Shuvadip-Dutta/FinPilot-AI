from django.db import models


class Company(models.Model):
    ticker = models.CharField(max_length=20)
    name = models.CharField(max_length=255)

    isin = models.CharField(
        max_length=12,
        blank=True,
        null=True,
        unique=True,
    )

    exchange = models.CharField(max_length=50)
    country = models.CharField(max_length=50)

    sector = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    industry = models.CharField(
        max_length=150,
        blank=True,
        null=True,
    )

    sec_cik = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        unique=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["ticker"]
        constraints = [
            models.UniqueConstraint(
                fields=["ticker", "exchange"],
                name="unique_ticker_exchange",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.ticker})"