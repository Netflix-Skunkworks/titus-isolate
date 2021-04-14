# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: isolate.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='isolate.proto',
  package='isolation.v1',
  syntax='proto3',
  serialized_options=b'Z\014isolation/v1',
  create_key=_descriptor._internal_create_key,
  serialized_pb=b'\n\risolate.proto\x12\x0cisolation.v1\"&\n\x06Thread\x12\n\n\x02id\x18\x01 \x01(\r\x12\x10\n\x08task_ids\x18\x02 \x03(\t\"9\n\x04\x43ore\x12\n\n\x02id\x18\x01 \x01(\r\x12%\n\x07threads\x18\x02 \x03(\x0b\x32\x14.isolation.v1.Thread\"K\n\x07Package\x12\n\n\x02id\x18\x01 \x01(\r\x12\x11\n\tnum_cores\x18\x02 \x01(\r\x12!\n\x05\x63ores\x18\x03 \x03(\x0b\x32\x12.isolation.v1.Core\"K\n\x06Layout\x12\x18\n\x10threads_per_core\x18\x01 \x01(\r\x12\'\n\x08packages\x18\x02 \x03(\x0b\x32\x15.isolation.v1.Package\"\x8d\x01\n\x0fInstanceContext\x12\x13\n\x0binstance_id\x18\x01 \x01(\t\x12\r\n\x05stack\x18\x02 \x01(\t\x12\x0f\n\x07\x63luster\x18\x03 \x01(\t\x12\x17\n\x0f\x61utoscale_group\x18\x04 \x01(\t\x12\x15\n\rresource_pool\x18\x05 \x01(\t\x12\x15\n\rinstance_type\x18\x06 \x01(\t\"\xa7\x04\n\x10PlacementRequest\x12$\n\x06layout\x18\x01 \x01(\x0b\x32\x14.isolation.v1.Layout\x12\x16\n\x0etasks_to_place\x18\x02 \x03(\t\x12G\n\x0etask_to_job_id\x18\x03 \x03(\x0b\x32/.isolation.v1.PlacementRequest.TaskToJobIdEntry\x12W\n\x16task_to_job_descriptor\x18\x04 \x03(\x0b\x32\x37.isolation.v1.PlacementRequest.TaskToJobDescriptorEntry\x12\x19\n\x11\x64\x65sired_policy_id\x18\x05 \x01(\t\x12\x37\n\x10instance_context\x18\x06 \x01(\x0b\x32\x1d.isolation.v1.InstanceContext\x12>\n\x08metadata\x18\x07 \x03(\x0b\x32,.isolation.v1.PlacementRequest.MetadataEntry\x1a\x32\n\x10TaskToJobIdEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\x1a:\n\x18TaskToJobDescriptorEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\x0c:\x02\x38\x01\x1a/\n\rMetadataEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\" \n\nAssignment\x12\x12\n\nthread_ids\x18\x01 \x03(\r\"\xcb\x02\n\x11PlacementResponse\x12\x45\n\x0b\x61ssignments\x18\x01 \x03(\x0b\x32\x30.isolation.v1.PlacementResponse.AssignmentsEntry\x12\x11\n\tpolicy_id\x18\x02 \x01(\t\x12\x1c\n\x14policy_model_version\x18\x03 \x01(\t\x12?\n\x08metadata\x18\x04 \x03(\x0b\x32-.isolation.v1.PlacementResponse.MetadataEntry\x1aL\n\x10\x41ssignmentsEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\'\n\x05value\x18\x02 \x01(\x0b\x32\x18.isolation.v1.Assignment:\x02\x38\x01\x1a/\n\rMetadataEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\x32i\n\x10IsolationService\x12U\n\x10\x43omputePlacement\x12\x1e.isolation.v1.PlacementRequest\x1a\x1f.isolation.v1.PlacementResponse\"\x00\x42\x0eZ\x0cisolation/v1b\x06proto3'
)




_THREAD = _descriptor.Descriptor(
  name='Thread',
  full_name='isolation.v1.Thread',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='id', full_name='isolation.v1.Thread.id', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='task_ids', full_name='isolation.v1.Thread.task_ids', index=1,
      number=2, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=31,
  serialized_end=69,
)


_CORE = _descriptor.Descriptor(
  name='Core',
  full_name='isolation.v1.Core',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='id', full_name='isolation.v1.Core.id', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='threads', full_name='isolation.v1.Core.threads', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=71,
  serialized_end=128,
)


_PACKAGE = _descriptor.Descriptor(
  name='Package',
  full_name='isolation.v1.Package',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='id', full_name='isolation.v1.Package.id', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='num_cores', full_name='isolation.v1.Package.num_cores', index=1,
      number=2, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='cores', full_name='isolation.v1.Package.cores', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=130,
  serialized_end=205,
)


