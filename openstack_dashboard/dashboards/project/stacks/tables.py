# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import logging

from django.http import Http404  # noqa
from django.template.defaultfilters import timesince  # noqa
from django.template.defaultfilters import title  # noqa
from django.utils.translation import ugettext_lazy as _  # noqa

from horizon import messages
from horizon import tables
from horizon.utils.filters import parse_isotime  # noqa
from horizon.utils.filters import replace_underscores  # noqa

from heatclient import exc

from openstack_dashboard import api
from openstack_dashboard.dashboards.project.stacks import mappings

LOG = logging.getLogger(__name__)


class LaunchStack(tables.LinkAction):
    name = "launch"
    verbose_name = _("Launch Stack")
    url = "horizon:project:stacks:select_template"
    classes = ("btn-create", "ajax-modal")


class DeleteStack(tables.BatchAction):
    name = "delete"
    action_present = _("Delete")
    action_past = _("Scheduled deletion of")
    data_type_singular = _("Stack")
    data_type_plural = _("Stacks")
    classes = ('btn-danger', 'btn-terminate')

    def action(self, request, stack_id):
        api.heat.stack_delete(request, stack_id)


class StacksUpdateRow(tables.Row):
    ajax = True

    def get_data(self, request, stack_id):
        try:
            return api.heat.stack_get(request, stack_id)
        except exc.HTTPNotFound:
            # returning 404 to the ajax call removes the
            # row from the table on the ui
            raise Http404
        except Exception as e:
            messages.error(request, e)


class StacksTable(tables.DataTable):
    STATUS_CHOICES = (
        ("Create Complete", True),
        ("Update Complete", True),
        ("Create Failed", False),
        ("Update Failed", False),
    )
    name = tables.Column("stack_name",
                         verbose_name=_("Stack Name"),
                         link="horizon:project:stacks:detail",)
    created = tables.Column("creation_time",
                            verbose_name=_("Created"),
                            filters=(parse_isotime, timesince))
    updated = tables.Column("updated_time",
                            verbose_name=_("Updated"),
                            filters=(parse_isotime, timesince))
    status = tables.Column("stack_status",
                           filters=(title, replace_underscores),
                           verbose_name=_("Status"),
                           status=True,
                           status_choices=STATUS_CHOICES)

    def get_object_display(self, stack):
        return stack.stack_name

    class Meta:
        name = "stacks"
        verbose_name = _("Stacks")
        status_columns = ["status", ]
        row_class = StacksUpdateRow
        table_actions = (LaunchStack, DeleteStack,)
        row_actions = (DeleteStack, )


class EventsTable(tables.DataTable):

    logical_resource = tables.Column('logical_resource_id',
                                     verbose_name=_("Stack Resource"),
                                     link=lambda d: d.logical_resource_id,)
    physical_resource = tables.Column('physical_resource_id',
                                      verbose_name=_("Resource"),
                                      link=mappings.resource_to_url)
    timestamp = tables.Column('event_time',
                              verbose_name=_("Time Since Event"),
                              filters=(parse_isotime, timesince))
    status = tables.Column("resource_status",
                           filters=(title, replace_underscores),
                           verbose_name=_("Status"),)

    statusreason = tables.Column("resource_status_reason",
                                 verbose_name=_("Status Reason"),)

    class Meta:
        name = "events"
        verbose_name = _("Stack Events")


class ResourcesUpdateRow(tables.Row):
    ajax = True

    def get_data(self, request, resource_name):
        try:
            stack = self.table.stack
            stack_identifier = '%s/%s' % (stack.stack_name, stack.id)
            return api.heat.resource_get(
                request, stack_identifier, resource_name)
        except exc.HTTPNotFound:
            # returning 404 to the ajax call removes the
            # row from the table on the ui
            raise Http404
        except Exception as e:
            messages.error(request, e)


class ResourcesTable(tables.DataTable):
    STATUS_CHOICES = (
        ("Create Complete", True),
        ("Create Failed", False),
    )

    logical_resource = tables.Column('logical_resource_id',
                                     verbose_name=_("Stack Resource"),
                                     link=lambda d: d.logical_resource_id)
    physical_resource = tables.Column('physical_resource_id',
                                     verbose_name=_("Resource"),
                                     link=mappings.resource_to_url)
    resource_type = tables.Column("resource_type",
                           verbose_name=_("Stack Resource Type"),)
    updated_time = tables.Column('updated_time',
                              verbose_name=_("Date Updated"),
                              filters=(parse_isotime, timesince))
    status = tables.Column("resource_status",
                           filters=(title, replace_underscores),
                           verbose_name=_("Status"),
                           status=True,
                           status_choices=STATUS_CHOICES)

    statusreason = tables.Column("resource_status_reason",
                                 verbose_name=_("Status Reason"),)

    def __init__(self, request, data=None,
                 needs_form_wrapper=None, **kwargs):
        super(ResourcesTable, self).__init__(
            request, data, needs_form_wrapper, **kwargs)
        self.stack = kwargs['stack']

    def get_object_id(self, datum):
        return datum.logical_resource_id

    class Meta:
        name = "resources"
        verbose_name = _("Stack Resources")
        status_columns = ["status", ]
        row_class = ResourcesUpdateRow
