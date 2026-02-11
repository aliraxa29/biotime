# Copyright (c) 2025, Ali Raxa and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class BioTimePosition(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		biotime_position_id: DF.Int
		last_sync: DF.Datetime | None
		parent_position: DF.Link | None
		parent_position_name: DF.Data | None
		position_code: DF.Data
		position_name: DF.Data
	# end: auto-generated types
	pass