_LAYOUT = _descriptor.Descriptor(
  name='Layout',
  full_name='isolation.v1.Layout',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='threads_per_core', full_name='isolation.v1.Layout.threads_per_core', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='packages', full_name='isolation.v1.Layout.packages', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=207,
  serialized_end=282,
)


_INSTANCECONTEXT = _descriptor.Descriptor(
  name='InstanceContext',
  full_name='isolation.v1.InstanceContext',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='instance_id', full_name='isolation.v1.InstanceContext.instance_id', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='stack', full_name='isolation.v1.InstanceContext.stack', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='cluster', full_name='isolation.v1.InstanceContext.cluster', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='autoscale_group', full_name='isolation.v1.InstanceContext.autoscale_group', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='resource_pool', full_name='isolation.v1.InstanceContext.resource_pool', index=4,
      number=5, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='instance_type', full_name='isolation.v1.InstanceContext.instance_type', index=5,
      number=6, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=285,
  serialized_end=426,
)


_PLACEMENTREQUEST_TASKTOJOBIDENTRY = _descriptor.Descriptor(
  name='TaskToJobIdEntry',
  full_name='isolation.v1.PlacementRequest.TaskToJobIdEntry',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='isolation.v1.PlacementRequest.TaskToJobIdEntry.key', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='value', full_name='isolation.v1.PlacementRequest.TaskToJobIdEntry.value', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=b'8\001',
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=821,
  serialized_end=871,
)

_PLACEMENTREQUEST_TASKTOJOBDESCRIPTORENTRY = _descriptor.Descriptor(
  name='TaskToJobDescriptorEntry',
  full_name='isolation.v1.PlacementRequest.TaskToJobDescriptorEntry',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='isolation.v1.PlacementRequest.TaskToJobDescriptorEntry.key', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='value', full_name='isolation.v1.PlacementRequest.TaskToJobDescriptorEntry.value', index=1,
      number=2, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=b"",
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=b'8\001',
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=873,
  serialized_end=931,
)

_PLACEMENTREQUEST_METADATAENTRY = _descriptor.Descriptor(
  name='MetadataEntry',
  full_name='isolation.v1.PlacementRequest.MetadataEntry',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='isolation.v1.PlacementRequest.MetadataEntry.key', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='value', full_name='isolation.v1.PlacementRequest.MetadataEntry.value', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=b'8\001',
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=933,
  serialized_end=980,
)

_PLACEMENTREQUEST = _descriptor.Descriptor(
  name='PlacementRequest',
  full_name='isolation.v1.PlacementRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='layout', full_name='isolation.v1.PlacementRequest.layout', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='tasks_to_place', full_name='isolation.v1.PlacementRequest.tasks_to_place', index=1,
      number=2, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='task_to_job_id', full_name='isolation.v1.PlacementRequest.task_to_job_id', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='task_to_job_descriptor', full_name='isolation.v1.PlacementRequest.task_to_job_descriptor', index=3,
      number=4, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='desired_policy_id', full_name='isolation.v1.PlacementRequest.desired_policy_id', index=4,
      number=5, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='instance_context', full_name='isolation.v1.PlacementRequest.instance_context', index=5,
      number=6, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='metadata', full_name='isolation.v1.PlacementRequest.metadata', index=6,
      number=7, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[_PLACEMENTREQUEST_TASKTOJOBIDENTRY, _PLACEMENTREQUEST_TASKTOJOBDESCRIPTORENTRY, _PLACEMENTREQUEST_METADATAENTRY, ],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=429,
  serialized_end=980,
)


_ASSIGNMENT = _descriptor.Descriptor(
  name='Assignment',
  full_name='isolation.v1.Assignment',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='thread_ids', full_name='isolation.v1.Assignment.thread_ids', index=0,
      number=1, type=13, cpp_type=3, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=982,
  serialized_end=1014,
)


_PLACEMENTRESPONSE_ASSIGNMENTSENTRY = _descriptor.Descriptor(
  name='AssignmentsEntry',
  full_name='isolation.v1.PlacementResponse.AssignmentsEntry',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='isolation.v1.PlacementResponse.AssignmentsEntry.key', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='value', full_name='isolation.v1.PlacementResponse.AssignmentsEntry.value', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=b'8\001',
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=1223,
  serialized_end=1299,
)

_PLACEMENTRESPONSE_METADATAENTRY = _descriptor.Descriptor(
  name='MetadataEntry',
  full_name='isolation.v1.PlacementResponse.MetadataEntry',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='key', full_name='isolation.v1.PlacementResponse.MetadataEntry.key', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='value', full_name='isolation.v1.PlacementResponse.MetadataEntry.value', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=b'8\001',
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=933,
  serialized_end=980,
)

