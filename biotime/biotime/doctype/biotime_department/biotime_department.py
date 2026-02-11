# Copyright (c) 2025, Ali Raxa and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class BioTimeDepartment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		biotime_department_id: DF.Int
		dept_code: DF.Data
		dept_name: DF.Data
		last_sync: DF.Datetime | None
		parent_department: DF.Link | None
		parent_dept_name: DF.Data | None
	# end: auto-generated types
	pass
