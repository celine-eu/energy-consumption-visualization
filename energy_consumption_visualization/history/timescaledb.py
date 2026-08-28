from peewee import (
    AutoField,
    CharField,
    DatabaseProxy,
    DateTimeField,
    FloatField,
    IntegerField,
    Model,
    TextField,
)
from playhouse.postgres_ext import BinaryJSONField

DB_PROXY = DatabaseProxy()

class BaseModel(Model):
    class Meta:
        database = DB_PROXY
        schema = "public"


class DataPoint(BaseModel):
    id = AutoField()
    name = CharField(max_length=128)
    location_code = CharField(max_length=128)
    device_id = CharField(max_length=128)
    data_provider = CharField(max_length=128)
    unit = TextField(null=True)

    class Meta:
        table_name = "data_points"


class UnitemporalDoubleDetails(BaseModel):
    dp_id = IntegerField()
    valid_time = DateTimeField()
    value = FloatField(null=True)

    class Meta:
        table_name = "unitemporal_double_details"
        primary_key = False


class UnitemporalJsonbDetails(BaseModel):
    dp_id = IntegerField()
    valid_time = DateTimeField()
    value = BinaryJSONField(null=True)

    class Meta:
        table_name = "unitemporal_jsonb_details"
        primary_key = False