_PLACEMENTRESPONSE = _descriptor.Descriptor(
  name='PlacementResponse',
  full_name='isolation.v1.PlacementResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='assignments', full_name='isolation.v1.PlacementResponse.assignments', index=0,
      number=1, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='policy_id', full_name='isolation.v1.PlacementResponse.policy_id', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='policy_model_version', full_name='isolation.v1.PlacementResponse.policy_model_version', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='metadata', full_name='isolation.v1.PlacementResponse.metadata', index=3,
      number=4, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[_PLACEMENTRESPONSE_ASSIGNMENTSENTRY, _PLACEMENTRESPONSE_METADATAENTRY, ],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=1017,
  serialized_end=1348,
)

_CORE.fields_by_name['threads'].message_type = _THREAD
_PACKAGE.fields_by_name['cores'].message_type = _CORE
_LAYOUT.fields_by_name['packages'].message_type = _PACKAGE
_PLACEMENTREQUEST_TASKTOJOBIDENTRY.containing_type = _PLACEMENTREQUEST
_PLACEMENTREQUEST_TASKTOJOBDESCRIPTORENTRY.containing_type = _PLACEMENTREQUEST
_PLACEMENTREQUEST_METADATAENTRY.containing_type = _PLACEMENTREQUEST
_PLACEMENTREQUEST.fields_by_name['layout'].message_type = _LAYOUT
_PLACEMENTREQUEST.fields_by_name['task_to_job_id'].message_type = _PLACEMENTREQUEST_TASKTOJOBIDENTRY
_PLACEMENTREQUEST.fields_by_name['task_to_job_descriptor'].message_type = _PLACEMENTREQUEST_TASKTOJOBDESCRIPTORENTRY
_PLACEMENTREQUEST.fields_by_name['instance_context'].message_type = _INSTANCECONTEXT
_PLACEMENTREQUEST.fields_by_name['metadata'].message_type = _PLACEMENTREQUEST_METADATAENTRY
_PLACEMENTRESPONSE_ASSIGNMENTSENTRY.fields_by_name['value'].message_type = _ASSIGNMENT
_PLACEMENTRESPONSE_ASSIGNMENTSENTRY.containing_type = _PLACEMENTRESPONSE
_PLACEMENTRESPONSE_METADATAENTRY.containing_type = _PLACEMENTRESPONSE
_PLACEMENTRESPONSE.fields_by_name['assignments'].message_type = _PLACEMENTRESPONSE_ASSIGNMENTSENTRY
_PLACEMENTRESPONSE.fields_by_name['metadata'].message_type = _PLACEMENTRESPONSE_METADATAENTRY
DESCRIPTOR.message_types_by_name['Thread'] = _THREAD
DESCRIPTOR.message_types_by_name['Core'] = _CORE
DESCRIPTOR.message_types_by_name['Package'] = _PACKAGE
DESCRIPTOR.message_types_by_name['Layout'] = _LAYOUT
DESCRIPTOR.message_types_by_name['InstanceContext'] = _INSTANCECONTEXT
DESCRIPTOR.message_types_by_name['PlacementRequest'] = _PLACEMENTREQUEST
DESCRIPTOR.message_types_by_name['Assignment'] = _ASSIGNMENT
DESCRIPTOR.message_types_by_name['PlacementResponse'] = _PLACEMENTRESPONSE
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

Thread = _reflection.GeneratedProtocolMessageType('Thread', (_message.Message,), {
  'DESCRIPTOR' : _THREAD,
  '__module__' : 'isolate_pb2'
  # @@protoc_insertion_point(class_scope:isolation.v1.Thread)
  })
_sym_db.RegisterMessage(Thread)

Core = _reflection.GeneratedProtocolMessageType('Core', (_message.Message,), {
  'DESCRIPTOR' : _CORE,
  '__module__' : 'isolate_pb2'
  # @@protoc_insertion_point(class_scope:isolation.v1.Core)
  })
_sym_db.RegisterMessage(Core)

Package = _reflection.GeneratedProtocolMessageType('Package', (_message.Message,), {
  'DESCRIPTOR' : _PACKAGE,
  '__module__' : 'isolate_pb2'
  # @@protoc_insertion_point(class_scope:isolation.v1.Package)
  })
_sym_db.RegisterMessage(Package)

Layout = _reflection.GeneratedProtocolMessageType('Layout', (_message.Message,), {
  'DESCRIPTOR' : _LAYOUT,
  '__module__' : 'isolate_pb2'
  # @@protoc_insertion_point(class_scope:isolation.v1.Layout)
  })
_sym_db.RegisterMessage(Layout)

InstanceContext = _reflection.GeneratedProtocolMessageType('InstanceContext', (_message.Message,), {
  'DESCRIPTOR' : _INSTANCECONTEXT,
  '__module__' : 'isolate_pb2'
  # @@protoc_insertion_point(class_scope:isolation.v1.InstanceContext)
  })
