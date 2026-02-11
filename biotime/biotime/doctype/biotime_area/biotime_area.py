# Copyright (c) 2025, Ali Raxa and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class BioTimeArea(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		area_code: DF.Data
		area_name: DF.Data
		biotime_area_id: DF.Int
		last_sync: DF.Datetime | None
		parent_area: DF.Link | None
		parent_area_name: DF.Data | None
	# end: auto-generated types
	pass
