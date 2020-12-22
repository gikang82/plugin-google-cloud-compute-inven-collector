from schematics import Model
from schematics.types import ModelType, StringType, BooleanType, ListType


class Labels(Model):
    key = StringType()
    value = StringType()


class Scheduling(Model):
    on_host_maintenance = StringType(default="MIGRATE")
    automatic_restart = BooleanType(default=True)
    preemptible = BooleanType(default=False)


class GoogleCloud(Model):
    self_link = StringType()
    fingerprint = StringType()
    reservation_affinity = StringType(default="ANY_RESERVATION")
    deletion_protection = BooleanType(default=False)
    scheduling = ModelType(Scheduling)
    labels = ListType(ModelType(Labels), default=[])
    tags = ListType(ModelType(Labels), default=[])
