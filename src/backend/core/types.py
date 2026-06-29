from sqlalchemy import Numeric

# SQLAlchemy column types for money and rates.
# The Postgres DOMAIN declarations (money_amount, percentage_rate) are created
# in the v1_domains_and_lookups migration; these are the Python-level equivalents.
MoneyAmount = Numeric(14, 2)
PercentageRate = Numeric(6, 4)