_sym_db.RegisterMessage(InstanceContext)

PlacementRequest = _reflection.GeneratedProtocolMessageType('PlacementRequest', (_message.Message,), {

  'TaskToJobIdEntry' : _reflection.GeneratedProtocolMessageType('TaskToJobIdEntry', (_message.Message,), {
    'DESCRIPTOR' : _PLACEMENTREQUEST_TASKTOJOBIDENTRY,
    '__module__' : 'isolate_pb2'
    # @@protoc_insertion_point(class_scope:isolation.v1.PlacementRequest.TaskToJobIdEntry)
    })
  ,

  'TaskToJobDescriptorEntry' : _reflection.GeneratedProtocolMessageType('TaskToJobDescriptorEntry', (_message.Message,), {
    'DESCRIPTOR' : _PLACEMENTREQUEST_TASKTOJOBDESCRIPTORENTRY,
    '__module__' : 'isolate_pb2'
    # @@protoc_insertion_point(class_scope:isolation.v1.PlacementRequest.TaskToJobDescriptorEntry)
    })
  ,

  'MetadataEntry' : _reflection.GeneratedProtocolMessageType('MetadataEntry', (_message.Message,), {
    'DESCRIPTOR' : _PLACEMENTREQUEST_METADATAENTRY,
    '__module__' : 'isolate_pb2'
    # @@protoc_insertion_point(class_scope:isolation.v1.PlacementRequest.MetadataEntry)
    })
  ,
  'DESCRIPTOR' : _PLACEMENTREQUEST,
  '__module__' : 'isolate_pb2'
  # @@protoc_insertion_point(class_scope:isolation.v1.PlacementRequest)
  })
_sym_db.RegisterMessage(PlacementRequest)
_sym_db.RegisterMessage(PlacementRequest.TaskToJobIdEntry)
_sym_db.RegisterMessage(PlacementRequest.TaskToJobDescriptorEntry)
_sym_db.RegisterMessage(PlacementRequest.MetadataEntry)

Assignment = _reflection.GeneratedProtocolMessageType('Assignment', (_message.Message,), {
  'DESCRIPTOR' : _ASSIGNMENT,
  '__module__' : 'isolate_pb2'
  # @@protoc_insertion_point(class_scope:isolation.v1.Assignment)
  })
_sym_db.RegisterMessage(Assignment)

PlacementResponse = _reflection.GeneratedProtocolMessageType('PlacementResponse', (_message.Message,), {

  'AssignmentsEntry' : _reflection.GeneratedProtocolMessageType('AssignmentsEntry', (_message.Message,), {
    'DESCRIPTOR' : _PLACEMENTRESPONSE_ASSIGNMENTSENTRY,
    '__module__' : 'isolate_pb2'
    # @@protoc_insertion_point(class_scope:isolation.v1.PlacementResponse.AssignmentsEntry)
    })
  ,

  'MetadataEntry' : _reflection.GeneratedProtocolMessageType('MetadataEntry', (_message.Message,), {
    'DESCRIPTOR' : _PLACEMENTRESPONSE_METADATAENTRY,
    '__module__' : 'isolate_pb2'
    # @@protoc_insertion_point(class_scope:isolation.v1.PlacementResponse.MetadataEntry)
    })
  ,
  'DESCRIPTOR' : _PLACEMENTRESPONSE,
  '__module__' : 'isolate_pb2'
  # @@protoc_insertion_point(class_scope:isolation.v1.PlacementResponse)
  })
_sym_db.RegisterMessage(PlacementResponse)
_sym_db.RegisterMessage(PlacementResponse.AssignmentsEntry)
_sym_db.RegisterMessage(PlacementResponse.MetadataEntry)


DESCRIPTOR._options = None
_PLACEMENTREQUEST_TASKTOJOBIDENTRY._options = None
_PLACEMENTREQUEST_TASKTOJOBDESCRIPTORENTRY._options = None
_PLACEMENTREQUEST_METADATAENTRY._options = None
_PLACEMENTRESPONSE_ASSIGNMENTSENTRY._options = None
_PLACEMENTRESPONSE_METADATAENTRY._options = None

_ISOLATIONSERVICE = _descriptor.ServiceDescriptor(
  name='IsolationService',
  full_name='isolation.v1.IsolationService',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_start=1350,
  serialized_end=1455,
  methods=[
  _descriptor.MethodDescriptor(
    name='ComputePlacement',
    full_name='isolation.v1.IsolationService.ComputePlacement',
    index=0,
    containing_service=None,
    input_type=_PLACEMENTREQUEST,
    output_type=_PLACEMENTRESPONSE,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
])
_sym_db.RegisterServiceDescriptor(_ISOLATIONSERVICE)

DESCRIPTOR.services_by_name['IsolationService'] = _ISOLATIONSERVICE

# @@protoc_insertion_point(module_scope)