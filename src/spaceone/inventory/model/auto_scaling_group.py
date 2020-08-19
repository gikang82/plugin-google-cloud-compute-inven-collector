from schematics import Model
from schematics.types import StringType, ModelType


# class LaunchConfiguration(Model):
#     name = StringType()
#
#
# class LaunchTemplate(Model):
#     launch_template_id = StringType(deserialize_from='LaunchTemplateId')
#     name = StringType(deserialize_from='LaunchTemplateName')
#     version = StringType(deserialize_from='Version')


class AutoScalers(Model):
    name = StringType()
    launch_configuration = ModelType(LaunchConfiguration, serialize_when_none=False)
    launch_template = ModelType(LaunchTemplate, serialize_when_none=False)
